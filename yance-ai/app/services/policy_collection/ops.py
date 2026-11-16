"""Operational guards shared by both collection queues.

The queues themselves live in :mod:`backfill` (archive) and :mod:`service`
(incremental).  This module holds the three things that must behave identically
for both of them, because getting them subtly different between queues is how a
"24h pipeline" ends up hammering a government site or filling the disk:

* :func:`pause_state` — one global kill switch (``policy_collection_paused``)
  plus per-source pauses already stored on ``policy_sources``.
* :func:`storage_guard` — refuse *new* downloads when free space is low.  Existing
  data stays readable and searchable; only growth stops.
* :func:`backlog_report` / :func:`heartbeat` — the numbers an operator needs to
  tell "quiet" apart from "stuck", without reading logs.

Nothing here performs network I/O.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.policy_collection import (
    PolicyCollectionRun,
    PolicyRawEvidence,
    PolicySourceState,
)
from app.services.policy_collection.catalog import Catalog, SourceDefinition
from app.services.policy_collection.rawstore import RawEvidenceStore


def _utcnow() -> datetime:
    return datetime.now(UTC)


# --------------------------------------------------------------------------- #
# pause switches
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class PauseState:
    paused: bool
    reason: str | None = None
    scope: str = "none"  # none / global / source

    @property
    def allowed(self) -> bool:
        return not self.paused


def pause_flag_path() -> Path:
    """Where the file-based global pause flag lives (on the persistent volume)."""
    configured = str(getattr(settings, "policy_collection_pause_flag_path", "") or "")
    if configured:
        return Path(configured)
    return Path(settings.policy_collection_raw_dir or "crawler_output/policy_raw") / "PAUSED"


def read_pause_flag() -> str | None:
    """Return the recorded reason when the pause flag exists, else ``None``."""
    path = pause_flag_path()
    try:
        if not path.exists():
            return None
        reason = path.read_text("utf-8").strip()
        return reason or "paused by operator"
    except OSError:
        # An unreadable flag must not be treated as "not paused": fail closed.
        return f"pause flag unreadable at {path}"


def write_pause_flag(reason: str) -> Path:
    path = pause_flag_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(reason.strip() or "paused by operator", "utf-8")
    return path


def clear_pause_flag() -> bool:
    path = pause_flag_path()
    try:
        path.unlink()
        return True
    except FileNotFoundError:
        return False


def pause_state(db: Session | None = None, source_id: str | None = None) -> PauseState:
    """Global switch wins over per-source state; a manual pause is never auto-cleared."""
    if settings.policy_collection_paused:
        return PauseState(paused=True, reason="global pause (policy_collection_paused=True)", scope="global")
    flag_reason = read_pause_flag()
    if flag_reason is not None:
        return PauseState(paused=True, reason=f"global pause (flag): {flag_reason}", scope="global")
    if db is not None and source_id:
        state = db.get(PolicySourceState, source_id)
        if state is not None and state.paused:
            return PauseState(
                paused=True,
                reason=state.paused_reason or "source paused",
                scope="source",
            )
    return PauseState(paused=False)


# --------------------------------------------------------------------------- #
# storage guard
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class StorageGuard:
    ok: bool
    free_mb: int
    threshold_mb: int
    path: str
    reason: str | None = None

    def as_dict(self) -> dict:
        return {
            "ok": self.ok,
            "free_mb": self.free_mb,
            "threshold_mb": self.threshold_mb,
            "path": self.path,
            "reason": self.reason,
        }


def storage_guard(store: RawEvidenceStore | None = None) -> StorageGuard:
    """Free-space check against the *persistent* evidence volume."""
    store = store or RawEvidenceStore(settings.policy_collection_raw_dir or "crawler_output/policy_raw")
    path = Path(store.root)
    probe = path
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent
    threshold = max(0, settings.policy_collection_min_free_disk_mb)
    try:
        usage = shutil.disk_usage(str(probe))
    except OSError as exc:  # pragma: no cover - unusual, but must not crash a queue
        return StorageGuard(
            ok=False,
            free_mb=-1,
            threshold_mb=threshold,
            path=str(probe),
            reason=f"disk usage unreadable: {exc}",
        )
    free_mb = int(usage.free // (1024 * 1024))
    ok = free_mb >= threshold
    return StorageGuard(
        ok=ok,
        free_mb=free_mb,
        threshold_mb=threshold,
        path=str(probe),
        reason=None
        if ok
        else f"free space {free_mb}MB below threshold {threshold}MB; new downloads stopped",
    )


# --------------------------------------------------------------------------- #
# backlog / heartbeat
# --------------------------------------------------------------------------- #
def _source_states(db: Session) -> dict[str, PolicySourceState]:
    return {row.source_id: row for row in db.scalars(select(PolicySourceState))}


def backlog_report(db: Session, catalog: Catalog, *, now: datetime | None = None) -> dict:
    """Per-queue backlog, so ``status`` can answer "is anything stuck?"."""
    now = now or _utcnow()
    states = _source_states(db)
    enabled = [source for source in catalog.sources if source.enabled]

    incremental_due: list[str] = []
    backfill_pending: list[str] = []
    backfill_done: list[str] = []
    backfill_unsupported: list[str] = []
    paused: list[str] = []
    failed: list[str] = []

    for source in enabled:
        state = states.get(source.source_id)
        if state is not None and state.paused:
            paused.append(source.source_id)
            continue
        last_check = state.last_check_at if state is not None else None
        if last_check is None or now - last_check >= timedelta(hours=source.check_interval_hours):
            incremental_due.append(source.source_id)
        cursor = (state.cursor or {}).get("backfill") if state is not None else None
        if cursor:
            if cursor.get("exhausted"):
                backfill_done.append(source.source_id)
            elif cursor.get("unsupported_reason"):
                backfill_unsupported.append(source.source_id)
            else:
                backfill_pending.append(source.source_id)
        else:
            backfill_pending.append(source.source_id)
        if state is not None and (state.consecutive_failures or 0) >= 3:
            failed.append(source.source_id)

    running = db.scalar(
        select(func.count())
        .select_from(PolicyCollectionRun)
        .where(PolicyCollectionRun.status == "running")
    )
    return {
        "generated_at": now.isoformat(),
        "enabled_sources": len(enabled),
        "incremental_due": len(incremental_due),
        "incremental_due_sources": incremental_due[:50],
        "backfill_pending": len(backfill_pending),
        "backfill_done": len(backfill_done),
        "backfill_unsupported": len(backfill_unsupported),
        "paused_sources": len(paused),
        "sources_with_failures": len(failed),
        "runs_in_flight": int(running or 0),
        "pause": pause_state(db).scope,
    }


def heartbeat(db: Session, *, stale_after_minutes: int = 180) -> dict:
    """Liveness of the collection loop itself (not of individual sources)."""
    now = _utcnow()
    last_run_at = db.scalar(select(func.max(PolicyCollectionRun.started_at)))
    last_success = db.scalar(select(func.max(PolicyCollectionRun.finished_at)))
    evidence_rows = db.scalar(select(func.count()).select_from(PolicyRawEvidence)) or 0
    stale = True
    if last_run_at is not None:
        last_run = last_run_at if last_run_at.tzinfo else last_run_at.replace(tzinfo=UTC)
        stale = now - last_run > timedelta(minutes=stale_after_minutes)
    return {
        "checked_at": now.isoformat(),
        "last_run_started_at": last_run_at.isoformat() if last_run_at else None,
        "last_run_finished_at": last_success.isoformat() if last_success else None,
        "evidence_rows": int(evidence_rows),
        "stale": stale,
        "stale_after_minutes": stale_after_minutes,
        "pause": pause_state(db).scope,
    }


def prioritised_sources(
    catalog: Catalog, db: Session, *, limit: int | None = None
) -> list[SourceDefinition]:
    """Archive order: declaration notices first, then national, then provinces, then cities.

    Rationale: the 10,000-document target is counted as "independent policy files +
    independent declaration notices".  A notice that closed in 2019 has no
    application value today, but it is still a legitimate archive record, so it
    is ordered *after* the currently actionable material rather than dropped.
    """
    states = _source_states(db)
    level_rank = {"national": 0, "provincial": 1, "municipal": 2, "park": 3}

    def key(source: SourceDefinition) -> tuple:
        channel_rank = 0 if "notice" in (source.channel or "").lower() else 1
        state = states.get(source.source_id)
        cursor = (state.cursor or {}).get("backfill") if state is not None else None
        done = bool(cursor and cursor.get("exhausted"))
        unsupported = bool(cursor and cursor.get("unsupported_reason"))
        page = int((cursor or {}).get("page", 1)) if cursor else 1
        return (
            1 if done else 0,
            1 if unsupported else 0,
            channel_rank,
            level_rank.get(source.level, 4),
            page,
            source.source_id,
        )

    ordered = sorted((s for s in catalog.sources if s.enabled), key=key)
    return ordered[:limit] if limit else ordered
