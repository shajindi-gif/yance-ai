"""Restart-safe expiry scanner; provider uncertainty leaves the order untouched."""

import argparse
import signal
import threading

import structlog

from app.core.db import SessionLocal
from app.services.payments.lifecycle import expire_orders


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    stop = threading.Event()
    for signum in (signal.SIGINT, signal.SIGTERM):
        signal.signal(signum, lambda *_: stop.set())
    while not stop.is_set():
        try:
            with SessionLocal() as db:
                expire_orders(db)
        except Exception:
            structlog.get_logger().error("payment_expiry_cycle_failed")
        if args.once:
            return
        stop.wait(30)


if __name__ == "__main__":
    main()
