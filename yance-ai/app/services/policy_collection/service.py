"""DB-bound orchestration for the policy collection system.

``runner`` knows how to fetch and parse; this module knows how a *production
run* is recorded: task lock, run row, source health, pause circuit breaker.

Everything the operational commands need lives here so that the CLI, an API
endpoint and a scheduled job all share one implementation:

* :func:`acquire_source_run` — one run per source at a time (DB row lock).
* :func:`execute_source_run` — run + persist statistics + update health.
* :func:`pause_source` / :func:`resume_source` — reversible operation, reads are
  never affected (paused sources simply stop being scheduled).
* :func:`coverage_report` — the six-state coverage matrix required by the docs.
* :func:`health_report` — freshness, failures, backlog, storage estimate.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import Policy, PolicyChunk, PolicyVersion
from app.models.policy_collection import (
    PolicyAttachment,
    PolicyCollectionRun,
    PolicyRawEvidence,
    PolicySourceState,
)
from app.services.policy_collection.catalog import Catalog, SourceDefinition, load_catalog
from app.services.policy_collection.rawstore import RawEvidenceStore
from app.services.policy_collection.runner import (
    CollectionLimits,
    PolicyCollectionRunner,
    SourceRunOutcome,
)
from app.services.policy_collection.store import SqlPolicyStore

logger = logging.getLogger(__name__)

COLLECTION_STATES = (
    "registered",  # in the catalog only
    "reachable",  # list page answered
    "fetched",  # at least one document downloaded
    "parsed",  # at least one document produced a version + chunks
    "searchable",  # at least one document visible in the public search index
    "in_production",  # scheduled and continuously running
)


def _utcnow() -> datetime:
    return datetime.now(UTC)


def raw_store() -> RawEvidenceStore:
    root = settings.policy_collection_raw_dir
    if not root:
        from pathlib import Path

        root = str(Path(__file__).resolve().parents[3] / "crawler_output" / "policy_raw")
    return RawEvidenceStore(root)


def load_runtime_catalog() -> Catalog:
    return load_catalog(settings.policy_collection_catalog_dir)


def _state_row(db: Session, source_id: str) -> PolicySourceState:
    row = db.get(PolicySourceState, source_id)
    if row is None:
        row = PolicySourceState(source_id=source_id)
        db.add(row)
        db.flush()
    return row


# --------------------------------------------------------------------------- #
# locking
# --------------------------------------------------------------------------- #
def acquire_source_run(
    db: Session,
    source_id: str,
    *,
    trigger: str,
    timeout_seconds: int | None = None,
) -> PolicyCollectionRun | None:
    """Create a run row unless another run for the same source is still alive."""
    timeout = timeout_seconds or settings.policy_collection_run_timeout_seconds
    stale_before = _utcnow() - timedelta(seconds=timeout)
    running = db.scalar(
        select(PolicyCollectionRun)
        .where(
            PolicyCollectionRun.source_id == source_id,
            PolicyCollectionRun.status == "running",
            PolicyCollectionRun.started_at >= stale_before,
        )
        .order_by(PolicyCollectionRun.started_at.desc())
    )
    if running is not None:
        logger.info("policy source %s already running (%s)", source_id, running.id)
        return None
    # Reap runs that died with a previous process so the source is not stuck.
    for stale in db.scalars(
        select(PolicyCollectionRun).where(
            PolicyCollectionRun.source_id == source_id,
            PolicyCollectionRun.status == "running",
            PolicyCollectionRun.started_at < stale_before,
        )
    ):
        stale.status = "abandoned"
        stale.finished_at = _utcnow()
        stale.error_kind = "stale_lock"
        stale.error_summary = "previous run exceeded the configured timeout"

    run = PolicyCollectionRun(
        id=uuid.uuid4(),
        source_id=source_id,
        trigger=trigger,
        status="running",
        lock_token=f"{uuid.uuid4().hex[:16]}",
        started_at=_utcnow(),
        stats={},
    )
    db.add(run)
    db.commit()
    return run


def finish_run(db: Session, run: PolicyCollectionRun, outcome: SourceRunOutcome) -> None:
    run.status = "completed" if outcome.ok else outcome.status
    run.finished_at = _utcnow()
    run.pages_fetched = outcome.pages_fetched
    run.items_seen = outcome.list_entries
    run.items_new = outcome.new_documents
    run.items_changed = outcome.updated_documents
    run.items_unchanged = outcome.unchanged_documents
    run.items_failed = outcome.failed_documents
    run.attachments_saved = outcome.attachments_saved
    run.attachments_failed = outcome.attachments_failed
    run.error_kind = outcome.error_kind
    run.error_summary = outcome.error
    run.stats = {
        "repost": outcome.repost_documents,
        "duration_ms": outcome.duration_ms,
        "items": [
            {
                "url": item.url,
                "status": item.status,
                "change": item.change,
                "policy_id": item.policy_id,
                "version": item.version,
                "error_kind": item.error_kind,
                "evidence_complete": item.evidence_complete,
            }
            for item in outcome.items[:200]
        ],
    }
    db.commit()


def update_source_health(db: Session, outcome: SourceRunOutcome) -> PolicySourceState:
    state = _state_row(db, outcome.source_id)
    state.last_check_at = _utcnow()
    state.last_items_seen = outcome.list_entries
    state.last_items_new = outcome.new_documents
    state.last_items_changed = outcome.updated_documents
    state.last_items_failed = outcome.failed_documents
    if outcome.ok:
        state.last_success_at = _utcnow()
        state.consecutive_failures = 0
        state.last_error = None
        state.last_error_kind = None
        if outcome.status == "no_update" and outcome.error_kind == "empty_list":
            state.last_error_kind = "empty_list"
            state.last_error = outcome.error
        elif outcome.new_documents or outcome.updated_documents or outcome.unchanged_documents:
            state.verification_state = "reachable"
    else:
        state.last_failure_at = _utcnow()
        state.consecutive_failures = (state.consecutive_failures or 0) + 1
        state.last_error_kind = outcome.error_kind
        state.last_error = (outcome.error or "")[:1000] or None
        threshold = settings.policy_collection_source_failure_pause_threshold
        if threshold and state.consecutive_failures >= threshold and not state.paused:
            state.paused = True
            state.paused_reason = (
                f"auto-paused after {state.consecutive_failures} consecutive failures "
                f"({outcome.error_kind})"
            )
    db.commit()
    return state


# --------------------------------------------------------------------------- #
# execution
# --------------------------------------------------------------------------- #
@dataclass
class RunReport:
    source_id: str
    run_id: str | None
    status: str
    outcome: SourceRunOutcome | None = None
    skipped_reason: str | None = None


def _validators_provider(db: Session):
    """Prior ETag / Last-Modified for a URL, read from stored evidence.

    Kept as a closure so the runner stays DB-free and therefore unit-testable
    offline.  Failing to find a validator is normal (first fetch) and simply
    results in an unconditional request.
    """

    def provide(source_id: str, url: str) -> dict[str, str]:
        from app.services.policy_collection.urlguard import normalize_url

        row = db.scalar(
            select(PolicyRawEvidence.http_meta)
            .where(
                PolicyRawEvidence.source_id == source_id,
                PolicyRawEvidence.url_normalized == normalize_url(url)[:1000],
                PolicyRawEvidence.purpose == "document",
            )
            .order_by(PolicyRawEvidence.fetched_at.desc())
            .limit(1)
        )
        if not row:
            return {}
        validators: dict[str, str] = {}
        if row.get("etag"):
            validators["etag"] = str(row["etag"])
        if row.get("last_modified"):
            validators["last_modified"] = str(row["last_modified"])
        return validators

    return provide


def _storage_stop_reason() -> str | None:
    """Refuse new downloads when the evidence volume is nearly full."""
    from app.services.policy_collection.ops import storage_guard

    guard = storage_guard()
    return None if guard.ok else "storage_full"


def execute_source_run(
    db: Session,
    source: SourceDefinition,
    *,
    trigger: str = "manual",
    limits: CollectionLimits | None = None,
    max_items: int | None = None,
    max_pages: int | None = None,
    start_page: int = 1,
    dry_run: bool = False,
) -> RunReport:
    if not settings.policy_collection_enabled and not dry_run and trigger != "manual":
        return RunReport(
            source_id=source.source_id,
            run_id=None,
            status="disabled",
            skipped_reason="policy_collection_enabled is False",
        )

    if dry_run:
        from app.services.policy_collection.runner import PolicyCollectionRunner as _R
        from app.services.policy_collection.store import MemoryPolicyStore

        runner = _R(
            store=MemoryPolicyStore(),
            raw_store=raw_store(),
            limits=limits or CollectionLimits.from_settings(settings),
            user_agent=settings.policy_collection_user_agent,
        )
        outcome = runner.run_source(
            source,
            trigger="dry-run",
            max_items=max_items,
            max_pages=max_pages,
            start_page=start_page,
        )
        return RunReport(
            source_id=source.source_id,
            run_id=outcome.run_id,
            status=outcome.status,
            outcome=outcome,
        )

    run = acquire_source_run(db, source.source_id, trigger=trigger)
    if run is None:
        return RunReport(
            source_id=source.source_id,
            run_id=None,
            status="locked",
            skipped_reason="another run for this source is still in progress",
        )
    store = SqlPolicyStore(db, embedding_enabled=False)
    runner = PolicyCollectionRunner(
        store=store,
        raw_store=raw_store(),
        limits=limits or CollectionLimits.from_settings(settings),
        user_agent=settings.policy_collection_user_agent,
        validators_provider=_validators_provider(db),
        prefetch_guard=_storage_stop_reason,
    )
    try:
        outcome = runner.run_source(
            source,
            trigger=trigger,
            run_id=str(run.id),
            max_items=max_items,
            max_pages=max_pages,
            start_page=start_page,
        )
    except Exception as exc:  # keep the run row consistent even on crash
        db.rollback()
        run.status = "failed"
        run.finished_at = _utcnow()
        run.error_kind = "runner_exception"
        run.error_summary = f"{type(exc).__name__}: {exc}"
        db.commit()
        raise
    finish_run(db, run, outcome)
    update_source_health(db, outcome)
    return RunReport(
        source_id=source.source_id, run_id=str(run.id), status=outcome.status, outcome=outcome
    )


def pause_source(db: Session, source_id: str, reason: str = "manual") -> PolicySourceState:
    state = _state_row(db, source_id)
    state.paused = True
    state.paused_reason = reason[:400]
    db.commit()
    return state


def resume_source(db: Session, source_id: str) -> PolicySourceState:
    state = _state_row(db, source_id)
    state.paused = False
    state.paused_reason = None
    state.consecutive_failures = 0
    db.commit()
    return state


def due_sources(
    catalog: Catalog, db: Session, *, now: datetime | None = None
) -> list[SourceDefinition]:
    """Sources whose check interval has elapsed and that are not paused."""
    moment = now or _utcnow()
    states = {row.source_id: row for row in db.scalars(select(PolicySourceState))}
    result: list[SourceDefinition] = []
    for source in catalog.sources:
        if not source.enabled:
            continue
        state = states.get(source.source_id)
        if state is not None and state.paused:
            continue
        last = (state.last_check_at if state else None) or source.last_success_at
        if last is None:
            result.append(source)
            continue
        if last.tzinfo is None:
            last = last.replace(tzinfo=UTC)
        if moment - last >= timedelta(hours=source.check_interval_hours):
            result.append(source)
    return result


# --------------------------------------------------------------------------- #
# reporting
# --------------------------------------------------------------------------- #
def coverage_rows(catalog: Catalog, db: Session) -> list[dict]:
    """Six-state coverage per source, derived from what actually exists."""
    states = {row.source_id: row for row in db.scalars(select(PolicySourceState))}
    rows: list[dict] = []
    for source in catalog.sources:
        origin_count = db.scalar(
            select(func.count(func.distinct(PolicyRawEvidence.url_normalized))).where(
                PolicyRawEvidence.source_id == source.source_id,
                PolicyRawEvidence.purpose == "document",
            )
        ) or 0
        parsed_count = db.scalar(
            select(func.count(func.distinct(PolicyRawEvidence.policy_id))).where(
                PolicyRawEvidence.source_id == source.source_id,
                PolicyRawEvidence.parse_status == "parsed",
                PolicyRawEvidence.policy_id.isnot(None),
            )
        ) or 0
        # "searchable" must mean *the retrieval endpoint returns it*, i.e. the
        # latest version is published and chunked - not merely that chunks exist.
        source_policy_ids = select(PolicyRawEvidence.policy_id).where(
            PolicyRawEvidence.source_id == source.source_id,
            PolicyRawEvidence.policy_id.isnot(None),
        )
        searchable = db.scalar(
            select(func.count(func.distinct(PolicyChunk.policy_id))).where(
                PolicyChunk.policy_id.in_(source_policy_ids),
                PolicyChunk.policy_version_id.in_(
                    select(PolicyVersion.id).where(PolicyVersion.status == "published")
                ),
            )
        ) or 0
        in_review = db.scalar(
            select(func.count(func.distinct(PolicyVersion.policy_id))).where(
                PolicyVersion.policy_id.in_(source_policy_ids),
                PolicyVersion.status == "pending_review",
            )
        ) or 0
        state = states.get(source.source_id)
        stage = "registered"
        if state is not None and state.verification_state in {"reachable", "list_verified"}:
            stage = "reachable"
        if origin_count:
            stage = "fetched"
        if parsed_count:
            stage = "parsed"
        if searchable:
            stage = "searchable"
        if state is not None and state.enabled and not state.paused and searchable:
            stage = "in_production" if source.check_interval_hours else stage
        rows.append(
            {
                "source_id": source.source_id,
                "name": source.name,
                "level": source.level,
                "province": source.province,
                "city": source.city,
                "enabled": source.enabled,
                "paused": bool(state.paused) if state else False,
                "catalog_state": source.verification_state,
                "stage": stage,
                "documents": origin_count,
                "parsed": parsed_count,
                "searchable_documents": searchable,
                "pending_review_documents": in_review,
                "last_check_at": state.last_check_at if state else None,
                "last_success_at": state.last_success_at if state else None,
                "last_error_kind": state.last_error_kind if state else None,
                "notes": source.notes,
            }
        )
    return rows


def health_report(db: Session) -> dict:
    total_evidence_bytes = db.scalar(select(func.coalesce(func.sum(PolicyRawEvidence.byte_size), 0))) or 0
    attachments = db.scalar(select(func.count(PolicyAttachment.id))) or 0
    failed_attachments = db.scalar(
        select(func.count(PolicyAttachment.id)).where(PolicyAttachment.parse_status == "failed")
    ) or 0
    # Parsed documents that do not yet have retrieval chunks: the backlog that
    # would block "已进入可用检索" for those policies.
    pending_policies = db.scalar(
        select(func.count(func.distinct(PolicyRawEvidence.policy_id))).where(
            PolicyRawEvidence.parse_status == "parsed",
            PolicyRawEvidence.policy_id.isnot(None),
            ~PolicyRawEvidence.policy_id.in_(select(PolicyChunk.policy_id)),
        )
    ) or 0
    versions = db.scalar(select(func.count(PolicyVersion.id))) or 0
    chunks = db.scalar(select(func.count(PolicyChunk.id))) or 0
    recent = db.scalars(
        select(PolicyCollectionRun).order_by(PolicyCollectionRun.started_at.desc()).limit(20)
    ).all()
    return {
        "evidence_bytes": int(total_evidence_bytes),
        "evidence_mb": round(int(total_evidence_bytes) / 1_048_576, 2),
        "attachments": attachments,
        "attachments_failed": failed_attachments,
        "policies_pending_review": pending_policies,
        "versions": versions,
        "chunks": chunks,
        "recent_runs": [
            {
                "source_id": run.source_id,
                "status": run.status,
                "trigger": run.trigger,
                "started_at": run.started_at,
                "new": run.items_new,
                "changed": run.items_changed,
                "failed": run.items_failed,
                "error_kind": run.error_kind,
            }
            for run in recent
        ],
    }


# --------------------------------------------------------------------------- #
# publication quality gate
# --------------------------------------------------------------------------- #
# Retrieval only serves ``PolicyVersion.status == "published"``.  Collection
# writes ``collected`` so that a fresh crawl never lands in front of customers
# unreviewed; this gate is what promotes the good ones automatically.  It is
# *fact* checking (is the evidence really there, is the text usable, is the
# region known) and deliberately not an eligibility opinion about any company.
PUBLISH_MIN_CHARS = 300

# Column/title strings that come from site navigation, not from a document.
NAV_TITLE_TOKENS = (
    "政府信息公开",
    "more",
    "更多",
    "首页",
    "网站地图",
)


@dataclass
class PromoteReport:
    checked: int = 0
    published: int = 0
    held_for_review: int = 0
    reasons: dict = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.reasons is None:
            self.reasons = {}

    def as_dict(self) -> dict:
        return {
            "checked": self.checked,
            "published": self.published,
            "held_for_review": self.held_for_review,
            "reasons": dict(sorted(self.reasons.items())),
        }


def _quality_gate_blockers(db: Session, version: PolicyVersion) -> list[str]:
    """Return the reasons this version is not publishable yet (empty = ok)."""
    blockers: list[str] = []
    title = (version.title or "").strip()
    if len(title) < 8 or any(token in title for token in NAV_TITLE_TOKENS):
        blockers.append("title_unusable")
    if len((version.content or "").strip()) < PUBLISH_MIN_CHARS:
        blockers.append("content_too_short")
    if not (version.region or "").strip():
        blockers.append("region_unknown")
    # Original-page evidence must exist and be complete; a failed evidence write
    # means we cannot prove what the page said.
    evidence_ok = db.scalar(
        select(func.count(PolicyRawEvidence.id)).where(
            PolicyRawEvidence.policy_version_id == version.id,
            PolicyRawEvidence.purpose == "document",
            PolicyRawEvidence.storage_path.isnot(None),
            PolicyRawEvidence.content_sha256.isnot(None),
        )
    ) or 0
    if evidence_ok == 0:
        blockers.append("original_evidence_missing")
    chunks = db.scalar(
        select(func.count(PolicyChunk.id)).where(PolicyChunk.policy_version_id == version.id)
    ) or 0
    if chunks == 0:
        blockers.append("no_retrieval_chunks")
    return blockers


def promote_ready_documents(
    db: Session,
    *,
    limit: int = 200,
    dry_run: bool = False,
) -> PromoteReport:
    """Move ``collected`` versions to ``published`` when the facts hold up.

    Versions that fail the gate move to ``pending_review`` and are reported with
    a reason code so an operator can see *why* something is not searchable.
    """
    report = PromoteReport()
    latest = (
        select(PolicyVersion.policy_id, func.max(PolicyVersion.version).label("latest_version"))
        .group_by(PolicyVersion.policy_id)
        .subquery()
    )
    candidates = db.scalars(
        select(PolicyVersion)
        .join(
            latest,
            (latest.c.policy_id == PolicyVersion.policy_id)
            & (latest.c.latest_version == PolicyVersion.version),
        )
        .where(
            PolicyVersion.status == "collected",
            PolicyVersion.tenant_id.is_(None),  # only the public catalogue is promoted
        )
        .order_by(PolicyVersion.publish_date.desc().nullslast(), PolicyVersion.id)
        .limit(limit)
    ).all()

    for version in candidates:
        report.checked += 1
        blockers = _quality_gate_blockers(db, version)
        if blockers:
            report.held_for_review += 1
            for reason in blockers:
                report.reasons[reason] = report.reasons.get(reason, 0) + 1
            if not dry_run:
                version.status = "pending_review"
        else:
            report.published += 1
            if not dry_run:
                version.status = "published"
                # Retrieval gates on Policy.status too (current_policy_clauses), so
                # promoting the version alone would leave the policy invisible.
                parent = db.get(Policy, version.policy_id)
                if parent is not None and parent.status != "published":
                    parent.status = "published"
                    parent.updated_at = func.now()
    if not dry_run:
        db.commit()
    return report
