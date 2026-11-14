"""Daily 03:00 Asia/Shanghai start, retrying statements that are generated later."""

import argparse
import json
import signal
import threading
import uuid
from datetime import date, datetime, timedelta
from time import monotonic
from zoneinfo import ZoneInfo

from app.core.config import settings
from app.core.db import SessionLocal
from app.models.models import User
from app.services.notifications.outbox import dispatch_outbox
from app.services.payments.reconciliation import reconcile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", type=date.fromisoformat)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--daemon", action="store_true")
    args = parser.parse_args()
    stop = threading.Event()
    for signum in (signal.SIGINT, signal.SIGTERM):
        signal.signal(signum, lambda *_: stop.set())
    last_attempt = float("-inf")
    while not stop.is_set():
        now = datetime.now(ZoneInfo("Asia/Shanghai"))
        if not args.daemon or (now.hour >= 3 and monotonic() - last_attempt >= 3600):
            day = args.date or now.date() - timedelta(days=1)
            failed = False
            for provider in ("alipay", "wechat"):
                try:
                    with SessionLocal() as db:
                        result = reconcile(db, provider, day, dry_run=args.dry_run)
                except Exception:
                    result = {"provider": provider, "status": "failed", "error": "reconciliation_cycle_failed"}
                failed = failed or result["status"] != "matched"
                print(json.dumps(result), flush=True)
            if not args.dry_run and settings.payment_ops_user_id:
                with SessionLocal() as db:
                    user = db.get(User, uuid.UUID(settings.payment_ops_user_id))
                    if user and user.is_platform_admin:
                        dispatch_outbox(db, tenant_id=user.tenant_id, limit=3, kind="payment_reconciliation")
            last_attempt = monotonic()
        if not args.daemon:
            return int(failed)
        stop.wait(60)


if __name__ == "__main__":
    raise SystemExit(main())
