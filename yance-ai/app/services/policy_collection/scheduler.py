"""Incremental collection scheduler (the "always-on" half of the collector).

The backfill queue walks history once; this module is what keeps the evidence base
current afterwards. It is deliberately *not* a cron job that fires a fire-and-forget
script: a cycle is bounded, observable and restartable, so "24/7" means "the loop is
supervised and can prove it ran", not "we hammer government sites all day".

Design decisions that matter operationally:

* **Bounded cycle.** A cycle stops at ``max_sources`` and at ``cycle_seconds``.
  Whatever is left over stays ``due`` and is picked up by the next cycle. A long
  government site stall therefore cannot eat the whole schedule.
* **One bad source never stops the loop.** Exceptions are recorded per source and
  the cycle continues; the failure counter then feeds :func:`alerts`.
* **Exhausted archives are re-checked slowly, not re-read.** A source that declared
  its archive finished is re-requested only after ``recheck_interval_hours`` and
  only with conditional headers, which is what turns a 22-screen archive into one
  ``304 Not Modified``.
* **Pause and disk alarms are honoured before any request.** Both are checked at the
  top of the cycle and again before each source, so a human pause takes effect
  within one document rather than within one cycle.
* **No scheduler-only database table.** Heartbeat state lives next to the raw store
  as JSON. That keeps deployment free of a new migration and still gives monitoring
  something concrete to read.
"""

from __future__ import annotations

import json
import logging
import signal
import threading
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import settings
from app.services.policy_collection.catalog import Catalog, SourceDefinition
from app.services.policy_collection.ops import pause_state, storage_guard
from app.services.policy_collection.service import (
    PolicySourceState,
    due_sources,
    execute_source_run,
    promote_ready_documents,
)

log = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# configuration
# --------------------------------------------------------------------------- #
@dataclass
class SchedulerConfig:
    interval_seconds: float = 300.0
    cycle_seconds: float = 600.0
    max_sources_per_cycle: int = 12
    recheck_interval_hours: float = 168.0
    state_path: Path | None = None

    @classmethod
    def from_settings(cls, **overrides) -> "SchedulerConfig":
        config = cls(
            interval_seconds=float(settings.policy_collection_scheduler_interval_seconds),
            cycle_seconds=float(settings.policy_collection_scheduler_cycle_seconds),
            max_sources_per_cycle=int(settings.policy_collection_scheduler_max_sources_per_cycle),
            recheck_interval_hours=float(settings.policy_collection_recheck_interval_hours),
            state_path=_default_state_path(),
        )
        for key, value in overrides.items():
            if value is not None:
                setattr(config, key, value)
        return config


def _default_state_path() -> Path:
    configured = (settings.policy_collection_alerts_json_path or "").strip()
    if configured:
        return Path(configured).expanduser()
    raw_dir = (settings.policy_collection_raw_dir or "").strip()
    if raw_dir:
        return Path(raw_dir).expanduser() / "scheduler_state.json"
    root = Path(__file__).resolve().parents[3]
    return root / "crawler_output" / "policy_raw" / "scheduler_state.json"


# --------------------------------------------------------------------------- #
# due selection
# --------------------------------------------------------------------------- #
def _naive_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def recheck_due(
    catalog: Catalog, db: Session, *, state_path: Path, now: datetime | None = None, interval_hours: float = 168.0
) -> list[SourceDefinition]:
    """Archives declared finished long enough ago to deserve a cheap re-check.

    Only sources whose cursor says ``exhausted`` qualify. This is what discovers a
    newly opened declaration window without re-reading years of old notices.
    """
    moment = now or datetime.now(UTC)
    checked = _read_state(state_path).get("rechecked_at", {})
    states = {row.source_id: row for row in db.query(PolicySourceState).all()}
    result: list[SourceDefinition] = []
    for source in catalog.sources:
        if not source.enabled:
            continue
        state = states.get(source.source_id)
        if state is None or state.paused:
            continue
        cursor = (state.cursor or {}).get("backfill") or {}
        if not cursor.get("exhausted"):
            continue
        last_raw = checked.get(source.source_id)
        last = _naive_utc(datetime.fromisoformat(last_raw)) if last_raw else _naive_utc(state.last_check_at)
        if last is None or moment - last >= timedelta(hours=interval_hours):
            result.append(source)
    return result


