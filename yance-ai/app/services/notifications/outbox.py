"""Durable deadline email intents; no exactly-once claim for SMTP/HTTP.

A crash after external acceptance is ambiguous. Expired sending leases and
unknown provider outcomes are quarantined as uncertain, never blindly retried.
"""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import exists, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.models import Membership, Notification, NotificationDelivery, Tenant, User, UserRole
from app.services.notifications import email

MAX_ATTEMPTS = 4
LEASE_SECONDS = 120


def enqueue_deadline_emails(db: Session, *, tenant_id=None, limit: int = 200) -> int:
    delivered = exists(
        select(NotificationDelivery.id).where(
            NotificationDelivery.notification_id == Notification.id,
            NotificationDelivery.recipient_user_id == User.id,
        )
    )
    query = (
        select(Notification, User)
        .join(User, User.tenant_id == Notification.tenant_id)
        .join(
            Membership,
            (Membership.user_id == User.id) & (Membership.tenant_id == Notification.tenant_id),
        )
        .join(Tenant, Tenant.id == Notification.tenant_id)
        .where(
            Notification.kind == "deadline",
            Notification.severity.in_(email.EMAIL_BANDS),
            Notification.read_at.is_(None),
            ~Notification.dedup_key.endswith(":emailed"),
            User.is_active.is_(True),
            User.email.is_not(None),
            Tenant.is_active.is_(True),
            Membership.status == "active",
            or_(
                (
                    Notification.user_id.is_(None)
                    & Membership.role.in_([UserRole.owner, UserRole.admin])
                ),
                Notification.user_id == User.id,
            ),
            ~delivered,
        )
        .order_by(Notification.created_at, Notification.id, User.id)
        .limit(min(max(limit, 1), 200))
    )
    if tenant_id:
        query = query.where(Notification.tenant_id == tenant_id)
    count = 0
    for notification, user in db.execute(query).all():
        result = db.execute(
            insert(NotificationDelivery)
            .values(
                tenant_id=notification.tenant_id,
                notification_id=notification.id,
                recipient_user_id=user.id,
                recipient_email=user.email,
                payload_json={
                    "title": notification.title,
                    "body": notification.body or notification.title,
                },
                status="pending",
                attempt_count=0,
                next_attempt_at=datetime.now(UTC),
            )
            .on_conflict_do_nothing(constraint="uq_notification_delivery_recipient")
            .returning(NotificationDelivery.id)
        )
        count += int(result.scalar_one_or_none() is not None)
    db.commit()
    return count


def _recover_expired(db: Session, tenant_id=None) -> None:
    query = (
        select(NotificationDelivery)
        .where(
            NotificationDelivery.status == "sending",
            NotificationDelivery.lease_expires_at <= datetime.now(UTC),
        )
        .with_for_update(skip_locked=True)
        .limit(200)
    )
    if tenant_id:
        query = query.where(NotificationDelivery.tenant_id == tenant_id)
    for delivery in db.scalars(query).all():
        delivery.status = "uncertain"
        delivery.error_code = "send_interrupted_requires_review"
        delivery.lease_token = None
        delivery.lease_expires_at = None
    db.commit()


def _authorized(db: Session, delivery: NotificationDelivery) -> bool:
    notification = db.scalar(
        select(Notification).where(
            Notification.id == delivery.notification_id,
            Notification.tenant_id == delivery.tenant_id,
        )
    )
    if (
        not notification
        or notification.read_at
        or notification.kind != "deadline"
        or notification.severity not in email.EMAIL_BANDS
    ):
        return False
    query = (
        select(User.id)
        .join(Membership, Membership.user_id == User.id)
        .join(Tenant, Tenant.id == User.tenant_id)
        .where(
            User.id == delivery.recipient_user_id,
            User.tenant_id == delivery.tenant_id,
            User.email == delivery.recipient_email,
            User.is_active.is_(True),
            Tenant.is_active.is_(True),
            Membership.tenant_id == delivery.tenant_id,
            Membership.status == "active",
        )
    )
    if notification.user_id:
        query = query.where(User.id == notification.user_id)
    else:
        query = query.where(Membership.role.in_([UserRole.owner, UserRole.admin]))
    return db.scalar(query) is not None


def dispatch_outbox(db: Session, *, tenant_id=None, limit: int = 20) -> int:
    _recover_expired(db, tenant_id)
    if not email.is_email_configured():
        return 0
    sent = 0
    for _ in range(min(max(limit, 1), 20)):
        query = (
            select(NotificationDelivery)
            .where(
                NotificationDelivery.status == "pending",
                NotificationDelivery.next_attempt_at <= datetime.now(UTC),
            )
            .order_by(NotificationDelivery.created_at, NotificationDelivery.id)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if tenant_id:
            query = query.where(NotificationDelivery.tenant_id == tenant_id)
        delivery = db.scalar(query.execution_options(populate_existing=True))
        if not delivery:
            db.rollback()
            break
        if not _authorized(db, delivery):
            delivery.status = "suppressed"
            delivery.error_code = "recipient_or_notification_no_longer_authorized"
            db.commit()
            continue
        if delivery.attempt_count >= MAX_ATTEMPTS:
            delivery.status = "failed"
            delivery.error_code = "retry_limit_reached"
            db.commit()
            continue
        token = uuid.uuid4()
        delivery.status = "sending"
        delivery.lease_token = token
        delivery.lease_expires_at = datetime.now(UTC) + timedelta(seconds=LEASE_SECONDS)
        delivery.attempt_count += 1
        delivery_id = delivery.id
        recipient, payload = delivery.recipient_email, dict(delivery.payload_json)
        db.commit()  # Intent and claim survive a process crash before the network call.
        try:
            outcome = email.send_notification_email(recipient, payload["title"], payload["body"])
        except Exception:  # No response bodies, addresses or credentials in errors.
            outcome = email.DeliveryOutcome("uncertain", "transport_exception")
        current = db.scalar(
            select(NotificationDelivery)
            .where(
                NotificationDelivery.id == delivery_id,
                NotificationDelivery.lease_token == token,
                NotificationDelivery.status == "sending",
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if not current:
            db.rollback()
            continue
        current.lease_token = None
        current.lease_expires_at = None
        current.error_code = outcome.code
        if outcome.status == "sent":
            current.status = "sent"
            current.sent_at = datetime.now(UTC)
            sent += 1
        elif outcome.status in {"retryable", "deferred"} and current.attempt_count < MAX_ATTEMPTS:
            current.status = "pending"
            current.next_attempt_at = datetime.now(UTC) + timedelta(
                seconds=min(3600, 30 * 2**current.attempt_count)
            )
        else:
            current.status = "uncertain" if outcome.status == "uncertain" else "failed"
        db.commit()
    return sent
