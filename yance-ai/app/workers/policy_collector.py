"""Long-running supervisor for the continuous policy collector.

This is the process that makes "24/7" true without a shell loop pretending to be a
service: it is started by docker compose (or the systemd unit in
``ops/systemd/yance-policy-collector.service``), it survives a database restart,
it writes a heartbeat file the container healthcheck reads, and it stops *between*
documents on SIGTERM so no cursor is left half-written.

What it deliberately does **not** do:

* it never downloads when ``policy_collection_enabled`` is false;
* it never exceeds its cycle budget (a cycle is bounded, the loop is not a queue);
* it never wipes, migrates or resets anything — a collector that can repair the
  schema is a collector that can destroy the corpus.

Run it with::

    python -m app.workers.policy_collector              # serve until SIGTERM
    python -m app.workers.policy_collector --once       # one cycle, then exit
    python -m app.workers.policy_collector --status     # print state and exit
"""

from __future__ import annotations

import argparse
import json
import signal
import sys
import threading
import time
from datetime import UTC, datetime
from pathlib import Path

import structlog

from app.core.config import settings
from app.core.db import SessionLocal
from app.core.logging import configure_logging
from app.services.policy_collection.catalog import load_catalog
from app.services.policy_collection.ops import pause_state
from app.services.policy_collection.scheduler import SchedulerConfig, run_cycle


def _state_path() -> Path:
    """Heartbeat lives next to the raw evidence, on the persistent volume."""
    raw_dir = Path(settings.policy_collection_raw_dir or "crawler_output/policy_raw")
    raw_dir.mkdir(parents=True, exist_ok=True)
    return raw_dir / "collector_state.json"


def _write_state(**fields) -> None:
    path = _state_path()
    try:
        current = json.loads(path.read_text("utf-8")) if path.exists() else {}
    except (OSError, ValueError):
        current = {}
    current.update(fields)
    current["updated_at"] = datetime.now(UTC).isoformat()
    tmp = path.with_suffix(".tmp")
    # Atomic replace: a healthcheck must never read a half-written file.
    tmp.write_text(json.dumps(current, ensure_ascii=False, indent=2), "utf-8")
    tmp.replace(path)


def _catalog():
    return load_catalog(settings.policy_collection_catalog_dir)


def run_once(*, cycles: int = 1, stop_event: threading.Event | None = None) -> list[dict]:
    """Run ``cycles`` scheduling cycles, writing a heartbeat after each one."""
    log = structlog.get_logger()
    config = SchedulerConfig.from_settings()
    results: list[dict] = []

    for index in range(cycles):
        if stop_event is not None and stop_event.is_set():
            break
        db = SessionLocal()
        try:
            paused = pause_state(db)
            if paused.paused:
                # Reported, not raised: a pause is an operator action, not a fault.
                log.info("policy_collector_paused", scope=paused.scope)
                _write_state(
                    status="paused",
                    pause_scope=paused.scope,
                    last_cycle_at=datetime.now(UTC).isoformat(),
                    cycle_index=index,
                )
                break
            result = run_cycle(db, _catalog(), config=config)
            payload = result.as_dict()
            payload["cycle_index"] = index
            results.append(payload)
            _write_state(
                status="running",
                stop_reason=payload.get("stop_reason"),
                last_cycle_at=payload.get("finished_at") or datetime.now(UTC).isoformat(),
                cycle_index=index,
                ran=len(payload.get("ran") or []),
                skipped=len(payload.get("skipped") or []),
                due_after=payload.get("due_after"),
                storage=payload.get("storage"),
            )
            log.info(
                "policy_collector_cycle",
                stop_reason=payload.get("stop_reason"),
                ran=len(payload.get("ran") or []),
                skipped=len(payload.get("skipped") or []),
                due_after=payload.get("due_after"),
            )
        except Exception as exc:  # noqa: BLE001 - the supervisor must outlive one bad cycle
            log.error("policy_collector_cycle_failed", error=f"{type(exc).__name__}: {exc}")
            _write_state(
                status="error",
                last_cycle_at=datetime.now(UTC).isoformat(),
                last_error=f"{type(exc).__name__}: {exc}",
            )
            db.rollback()
        finally:
            db.close()

        if index + 1 < cycles:
            delay = max(0.0, float(settings.policy_collection_scheduler_interval_seconds))
            if stop_event is not None:
                stop_event.wait(delay)
            else:  # pragma: no cover - only in direct CLI use
                time.sleep(delay)
    return results


def print_status() -> int:
    path = _state_path()
    if not path.exists():
        print(f"no heartbeat yet at {path}")
        return 1
    print(path.read_text("utf-8"))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Continuous policy collection supervisor")
    parser.add_argument("--once", action="store_true", help="run a single cycle and exit")
    parser.add_argument("--cycles", type=int, default=0, help="stop after N cycles (0 = forever)")
    parser.add_argument("--status", action="store_true", help="print the heartbeat file and exit")
    args = parser.parse_args(argv)

    configure_logging()
    log = structlog.get_logger()

    if args.status:
        return print_status()

    if not settings.policy_collection_enabled:
        # Refusing loudly beats silently doing nothing in a loop: an operator who
        # forgot the master switch sees why immediately.
        log.warning("policy_collector_disabled", hint="set YANCE_POLICY_COLLECTION_ENABLED=true")
        _write_state(status="disabled", last_cycle_at=None)
        return 0

    stop_event = threading.Event()

    def _stop(signum, _frame):
        log.info("policy_collector_stopping", signal=signal.Signals(signum).name)
        stop_event.set()

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

    cycles = 1 if args.once else args.cycles
    log.info(
        "policy_collector_started",
        cycles=cycles or "forever",
        interval_seconds=settings.policy_collection_scheduler_interval_seconds,
        cycle_budget_seconds=settings.policy_collection_scheduler_cycle_seconds,
    )
    try:
        if cycles:
            run_once(cycles=cycles, stop_event=stop_event)
            return 0
        completed = 0
        while not stop_event.is_set():
            run_once(cycles=1, stop_event=stop_event)
            completed += 1
            stop_event.wait(max(1.0, float(settings.policy_collection_scheduler_interval_seconds)))
        log.info("policy_collector_stopped", cycles_completed=completed)
        _write_state(status="stopped", last_cycle_at=datetime.now(UTC).isoformat())
        return 0
    except KeyboardInterrupt:  # pragma: no cover - interactive use
        stop_event.set()
        return 0


if __name__ == "__main__":
    sys.exit(main())
