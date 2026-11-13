"""Compare provider facts to local records without manufacturing a settlement."""

import hashlib
import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import (
    Membership,
    Notification,
    NotificationDelivery,
    Payment,
    ReconciliationIssue,
    ReconciliationRun,
    Refund,
    User,
)
from app.services.notifications.deadlines import add_notification
from app.services.payments.bills import BillRecord


def compare(db: Session, provider: str, day: date, rows: list[BillRecord]) -> list[dict]:
    issues = []
    seen = set()
    for row in rows:
        payment = db.scalar(
            select(Payment).where(
                Payment.provider == provider, Payment.provider_trade_no == row.reference
            )
        )
        key = (row.reference, row.kind, row.refund_reference or row.transaction)
        if key in seen:
            raise ValueError("Duplicate provider bill record")
        seen.add(key)
        issue = {"reference": row.reference, "received_amount": row.amount}
        if not payment:
            issues.append(
                {**issue, "issue_type": "unattributed_merchant_trade", "expected_amount": None}
            )
            continue
        expected = Decimal(str(payment.amount))
        if expected != row.amount or payment.currency != "CNY":
            issues.append(
                {**issue, "issue_type": "amount_or_currency_mismatch", "expected_amount": expected}
            )
        if row.kind == "paid":
            if payment.status != "completed":
                issues.append(
                    {
                        **issue,
                        "issue_type": "provider_paid_local_unsettled",
                        "expected_amount": expected,
                    }
                )
            local_transaction = (
                payment.alipay_trade_no
                if provider == "alipay"
                else (payment.raw_response or {}).get("transaction_id")
            )
            if local_transaction and local_transaction != row.transaction:
                issues.append(
                    {**issue, "issue_type": "transaction_mismatch", "expected_amount": expected}
                )
        else:
            refund = db.scalar(select(Refund).where(Refund.order_id == payment.order_id))
            if not refund or refund.status != "succeeded":
                issues.append(
                    {
                        **issue,
                        "issue_type": "provider_refunded_local_unconfirmed",
                        "expected_amount": expected,
                    }
                )
            elif provider == "wechat" and (
                refund.provider_refund_id != row.transaction
                or refund.provider_refund_no != row.refund_reference
            ):
                issues.append(
                    {
                        **issue,
                        "issue_type": "refund_reference_mismatch",
                        "expected_amount": expected,
                    }
                )
    zone = ZoneInfo("Asia/Shanghai")
    start = datetime.combine(day, datetime.min.time(), tzinfo=zone)
    end = start + timedelta(days=1)
    for payment in db.scalars(
        select(Payment).where(
            Payment.provider == provider,
            Payment.status == "completed",
            Payment.paid_at >= start,
            Payment.paid_at < end,
        )
    ):
        if not any(
            row.reference == payment.provider_trade_no and row.kind == "paid" for row in rows
        ):
            issues.append(
                {
                    "reference": payment.provider_trade_no or str(payment.id),
                    "issue_type": "local_paid_missing_from_bill",
                    "expected_amount": payment.amount,
                    "received_amount": None,
                }
            )
    return issues


def enqueue_alert(db: Session, run: ReconciliationRun) -> bool:
    if not settings.payment_ops_user_id:
        return False
    try:
        user = db.get(User, uuid.UUID(settings.payment_ops_user_id))
    except ValueError:
        return False
    if not user or not user.is_platform_admin or not user.is_active or not user.email:
        return False
    member = db.scalar(
        select(Membership).where(
            Membership.user_id == user.id,
            Membership.tenant_id == user.tenant_id,
            Membership.status == "active",
        )
    )
    if not member:
        return False
    key = f"payment-reconciliation:{run.provider}:{run.bill_date}:{run.issue_count}:{run.status}"
    add_notification(
        db,
        tenant_id=user.tenant_id,
        user_id=user.id,
        kind="payment_reconciliation",
        severity="critical",
        title="支付对账需要核对",
        body=f"{run.provider} {run.bill_date}：状态{run.status}，差异{run.issue_count}项。请按支付运维手册核对，勿直接修改历史金额。",
        dedup_key=key,
    )
    notification = db.scalar(
        select(Notification).where(
            Notification.tenant_id == user.tenant_id, Notification.dedup_key == key
        )
    )
    db.execute(
        insert(NotificationDelivery)
        .values(
            tenant_id=user.tenant_id,
            notification_id=notification.id,
            recipient_user_id=user.id,
            recipient_email=user.email,
            payload_json={"title": notification.title, "body": notification.body},
            status="pending",
            attempt_count=0,
            next_attempt_at=datetime.now(UTC),
        )
        .on_conflict_do_nothing(constraint="uq_notification_delivery_recipient")
    )
    return True