# --------------------------------------------------------------------------- #
# state file
# --------------------------------------------------------------------------- #
def _read_state(state_path: Path | None) -> dict:
    if state_path is None or not state_path.exists():
        return {}
    try:
        return json.loads(state_path.read_text("utf-8"))
    except (OSError, ValueError):  # pragma: no cover - corrupt state must not stop the loop
        return {}


def _write_state(state_path: Path | None, payload: dict) -> None:
    if state_path is None:
        return
    try:
        state_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = state_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), "utf-8")
        tmp.replace(state_path)
    except OSError as exc:  # pragma: no cover - logging only
        log.warning("scheduler state not persisted: %s", exc)


# --------------------------------------------------------------------------- #
# one cycle
# --------------------------------------------------------------------------- #
@dataclass
class CycleResult:
    started_at: str
    finished_at: str
    stop_reason: str = "completed"
    ran: list[dict] = field(default_factory=list)
    skipped: list[dict] = field(default_factory=list)
    due_before: int = 0
    due_after: int = 0
    rechecked: list[dict] = field(default_factory=list)
    storage: dict | None = None

    def as_dict(self) -> dict:
        return {
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "stop_reason": self.stop_reason,
            "due_before": self.due_before,
            "due_after": self.due_after,
            "ran": self.ran,
            "skipped": self.skipped,
            "rechecked": self.rechecked,
            "storage": self.storage,
        }


def _priority_key(source: SourceDefinition, states: dict[str, PolicySourceState]) -> tuple:
    state = states.get(source.source_id)
    failures = state.consecutive_failures if state is not None else 0
    last_search = _naive_utc(state.last_check_at) if state is not None else None
    channel = (source.channel or "").lower()
    # Declaration notices first: they carry application windows that expire.
    channel_rank = 0 if channel in {"application", "notice"} else 1
    return (
        channel_rank,
        failures,
        last_search or datetime(1970, 1, 1, tzinfo=UTC),
        source.source_id,
    )


