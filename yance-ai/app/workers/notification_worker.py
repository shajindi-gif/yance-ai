"""Optional deadline outbox processor. EMAIL_ENABLED and provider setup still apply."""

import argparse
import signal
import threading
from time import monotonic

import structlog

from app.core.db import SessionLocal
from app.core.logging import configure_logging
from app.services.notifications.deadlines import scan_deadlines
from app.services.notifications.email import dispatch_deadline_emails


def main() -> int:
    parser = argparse.ArgumentParser(description="Process durable deadline email intents")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--poll-seconds", type=float, default=10)
    args = parser.parse_args()
    stop = threading.Event()
    for signum in (signal.SIGTERM, signal.SIGINT):
        signal.signal(signum, lambda *_args: stop.set())
    configure_logging()
    logger = structlog.get_logger()
    logger.info("notification_worker_started")
    last_sweep = float("-inf")
    while not stop.is_set():
        try:
            with SessionLocal() as db:
                if monotonic() - last_sweep >= 3600:
                    scan_deadlines(db)
                    last_sweep = monotonic()
                # Keep the shutdown window bounded to one adapter call per cycle.
                dispatch_deadline_emails(db, limit=1)
        except Exception:
            logger.error("notification_worker_cycle_failed")
        if args.once:
            break
        stop.wait(max(args.poll_seconds, 0.1))
    logger.info("notification_worker_stopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
