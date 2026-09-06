import argparse
import time

from app.core.config import settings
from app.core.db import SessionLocal
from app.services.documents.ingestion import claim_next_ingestion, process_ingestion
from app.services.oss import get_oss_storage


def run_once() -> bool:
    storage = get_oss_storage()
    with SessionLocal() as db:
        run = claim_next_ingestion(db)
        if not run:
            return False
        process_ingestion(db, run.id, storage, claimed=True)
        return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Yance document ingestion worker")
    parser.add_argument("--once", action="store_true", help="Claim at most one run and exit")
    parser.add_argument("--poll-seconds", type=float, default=settings.agent_worker_poll_seconds)
    args = parser.parse_args()
    while True:
        processed = run_once()
        if args.once:
            return
        if not processed:
            time.sleep(max(args.poll_seconds, 0.1))


if __name__ == "__main__":
    main()
