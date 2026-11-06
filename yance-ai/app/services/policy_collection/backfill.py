"""Historical backfill queue.

Why a second queue instead of "just crawl everything"
-----------------------------------------------------
The incremental queue (:func:`service.execute_source_run`) is optimised for
*discovering changes*: read page 1, look at the newest items, stop.  That design
can never build an archive — 90 sources x 2 documents per run is how the previous
dry run produced 84 documents, not because the sites only hold 84 documents.

This module walks each source's archive **page by page**, one bounded batch at a
time, and persists a cursor after every batch:

    state.cursor["backfill"] = {
        "page": 7,                # next page to read
        "documents_stored": 132,  # cumulative, informational
        "exhausted": false,       # list has more pages
        "unsupported_reason": null,
        "updated_at": "2026-11-06T..."
    }

Guarantees the operator asked for:

* **Resumable** — an interrupted batch resumes at ``page``; the cursor is only
  advanced after the batch's run row is committed.
* **Bounded** — page window, document count and elapsed seconds are all capped.
* **Isolated** — one source failing raises nothing for the others; failures land
  in the run row and in source health (``consecutive_failures``).
* **Honest** — a source whose list page exposes no pagination is recorded as
  ``unsupported_reason`` instead of being silently reported as "archived".
* **Non-destructive** — evidence is append-only; re-reading a page can only add
  rows, never delete or overwrite them.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.policy_collection import PolicySourceState
from app.services.policy_collection.catalog import Catalog, SourceDefinition
from app.services.policy_collection.ops import (
    backlog_report,
    pause_state,
    prioritised_sources,
    storage_guard,
)
from app.services.policy_collection.runner import CollectionLimits
from app.services.policy_collection.service import RunReport, execute_source_run

logger = logging.getLogger(__name__)

CURSOR_KEY = "backfill"


def _utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass
class BackfillConfig:
    max_sources: int = 5
    pages_per_batch: int = 3
    docs_per_batch: int = 15
    seconds_budget: int = 900
    source_ids: tuple[str, ...] = ()

    @classmethod
    def from_settings(cls, **overrides) -> "BackfillConfig":
        base = cls(
            max_sources=int(getattr(settings, "policy_collection_backfill_max_sources", 5) or 5),
            pages_per_batch=max(1, int(settings.policy_collection_backfill_pages_per_batch or 1)),
            docs_per_batch=max(1, int(settings.policy_collection_backfill_docs_per_batch or 1)),
            seconds_budget=max(30, int(settings.policy_collection_backfill_window_seconds or 900)),
        )
        for key, value in overrides.items():
            if value is not None and hasattr(base, key):
                setattr(base, key, value)
        return base


@dataclass
class SourceBackfillResult:
    source_id: str
    page_from: int
    page_to: int
    pages_read: int = 0
    documents_seen: int = 0
    documents_new: int = 0
    documents_changed: int = 0
    documents_unchanged: int = 0
    documents_failed: int = 0
    status: str = "pending"
    exhausted: bool = False
    stop_reason: str | None = None
    note: str | None = None

    def as_dict(self) -> dict:
        return {
            "source_id": self.source_id,
            "page_from": self.page_from,
            "page_to": self.page_to,
            "pages_read": self.pages_read,
            "documents_seen": self.documents_seen,
            "documents_new": self.documents_new,
            "documents_changed": self.documents_changed,
            "documents_unchanged": self.documents_unchanged,
            "documents_failed": self.documents_failed,
            "status": self.status,
            "exhausted": self.exhausted,
            "stop_reason": self.stop_reason,
            "note": self.note,
        }


@dataclass
class BackfillBatchReport:
    started_at: datetime
    finished_at: datetime | None = None
    sources: list[SourceBackfillResult] = field(default_factory=list)
    skipped: list[dict] = field(default_factory=list)
    stop_reason: str | None = None
    storage: dict | None = None
    pause: str = "none"

    @property
    def totals(self) -> dict:
        return {
            "sources": len(self.sources),
            "pages_read": sum(s.pages_read for s in self.sources),
            "documents_seen": sum(s.documents_seen for s in self.sources),
            "documents_new": sum(s.documents_new for s in self.sources),
            "documents_changed": sum(s.documents_changed for s in self.sources),
            "documents_unchanged": sum(s.documents_unchanged for s in self.sources),
            "documents_failed": sum(s.documents_failed for s in self.sources),
        }

    def as_dict(self) -> dict:
        return {
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "stop_reason": self.stop_reason,
            "pause": self.pause,
            "storage": self.storage,
            "totals": self.totals,
            "sources": [s.as_dict() for s in self.sources],
            "skipped": self.skipped,
        }


# --------------------------------------------------------------------------- #
# cursor helpers
# --------------------------------------------------------------------------- #
def read_cursor(state: PolicySourceState) -> dict:
    cursor = dict((state.cursor or {}).get(CURSOR_KEY) or {})
    cursor.setdefault("page", 1)
    cursor.setdefault("exhausted", False)
    return cursor


def write_cursor(state: PolicySourceState, cursor: dict) -> None:
    payload = dict(state.cursor or {})
    payload[CURSOR_KEY] = {**cursor, "updated_at": _utcnow().isoformat()}
    state.cursor = payload


def _state(db: Session, source_id: str) -> PolicySourceState:
    state = db.get(PolicySourceState, source_id)
    if state is None:
        state = PolicySourceState(source_id=source_id)
        db.add(state)
        db.flush()
    return state


# --------------------------------------------------------------------------- #
# plan / run
# --------------------------------------------------------------------------- #
def plan(db: Session, catalog: Catalog, *, config: BackfillConfig) -> list[dict]:
    """Which sources the next batch would touch, in order, with their cursor."""
    plan_rows: list[dict] = []
    for source in prioritised_sources(catalog, db, limit=config.max_sources):
        state = db.get(PolicySourceState, source.source_id)
        cursor = read_cursor(state) if state is not None else {"page": 1, "exhausted": False}
        plan_rows.append(
            {
                "source_id": source.source_id,
                "name": source.name,
                "level": source.level,
                "channel": source.channel,
                "next_page": cursor.get("page", 1),
                "exhausted": bool(cursor.get("exhausted")),
                "unsupported_reason": cursor.get("unsupported_reason"),
                "gap_reason": cursor.get("gap_reason"),
                "gap_page": cursor.get("gap_page"),
            }
        )
    return plan_rows


def run_batch(
    db: Session,
    catalog: Catalog,
    *,
    config: BackfillConfig | None = None,
    limits: CollectionLimits | None = None,
    dry_run: bool = False,
) -> BackfillBatchReport:
    """Execute one bounded backfill batch and persist every cursor change."""
    config = config or BackfillConfig.from_settings()
    report = BackfillBatchReport(started_at=_utcnow())

    guard = storage_guard()
    report.storage = guard.as_dict()
    if not guard.ok:
        report.stop_reason = "storage_full"
        logger.warning("backfill refused: %s", guard.reason)
        report.finished_at = _utcnow()
        return report

    global_pause = pause_state(db)
    report.pause = global_pause.scope
    if global_pause.paused:
        report.stop_reason = "paused"
        report.finished_at = _utcnow()
        return report

    by_id = {source.source_id: source for source in catalog.sources}
    candidates = (
        [by_id[sid] for sid in config.source_ids if sid in by_id]
        if config.source_ids
        else prioritised_sources(catalog, db, limit=config.max_sources)
    )

    deadline = time.monotonic() + config.seconds_budget
    for source in candidates:
        if time.monotonic() > deadline:
            report.stop_reason = "time_budget"
            break
        if settings.policy_collection_paused:
            report.stop_reason = "paused"
            break
        state = _state(db, source.source_id)
        cursor = read_cursor(state)
        if cursor.get("exhausted"):
            report.skipped.append({"source_id": source.source_id, "reason": "archive_exhausted"})
            continue
        if cursor.get("backfill_blocked"):
            report.skipped.append(
                {
                    "source_id": source.source_id,
                    "reason": "backfill_parked",
                    "detail": cursor.get("backfill_blocked"),
                }
            )
            continue
        if cursor.get("unsupported_reason"):
            report.skipped.append(
                {
                    "source_id": source.source_id,
                    "reason": "pagination_unsupported",
                    "detail": cursor.get("unsupported_reason"),
                }
            )
            continue
        if state.paused:
            report.skipped.append(
                {"source_id": source.source_id, "reason": "source_paused", "detail": state.paused_reason}
            )
            continue

        result = _run_one(
            db,
            source,
            state,
            cursor,
            config=config,
            limits=limits,
            dry_run=dry_run,
        )
        report.sources.append(result)
        if result.stop_reason == "storage_full":
            report.stop_reason = "storage_full"
            break

    report.finished_at = _utcnow()
    return report


def _run_one(
    db: Session,
    source: SourceDefinition,
    state: PolicySourceState,
    cursor: dict,
    *,
    config: BackfillConfig,
    limits: CollectionLimits | None,
    dry_run: bool,
) -> SourceBackfillResult:
    start_page = max(1, int(cursor.get("page", 1)))
    result = SourceBackfillResult(
        source_id=source.source_id,
        page_from=start_page,
        page_to=start_page + config.pages_per_batch - 1,
    )

    run_report: RunReport = execute_source_run(
        db,
        source,
        trigger="backfill",
        limits=limits,
        max_items=config.docs_per_batch,
        max_pages=config.pages_per_batch,
        start_page=start_page,
        dry_run=dry_run,
    )
    result.status = run_report.status
    outcome = run_report.outcome
    if outcome is None:
        # Locked / disabled / not executed: cursor must not move.
        result.stop_reason = run_report.skipped_reason or run_report.status
        result.note = f"not executed: {run_report.status}"
        return result

    result.pages_read = outcome.pages_fetched
    result.documents_seen = outcome.list_entries
    result.documents_new = outcome.new_documents
    result.documents_changed = outcome.updated_documents
    result.documents_unchanged = outcome.unchanged_documents
    result.documents_failed = outcome.failed_documents
    result.note = outcome.adapter_note

    if outcome.error_kind == "storage_full":
        result.stop_reason = "storage_full"
        return result

    unsupported = "pagination_unsupported" in (outcome.adapter_note or "")
    if unsupported:
        # Never keep re-reading page 1 while pretending an archive exists.
        cursor["unsupported_reason"] = outcome.adapter_note
        if not dry_run:
            write_cursor(state, cursor)
            db.commit()
        result.exhausted = True
        result.stop_reason = "pagination_unsupported"
        return result

    # A page that answers 200 but yields no candidate links has three very
    # different meanings, and conflating them is how an archive silently loses
    # history: (a) the site says this was the last screen, so the archive really
    # ended; (b) the list rule stopped matching, so history is still there and the
    # cursor must not move; (c) the column genuinely has nothing to show yet.
    # Only (a) may mark the cursor exhausted.
    list_error = outcome.error_kind in {"empty_list", "selector_miss"}
    if outcome.ok and list_error:
        declared = outcome.pages_available
        beyond_declared = bool(declared) and start_page > declared
        if beyond_declared:
            cursor["exhausted"] = True
            cursor["page"] = start_page
            cursor.pop("gap_reason", None)
            if not dry_run:
                write_cursor(state, cursor)
                db.commit()
            result.exhausted = True
            result.stop_reason = "archive_end"
            return result
        attempt = int(cursor.get("gap_streak", 0)) + 1
        cursor["gap_streak"] = attempt
        cursor["gap_reason"] = (
            outcome.error
            or f"page {start_page} returned no candidates (declared pages: {declared or 'unknown'})"
        )
        cursor["gap_page"] = start_page
        limit = int(getattr(settings, "policy_collection_gap_streak_limit", 3) or 3)
        if attempt >= limit:
            # Parked, not skipped: the page is still re-readable after a manual
            # ``backfill-reset``, so no history is lost and the loop stops burning
            # cycles on a selector that is clearly broken.
            cursor["backfill_blocked"] = (
                f"page {start_page} returned no candidates {attempt} times "
                f"(declared pages: {declared or 'unknown'}); reset after fixing the list rule"
            )
            result.stop_reason = "parked_after_empty_pages"
            if not dry_run:
                write_cursor(state, cursor)
                db.commit()
            result.exhausted = False
            return result
        # The cursor deliberately stays on this page: re-reading it after a fix is
        # idempotent, whereas skipping it would leave a permanent hole.
        if not dry_run:
            write_cursor(state, cursor)
            db.commit()
        result.exhausted = False
        result.stop_reason = "page_empty_unverified"
        return result

    if outcome.ok and result.pages_read == 0:
        result.stop_reason = "no_page_read"
        return result

    if outcome.ok:
        cursor["page"] = start_page + max(1, result.pages_read)
        cursor["documents_stored"] = int(cursor.get("documents_stored", 0)) + result.documents_new
        cursor["exhausted"] = False
        cursor.pop("unsupported_reason", None)
        cursor.pop("gap_streak", None)
        cursor.pop("gap_reason", None)
        cursor.pop("backfill_blocked", None)
        if not dry_run:
            write_cursor(state, cursor)
            db.commit()
        result.stop_reason = "batch_complete"
        return result

    # Source-level failure: keep the cursor where it is so a retry re-reads the
    # same window (idempotent, no gap), and let health/backoff handle frequency.
    result.stop_reason = "source_error"
    return result


def status(db: Session, catalog: Catalog) -> dict:
    """Cursor table + backlog, for the ``backfill-status`` command."""
    rows: list[dict] = []
    for source in catalog.sources:
        if not source.enabled:
            continue
        state = db.get(PolicySourceState, source.source_id)
        cursor = read_cursor(state) if state is not None else {"page": 1, "exhausted": False}
        rows.append(
            {
                "source_id": source.source_id,
                "level": source.level,
                "channel": source.channel,
                "page": cursor.get("page", 1),
                "documents_stored": cursor.get("documents_stored", 0),
                "exhausted": bool(cursor.get("exhausted")),
                "gap_reason": cursor.get("gap_reason"),
                "unsupported_reason": cursor.get("unsupported_reason"),
                "updated_at": cursor.get("updated_at"),
                "paused": bool(state.paused) if state is not None else False,
            }
        )
    pending = [row for row in rows if not row["exhausted"] and not row["unsupported_reason"]]
    return {
        "generated_at": _utcnow().isoformat(),
        "enabled_sources": len(rows),
        "pending": len(pending),
        "exhausted": sum(1 for row in rows if row["exhausted"]),
        "unsupported": sum(1 for row in rows if row["unsupported_reason"]),
        "sources": rows,
        "backlog": backlog_report(db, catalog),
    }
