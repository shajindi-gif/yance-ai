import argparse
import asyncio
import signal

import structlog

from app.core.config import settings
from app.core.logging import configure_logging
from app.services.agents.harness import run_agent_worker


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Yance durable Agent worker")
    parser.add_argument("--once", action="store_true", help="Claim at most one run and exit")
    parser.add_argument("--poll-seconds", type=float, default=settings.agent_worker_poll_seconds)
    args = parser.parse_args()
    configure_logging()
    logger = structlog.get_logger()
    received = {"signal": signal.SIGINT}

    def stop(signum, _frame):
        received["signal"] = signum
        raise KeyboardInterrupt

    try:
        signal.signal(signal.SIGTERM, stop)
        logger.info("agent_worker_started")
        asyncio.run(run_agent_worker(poll_seconds=max(0.1, args.poll_seconds), once=args.once))
    except KeyboardInterrupt:
        logger.info("agent_worker_stopped", signal=signal.Signals(received["signal"]).name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