def reconcile(db: Session, provider: str, day: date, *, dry_run: bool = False) -> dict:
    from app.services.payments.bills import download_bill, parse_bill

    lock = int.from_bytes(
        hashlib.sha256(f"bill:{provider}:{day}".encode()).digest()[:8], "big", signed=True
    )
    if not db.scalar(text("SELECT pg_try_advisory_xact_lock(:key)"), {"key": lock}):
        return {"provider": provider, "status": "busy"}
    run = db.scalar(
        select(ReconciliationRun).where(
            ReconciliationRun.provider == provider, ReconciliationRun.bill_date == day
        )
    )
    try:
        raw = download_bill(provider, day)
        rows = parse_bill(provider, raw)
        issues = compare(db, provider, day, rows)
        missing_time = (
            db.scalar(
                select(Payment.id)
                .where(
                    Payment.provider == provider,
                    Payment.status == "completed",
                    Payment.paid_at.is_(None),
                )
                .limit(1)
            )
            is not None
        )
        status = "partial" if missing_time else "differences" if issues else "matched"
        error = "legacy_provider_time_unknown" if missing_time else None
        digest = hashlib.sha256(raw).hexdigest()
    except Exception:
        db.rollback()
        if not db.scalar(text("SELECT pg_try_advisory_xact_lock(:key)"), {"key": lock}):
            return {"provider": provider, "status": "busy"}
        if dry_run:
            return {
                "provider": provider,
                "status": "waiting",
                "error": "bill_unavailable_or_unverified",
            }
        run = db.scalar(
            select(ReconciliationRun)
            .where(ReconciliationRun.provider == provider, ReconciliationRun.bill_date == day)
            .with_for_update()
        )
        status, error, digest, issues = "waiting", "bill_unavailable_or_unverified", None, []
    if dry_run:
        db.rollback()
        return {"provider": provider, "status": status, "issues": len(issues), "error": error}
    if not run:
        run = ReconciliationRun(provider=provider, bill_date=day)
        db.add(run)
    run.status = status
    run.error_code = error
    run.last_attempt_at = datetime.now(UTC)
    if status != "waiting":
        run.source_sha256 = digest
        run.issue_count = len(issues)
        current = {(item["reference"], item["issue_type"]) for item in issues}
        for old in db.scalars(
            select(ReconciliationIssue).where(
                ReconciliationIssue.provider == provider, ReconciliationIssue.bill_date == day
            )
        ):
            if (old.reference, old.issue_type) not in current:
                old.status = "resolved"
        for issue in issues:
            db.execute(
                insert(ReconciliationIssue)
                .values(id=uuid.uuid4(), provider=provider, bill_date=day, status="open", **issue)
                .on_conflict_do_update(
                    constraint="uq_reconciliation_issue",
                    set_={
                        "status": "open",
                        "expected_amount": issue["expected_amount"],
                        "received_amount": issue["received_amount"],
                    },
                )
            )
    if status != "matched" and not enqueue_alert(db, run):
        run.error_code = error or "ops_recipient_not_configured"
    db.commit()
    return {"provider": provider, "status": status, "issues": len(issues), "error": run.error_code}