def run_cycle(
    db: Session,
    catalog: Catalog,
    *,
    config: SchedulerConfig | None = None,
    now: datetime | None = None,
    include_recheck: bool = True,
    execute=None,
) -> CycleResult:
    """Run one bounded incremental cycle.

    ``execute`` is injectable so the whole cycle can be tested without a network
    request, which is the only way to assert the guard behaviour reliably.
    """
    config = config or SchedulerConfig.from_settings()
    run_source = execute or execute_source_run
    moment = now or datetime.now(UTC)
    result = CycleResult(started_at=moment.isoformat(), finished_at=moment.isoformat())

    if not settings.policy_collection_enabled:
        # Nothing to schedule while the master switch is off; recording 90 skipped
        # rows per cycle would only train everyone to ignore the log.
        result.stop_reason = "collection_disabled"
        result.due_before = len(due_sources(catalog, db, now=moment))
        result.due_after = result.due_before
        result.finished_at = datetime.now(UTC).isoformat()
        return result

    pause = pause_state(db)
    if pause.paused:
        result.stop_reason = "paused"
        result.due_before = len(due_sources(catalog, db, now=moment))
        result.due_after = result.due_before
        result.finished_at = datetime.now(UTC).isoformat()
        return result

    guard = storage_guard()
    result.storage = guard.as_dict()
    if not guard.ok:
        result.stop_reason = "storage_full"
        result.due_before = len(due_sources(catalog, db, now=moment))
        result.due_after = result.due_before
        result.finished_at = datetime.now(UTC).isoformat()
        return result

    due = due_sources(catalog, db, now=moment)
    result.due_before = len(due)
    states = {row.source_id: row for row in db.query(PolicySourceState).all()}
    ordered = sorted(due, key=lambda source: _priority_key(source, states))

    deadline = time.monotonic() + max(1.0, config.cycle_seconds)
    rechecked_ids = set(_read_state(config.state_path).get("rechecked_at", {}))

    for source in ordered:
        if len(result.ran) >= config.max_sources_per_cycle:
            result.stop_reason = "max_sources"
            break
        if len(result.skipped) >= 200:
            result.stop_reason = "skip_cap"
            break
        if time.monotonic() >= deadline:
            result.stop_reason = "time_budget"
            break
        # Re-checked immediately before each source: a pause or a filling disk must
        # take effect within one document, not within one cycle.
        if pause_state(db, source.source_id).paused:
            result.skipped.append({"source_id": source.source_id, "reason": "paused"})
            continue
        if not storage_guard().ok:
            result.stop_reason = "storage_full"
            break
        try:
            report = run_source(db, source, trigger="scheduler")
        except Exception as exc:  # noqa: BLE001 - one source must never kill the loop
            log.warning("source cycle failed: %s: %s", source.source_id, exc)
            result.ran.append({"source_id": source.source_id, "status": "exception", "error": str(exc)[:300]})
            continue
        if report.skipped_reason:
            result.skipped.append({"source_id": source.source_id, "reason": report.skipped_reason})
            continue
        outcome = report.outcome
        result.ran.append(
            {
                "source_id": source.source_id,
                "status": report.status,
                "new": getattr(outcome, "new_documents", 0),
                "updated": getattr(outcome, "updated_documents", 0),
                "failed": getattr(outcome, "failed_documents", 0),
                "pages": getattr(outcome, "pages_fetched", 0),
            }
        )

    if include_recheck and result.stop_reason == "completed":
        for source in recheck_due(
            catalog,
            db,
            state_path=config.state_path,
            now=moment,
            interval_hours=config.recheck_interval_hours,
        ):
            if len(result.ran) >= config.max_sources_per_cycle or time.monotonic() >= deadline:
                break
            try:
                report = run_source(db, source, trigger="recheck")
            except Exception as exc:  # noqa: BLE001
                result.rechecked.append({"source_id": source.source_id, "status": "exception", "error": str(exc)[:200]})
                continue
            result.rechecked.append(
                {"source_id": source.source_id, "status": report.status, "new": getattr(report.outcome, "new_documents", 0)}
            )
            rechecked_ids.add(source.source_id)

    # Publication gate.  ``collected`` is deliberate (nothing reaches a customer
    # unreviewed) but it is also *invisible*: retrieval only serves published
    # versions.  Nothing used to call the gate, so every crawled document stayed in
    # ``collected`` forever and the web search box never showed a single one of
    # them.  Running it inside the cycle is what makes "collected" mean "waiting a
    # few minutes" instead of "never".
    try:
        promotion = promote_ready_documents(db, limit=200)
        if promotion.published or promotion.held_for_review:
            log.info("publication gate: %s", promotion.as_dict())
    except Exception as exc:  # noqa: BLE001 - promotion must never kill collection
        log.warning("publication gate failed: %s", exc)

    result.due_after = len(due_sources(catalog, db, now=datetime.now(UTC)))
    result.finished_at = datetime.now(UTC).isoformat()

    state = _read_state(config.state_path)
    state.update(
        {
            "last_cycle_started_at": result.started_at,
            "last_cycle_finished_at": result.finished_at,
            "last_stop_reason": result.stop_reason,
            "due_after": result.due_after,
            "pid": None,
            "rechecked_at": {
                source_id: (state.get("rechecked_at", {}).get(source_id) or result.finished_at)
                for source_id in rechecked_ids
            },
        }
    )
    _write_state(config.state_path, state)
    return result


# --------------------------------------------------------------------------- #
# long-running loop
# --------------------------------------------------------------------------- #
def scheduler_state(config: SchedulerConfig | None = None) -> dict:
    config = config or SchedulerConfig.from_settings()
    return _read_state(config.state_path)


