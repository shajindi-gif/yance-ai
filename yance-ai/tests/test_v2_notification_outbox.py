"""Synthetic recipients; every delivery adapter is replaced, no external sends."""

import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.core.db import SessionLocal
from app.models.models import Membership, Notification, NotificationDelivery, Tenant, User
from app.services.notifications import email
from app.services.notifications.deadlines import add_notification
from app.services.notifications.outbox import dispatch_outbox, enqueue_deadline_emails

pytestmark = pytest.mark.skipif(
    os.getenv("APP_ENV") != "test", reason="isolated PostgreSQL required"
)


def _notice(*, recipients=1, target=False, legacy=False):
    with SessionLocal() as db:
        tenant = Tenant(name="Synthetic outbox tenant", slug=uuid.uuid4().hex)
        db.add(tenant)
        db.flush()
        users = []
        for index in range(recipients):
            user = User(
                tenant_id=tenant.id,
                email=f"outbox-{uuid.uuid4().hex}@example.invalid",
                full_name="Synthetic recipient",
                password_hash="not-used",
                role="owner" if index == 0 else "admin",
            )
            db.add(user)
            db.flush()
            db.add(
                Membership(tenant_id=tenant.id, user_id=user.id, role=user.role, status="active")
            )
            users.append(user)
        key = f"deadline:synthetic:{uuid.uuid4()}"
        notification = Notification(
            tenant_id=tenant.id,
            user_id=users[0].id if target else None,
            kind="deadline",
            severity="warning",
            title="合成提醒",
            body="仅测试",
            dedup_key=key + (":emailed" if legacy else ""),
        )
        db.add(notification)
        db.commit()
        return tenant.id, notification.id, key, [(user.id, user.email) for user in users]


@pytest.fixture(autouse=True)
def fake_delivery(monkeypatch):
    monkeypatch.setattr(email, "is_email_configured", lambda: True)

    def forbidden(*_args):
        raise AssertionError("Test must explicitly replace the delivery outcome")

    monkeypatch.setattr(email, "send_notification_email", forbidden)


def test_partial_recipient_failure_retries_only_that_recipient(monkeypatch):
    tenant, notification, key, users = _notice(recipients=2)
    calls = []

    def deliver(to, *_args):
        calls.append(to)
        return (
            email.DeliveryOutcome("retryable", "synthetic_rate_limit")
            if to == users[1][1] and calls.count(to) == 1
            else email.DeliveryOutcome("sent")
        )

    monkeypatch.setattr(email, "send_notification_email", deliver)
    with SessionLocal() as db:
        assert enqueue_deadline_emails(db, tenant_id=tenant) == 2
        assert dispatch_outbox(db, tenant_id=tenant) == 1
        pending = db.scalar(
            select(NotificationDelivery).where(
                NotificationDelivery.notification_id == notification,
                NotificationDelivery.status == "pending",
            )
        )
        pending.next_attempt_at = datetime.now(UTC) - timedelta(seconds=1)
        db.commit()
    with SessionLocal() as db:
        assert enqueue_deadline_emails(db, tenant_id=tenant) == 0
        assert dispatch_outbox(db, tenant_id=tenant) == 1
        assert db.get(Notification, notification).dedup_key == key
        assert not add_notification(
            db, tenant_id=tenant, kind="deadline", title="不应再次创建", dedup_key=key
        )
    assert calls.count(users[0][1]) == 1 and calls.count(users[1][1]) == 2


def test_interrupted_send_becomes_uncertain_without_automatic_resend(monkeypatch):
    tenant, notification, _, _ = _notice()
    calls = []

    def crash(*_args):
        calls.append("provider may have accepted")
        raise SystemExit("synthetic process loss")

    monkeypatch.setattr(email, "send_notification_email", crash)
    with SessionLocal() as db:
        enqueue_deadline_emails(db, tenant_id=tenant)
        with pytest.raises(SystemExit):
            dispatch_outbox(db, tenant_id=tenant)
    with SessionLocal() as db:
        delivery = db.scalar(
            select(NotificationDelivery).where(NotificationDelivery.notification_id == notification)
        )
        assert delivery.status == "sending"
        delivery.lease_expires_at = datetime.now(UTC) - timedelta(seconds=1)
        db.commit()
    with SessionLocal() as db:
        assert dispatch_outbox(db, tenant_id=tenant) == 0
        delivery = db.scalar(
            select(NotificationDelivery).where(NotificationDelivery.notification_id == notification)
        )
        assert delivery.status == "uncertain"
    assert len(calls) == 1