def serve(
    db_factory,
    catalog_loader,
    *,
    config: SchedulerConfig | None = None,
    max_cycles: int | None = None,
    stop_event: threading.Event | None = None,
) -> list[dict]:
    """Run cycles forever (or ``max_cycles`` times) until SIGTERM/SIGINT.

    ``db_factory`` and ``catalog_loader`` are callables so the loop can reconnect
    after a database restart instead of dying with a stale session.
    """
    config = config or SchedulerConfig.from_settings()
    stop_event = stop_event or threading.Event()
    previous = {}

    def _handle(signum, _frame):  # pragma: no cover - signal path
        log.info("scheduler received signal %s, finishing current source", signum)
        stop_event.set()

    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            previous[sig] = signal.signal(sig, _handle)
        except (ValueError, OSError):  # pragma: no cover - not the main thread
            pass

    history: list[dict] = []
    cycles = 0
    try:
        state = _read_state(config.state_path)
        state.update({"pid": None, "started_at": datetime.now(UTC).isoformat()})
        _write_state(config.state_path, state)
        while not stop_event.is_set():
            catalog = catalog_loader()
            db = db_factory()
            try:
                result = run_cycle(db, catalog, config=config)
            finally:
                db.close()
            history.append(result.as_dict())
            cycles += 1
            state = _read_state(config.state_path)
            state["last_cycle"] = result.as_dict()
            _write_state(config.state_path, state)
            if max_cycles is not None and cycles >= max_cycles:
                break
            stop_event.wait(config.interval_seconds)
    finally:
        for sig, handler in previous.items():
            try:
                signal.signal(sig, handler)
            except (ValueError, OSError):  # pragma: no cover
                pass
    return history


# --------------------------------------------------------------------------- #
# alerts
# --------------------------------------------------------------------------- #
def alerts(
    db: Session,
    catalog: Catalog,
    *,
    now: datetime | None = None,
    failure_threshold: int | None = None,
    stale_hours: float | None = None,
) -> list[dict]:
    """Actionable health problems, one row per issue.

    The point is that a source can fail for weeks without touching the catalog (by
    design, a transient failure must not rewrite a source's verdict), so the *state*
    table is the only place that can reveal a permanently broken adapter. Without
    this function that silence looks like success.
    """
    moment = now or datetime.now(UTC)
    threshold = failure_threshold if failure_threshold is not None else settings.policy_collection_alert_failure_threshold
    stale_after = stale_hours if stale_hours is not None else settings.policy_collection_alert_stale_hours
    states = {row.source_id: row for row in db.query(PolicySourceState).all()}
    found: list[dict] = []

    for source in catalog.sources:
        if not source.enabled:
            continue
        state = states.get(source.source_id)
        if state is None:
            continue
        failures = state.consecutive_failures or 0
        if failures >= threshold:
            found.append(
                {
                    "kind": "persistent_failure",
                    "source_id": source.source_id,
                    "consecutive_failures": failures,
                    "last_error_kind": state.last_error_kind,
                    "last_error": (state.last_error or "")[:200],
                    "action": "inspect adapter/selector; source is excluded from new downloads until fixed",
                }
            )
        last_success = _naive_utc(state.last_success_at)
        if last_success is not None and moment - last_success >= timedelta(hours=stale_after):
            found.append(
                {
                    "kind": "stale_source",
                    "source_id": source.source_id,
                    "hours_since_success": round((moment - last_success).total_seconds() / 3600, 1),
                    "action": "check whether the column moved or now requires a different adapter",
                }
            )
        cursor = (state.cursor or {}).get("backfill") or {}
        if cursor.get("gap_reason"):
            found.append(
                {
                    "kind": "unverified_page_gap",
                    "source_id": source.source_id,
                    "gap_reason": cursor.get("gap_reason"),
                    "page": cursor.get("page"),
                    "action": "history may be missing behind an empty page; verify manually",
                }
            )

    guard = storage_guard()
    if not guard.ok:
        found.append({"kind": "disk_low", **guard.as_dict(), "action": "new downloads are stopped"})

    # A disabled master switch is a *deliberate* state, but it is worth reporting
    # here rather than in the cycle log: with collection off, every other alert
    # ("stale source", "no new documents") is a consequence, not a new problem.
    if not settings.policy_collection_enabled:
        found.append(
            {
                "kind": "collection_disabled",
                "due_sources": len(due_sources(catalog, db, now=moment)),
                "action": "set POLICY_COLLECTION_ENABLED=true to resume scheduling",
            }
        )

    pause = pause_state(db)
    if pause.paused:
        found.append({"kind": "paused", "scope": pause.scope, "action": "collection is stopped on purpose"})
    return found