def test_two_dispatchers_send_once(monkeypatch):
    tenant, _, _, _ = _notice()
    calls = []
    monkeypatch.setattr(
        email,
        "send_notification_email",
        lambda *_args: calls.append(1) or email.DeliveryOutcome("sent"),
    )
    with SessionLocal() as db:
        enqueue_deadline_emails(db, tenant_id=tenant)

    def dispatch(_index):
        with SessionLocal() as db:
            return dispatch_outbox(db, tenant_id=tenant)

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(dispatch, range(2))) == [0, 1]
    assert calls == [1]


def test_revoked_recipient_is_suppressed_and_cross_tenant_is_untouched():
    tenant, notice, _, users = _notice()
    other, _, _, _ = _notice()
    with SessionLocal() as db:
        enqueue_deadline_emails(db, tenant_id=tenant)
        assert dispatch_outbox(db, tenant_id=other) == 0
        membership = db.scalar(select(Membership).where(Membership.user_id == users[0][0]))
        membership.status = "revoked"
        db.commit()
        assert dispatch_outbox(db, tenant_id=tenant) == 0
        delivery = db.scalar(
            select(NotificationDelivery).where(NotificationDelivery.notification_id == notice)
        )
        assert delivery.status == "suppressed" and delivery.attempt_count == 0


def test_private_notification_only_targets_its_user_and_legacy_keys_stay_deduped():
    tenant, notification, _, _ = _notice(recipients=2, target=True)
    legacy_tenant, _, legacy_key, _ = _notice(legacy=True)
    with SessionLocal() as db:
        assert enqueue_deadline_emails(db, tenant_id=tenant) == 1
        assert enqueue_deadline_emails(db, tenant_id=legacy_tenant) == 0
        assert not add_notification(
            db,
            tenant_id=legacy_tenant,
            kind="deadline",
            title="旧记录不能重发",
            dedup_key=legacy_key,
        )
        assert db.get(Notification, notification).user_id is not None


def test_pending_intent_survives_disabled_transport(monkeypatch):
    tenant, notification, _, _ = _notice()
    monkeypatch.setattr(email, "is_email_configured", lambda: False)
    with SessionLocal() as db:
        assert enqueue_deadline_emails(db, tenant_id=tenant) == 1
        assert dispatch_outbox(db, tenant_id=tenant) == 0
    with SessionLocal() as db:
        assert (
            db.scalar(
                select(NotificationDelivery.status).where(
                    NotificationDelivery.notification_id == notification
                )
            )
            == "pending"
        )


def test_retry_budget_is_bounded(monkeypatch):
    tenant, notification, _, _ = _notice()
    calls = []
    monkeypatch.setattr(
        email,
        "send_notification_email",
        lambda *_args: calls.append(1) or email.DeliveryOutcome("retryable", "synthetic_rejection"),
    )
    with SessionLocal() as db:
        enqueue_deadline_emails(db, tenant_id=tenant)
        for _ in range(5):
            dispatch_outbox(db, tenant_id=tenant)
            row = db.scalar(
                select(NotificationDelivery).where(
                    NotificationDelivery.notification_id == notification
                )
            )
            row.next_attempt_at = datetime.now(UTC) - timedelta(seconds=1)
            db.commit()
        assert row.status == "failed" and row.attempt_count == 4
    assert len(calls) == 4


def test_two_enqueuers_share_one_recipient_intent():
    tenant, _, _, _ = _notice()

    def enqueue(_index):
        with SessionLocal() as db:
            return enqueue_deadline_emails(db, tenant_id=tenant)

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(enqueue, range(2))) == [0, 1]


def test_late_transport_result_cannot_overwrite_recovered_uncertainty(monkeypatch):
    tenant, notification, _, _ = _notice()

    def late_success(*_args):
        with SessionLocal() as recovery:
            row = recovery.scalar(
                select(NotificationDelivery).where(
                    NotificationDelivery.notification_id == notification
                )
            )
            row.lease_expires_at = datetime.now(UTC) - timedelta(seconds=1)
            recovery.commit()
            assert dispatch_outbox(recovery, tenant_id=tenant) == 0
        return email.DeliveryOutcome("sent")

    monkeypatch.setattr(email, "send_notification_email", late_success)
    with SessionLocal() as db:
        enqueue_deadline_emails(db, tenant_id=tenant)
        assert dispatch_outbox(db, tenant_id=tenant) == 0
        row = db.scalar(
            select(NotificationDelivery).where(NotificationDelivery.notification_id == notification)
        )
        assert row.status == "uncertain" and row.sent_at is None
