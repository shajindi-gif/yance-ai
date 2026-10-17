"""Email verification-code login: channel gate, DB rate limits, expiry,
attempt lockout, replay rejection and auto-provisioning idempotency.

Run against a fresh migrated PostgreSQL test database (same convention as
test_core_workflow.py).
"""

import os
import re
import uuid
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.api.routes import auth
from app.core.config import settings
from app.core.db import SessionLocal
from app.main import app
from app.models.models import (
    AnalyticsEvent,
    Company,
    EmailCode,
    Membership,
    Tenant,
    User,
    now_utc,
)
from app.schemas.schemas import BootstrapRequest
from app.services import email_code as ec

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(
        os.getenv("APP_ENV") != "test",
        reason="Email-code tests require the migrated PostgreSQL test database",
    ),
]

client = TestClient(app)


@pytest.fixture()
def email_on(monkeypatch):
    """Enable the channel and capture outgoing code emails (no Resend call)."""
    monkeypatch.setattr(settings, "email_enabled", True)
    monkeypatch.setattr(settings, "resend_api_key", "re_test_key")
    monkeypatch.setattr(settings, "email_from", "衍策引擎AI <notify@example.com>")
    sent: list[tuple[str, str]] = []

    def fake_send(to, subject, body):
        match = re.search(r"验证码是：(\d{6})", body)
        sent.append((to, match.group(1) if match else ""))
        return True

    monkeypatch.setattr(ec, "send_email", fake_send)
    return sent


def _email() -> str:
    return f"e-{uuid.uuid4().hex[:10]}@example.com"


def _ip() -> str:
    return f"10.20.{uuid.uuid4().int % 200}.{(uuid.uuid4().int >> 8) % 200 + 5}"


def _send(email: str, ip: str | None = None):
    headers = {"X-Forwarded-For": ip or _ip()}
    return client.post("/api/v1/auth/email/send", json={"email": email}, headers=headers)


def _verify(payload: dict):
    return client.post("/api/v1/auth/email/verify", json=payload)


def _latest_row(email: str) -> EmailCode:
    with SessionLocal() as db:
        return db.scalars(
            select(EmailCode)
            .where(EmailCode.email == email)
            .order_by(EmailCode.created_at.desc())
            .limit(1)
        ).one()


def _backdate_created(email: str, seconds: int) -> None:
    with SessionLocal() as db:
        for row in db.scalars(select(EmailCode).where(EmailCode.email == email)).all():
            if row.created_at >= row.created_at - timedelta(seconds=seconds):
                row.created_at = now_utc() - timedelta(seconds=seconds)
        db.commit()


def _expire_now(email: str) -> None:
    with SessionLocal() as db:
        row = db.scalars(
            select(EmailCode)
            .where(EmailCode.email == email, EmailCode.used_at.is_(None))
            .order_by(EmailCode.created_at.desc())
            .limit(1)
        ).one()
        row.expires_at = now_utc() - timedelta(minutes=1)
        db.commit()


# ── channel gate ──────────────────────────────────────────────────────


def test_send_and_verify_return_503_when_channel_unconfigured(monkeypatch):
    monkeypatch.setattr(settings, "email_enabled", False)
    response = _send(_email())
    assert response.status_code == 503
    assert "尚未开通" in response.json()["detail"]

    response = _verify({"email": _email(), "code": "123456"})
    assert response.status_code == 503

    config = client.get("/api/v1/auth/config")
    assert config.status_code == 200
    assert config.json()["email_login_enabled"] is False


def test_auth_config_reports_enabled(email_on):
    config = client.get("/api/v1/auth/config")
    assert config.status_code == 200
    assert config.json()["email_login_enabled"] is True


# ── DB-backed rate limits ─────────────────────────────────────────────


def test_cooldown_blocks_immediate_resend(email_on):
    email = _email()
    assert _send(email).status_code == 202
    second = _send(email)
    assert second.status_code == 429
    assert "秒后重试" in second.json()["detail"]
    assert len(email_on) == 1  # no code generated for the blocked request

    # after the 60s cooldown window (simulated by backdating), resend is allowed
    _backdate_created(email, 61)
    assert _send(email).status_code == 202
    assert len(email_on) == 2


def test_per_email_hourly_cap(email_on):
    email = _email()
    for _ in range(ec.PER_EMAIL_PER_HOUR):
        response = _send(email)
        assert response.status_code == 202, response.text
        _backdate_created(email, 61)  # clear cooldown, stay inside the 1h window
    blocked = _send(email)
    assert blocked.status_code == 429
    assert len(email_on) == ec.PER_EMAIL_PER_HOUR


def test_per_ip_hourly_cap(email_on):
    ip = _ip()
    for _ in range(ec.PER_IP_PER_HOUR):
        response = _send(_email(), ip=ip)
        assert response.status_code == 202
    eleventh = _send(_email(), ip=ip)
    assert eleventh.status_code == 429


# ── code lifecycle ────────────────────────────────────────────────────


def test_expired_code_rejected(email_on):
    email = _email()
    _send(email)
    code = email_on[-1][1]
    _expire_now(email)
    response = _verify(
        {
            "email": email,
            "code": code,
            "owner_name": "过期测试",
            "company_name": "上海过期验证码有限公司",
            "agreed_terms_version": "test-terms",
        }
    )
    assert response.status_code == 401
    assert "过期" in response.json()["detail"]
    assert db_scalar_count(User, User.email == email) == 0


def db_scalar_count(model, *criteria) -> int:
    with SessionLocal() as db:
        return db.scalar(select(func.count()).select_from(model).where(*criteria)) or 0


def test_wrong_attempts_lockout(email_on):
    email = _email()
    _send(email)
    code = email_on[-1][1]
    wrong = "000000" if code != "000000" else "000001"
    fields = {
        "email": email,
        "owner_name": "锁测试",
        "company_name": "上海错误次数有限公司",
        "agreed_terms_version": "test-terms",
    }
    for _ in range(ec.MAX_ATTEMPTS):
        response = _verify({**fields, "code": wrong})
        assert response.status_code == 401
    # attempts exhausted: even the correct code is now refused until a fresh one
    locked = _verify({**fields, "code": code})
    assert locked.status_code == 429
    assert db_scalar_count(User, User.email == email) == 0


def test_code_single_use_replay_rejected(email_on):
    email = _email()
    _send(email)
    code = email_on[-1][1]
    ok = _verify(
        {
            "email": email,
            "code": code,
            "owner_name": "张三",
            "company_name": "上海回放科技有限公司",
            "agreed_terms_version": "test-terms",
        }
    )
    assert ok.status_code == 200
    replay = _verify(
        {
            "email": email,
            "code": code,
            "owner_name": "张三",
            "company_name": "上海回放科技有限公司",
            "agreed_terms_version": "test-terms",
        }
    )
    assert replay.status_code == 401


def test_new_email_missing_fields_does_not_burn_code(email_on):
    email = _email()
    _send(email)
    code = email_on[-1][1]
    first = _verify({"email": email, "code": code})
    assert first.status_code == 400
    assert "首次登录" in first.json()["detail"]
    assert _latest_row(email).used_at is None  # code still usable
    second = _verify(
        {
            "email": email,
            "code": code,
            "owner_name": "李四",
            "company_name": "上海补齐信息有限公司",
            "agreed_terms_version": "test-terms",
        }
    )
    assert second.status_code == 200


# ── auto-provisioning ─────────────────────────────────────────────────


def test_auto_register_provisions_workspace_and_token(email_on):
    email = _email()
    _send(email)
    code = email_on[-1][1]
    response = _verify(
        {
            "email": email,
            "code": code,
            "owner_name": "王五",
            "company_name": "上海自动建号有限公司",
            "agreed_terms_version": "test-terms",
        }
    )
    assert response.status_code == 200
    token = response.json()["access_token"]

    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == email
    assert me.json()["role"] == "owner"

    with SessionLocal() as db:
        user = db.scalars(select(User).where(User.email == email)).one()
        tenants = db.scalars(select(Tenant).where(Tenant.id == user.tenant_id)).all()
        assert len(tenants) == 1
        assert tenants[0].name == "上海自动建号有限公司"
        membership = db.scalars(
            select(Membership).where(Membership.user_id == user.id)
        ).one()
        assert membership.status == "active"
        assert db.scalars(select(Company).where(Company.tenant_id == user.tenant_id)).one()
        events = set(
            db.scalars(
                select(AnalyticsEvent.name).where(AnalyticsEvent.tenant_id == user.tenant_id)
            ).all()
        )
        assert {"signup_completed", "terms_accepted", "company_created", "login_completed"} <= events

    # password login must be impossible for a code-only account
    guess = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": "whatever-123456"},
    )
    assert guess.status_code == 401


def test_second_code_login_reuses_same_workspace(email_on):
    email = _email()
    _send(email)
    first = _verify(
        {
            "email": email,
            "code": email_on[-1][1],
            "owner_name": "赵六",
            "company_name": "上海二次登录有限公司",
            "agreed_terms_version": "test-terms",
        }
    )
    assert first.status_code == 200

    _backdate_created(email, 61)
    assert _send(email).status_code == 202
    second = _verify({"email": email, "code": email_on[-1][1]})  # existing user: no fields
    assert second.status_code == 200
    assert db_scalar_count(User, User.email == email) == 1

    # No second workspace was provisioned for the same email on re-login.
    with SessionLocal() as db:
        user = db.scalars(select(User).where(User.email == email)).one()
        tenants_for_email = db.scalar(
            select(func.count(Tenant.id))
            .join(User, User.tenant_id == Tenant.id)
            .where(User.email == email)
        )
        assert tenants_for_email == 1
        assert db.scalar(
            select(func.count(Company.id)).where(Company.tenant_id == user.tenant_id)
        ) == 1

    me = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {second.json()['access_token']}"},
    )
    assert me.json()["email"] == email


def test_existing_password_user_can_login_by_code(email_on):
    email = _email()
    registered = client.post(
        "/api/v1/auth/register",
        json={
            "company_name": "上海密码注册用户有限公司",
            "industry": "人工智能",
            "province": "上海市",
            "city": "上海市",
            "owner_email": email,
            "owner_name": "钱七",
            "owner_password": "integration-password-123",
            "agreed_terms_version": "test-terms",
        },
    )
    assert registered.status_code == 201

    _send(email)
    response = _verify({"email": email, "code": email_on[-1][1]})
    assert response.status_code == 200
    assert db_scalar_count(User, User.email == email) == 1


def test_multi_workspace_email_asks_for_password_login(email_on):
    email = _email()
    suffix = uuid.uuid4().hex[:6]
    with SessionLocal() as db:
        for index in (1, 2):
            auth.create_tenant_and_owner(
                BootstrapRequest(
                    tenant_name=f"多工作区租户 {suffix}-{index}",
                    tenant_slug=f"multi-{suffix}-{index}",
                    owner_email=email,
                    owner_name="多面手",
                    owner_password="integration-password-123",
                ),
                db,
            )

    _send(email)
    response = _verify({"email": email, "code": email_on[-1][1]})
    assert response.status_code == 400
    assert "多个工作区" in response.json()["detail"]
    assert _latest_row(email).used_at is None  # code preserved, no auto choice made


# ── 找回密码（password reset）────────────────────────────────────────


def _register_user(email: str, password: str = "old-password-12345") -> str:
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "company_name": f"Reset {uuid.uuid4().hex[:6]}",
            "owner_email": email,
            "owner_name": "重置测试",
            "owner_password": password,
            "agreed_terms_version": "test-terms",
        },
    )
    assert resp.status_code == 201, resp.text
    return password


def _reset_request(email: str, ip: str | None = None):
    headers = {"X-Forwarded-For": ip or _ip()}
    return client.post(
        "/api/v1/auth/password/reset/request", json={"email": email}, headers=headers
    )


def _reset_confirm(email: str, code: str, new_password: str):
    return client.post(
        "/api/v1/auth/password/reset/confirm",
        json={"email": email, "code": code, "new_password": new_password},
    )


def test_reset_request_503_when_unconfigured(monkeypatch):
    monkeypatch.setattr(settings, "email_enabled", False)
    resp = _reset_request(_email())
    assert resp.status_code == 503
    assert "尚未开通" in resp.json()["detail"]


def test_reset_confirm_503_when_unconfigured(monkeypatch):
    monkeypatch.setattr(settings, "email_enabled", False)
    resp = _reset_confirm(_email(), "123456", "brand-new-password-1")
    assert resp.status_code == 503


def test_reset_unknown_email_no_send_but_202(email_on):
    unknown = _email()
    resp = _reset_request(unknown)
    assert resp.status_code == 202  # anti-enumeration: same reply
    assert len(email_on) == 0  # but no code was actually delivered
    with SessionLocal() as db:
        assert db.scalar(
            select(func.count()).select_from(EmailCode).where(EmailCode.email == unknown)
        ) == 0


def test_reset_flow_changes_password_and_logs_in(email_on):
    email = _email()
    _register_user(email)
    resp = _reset_request(email)
    assert resp.status_code == 202
    assert len(email_on) == 1
    code = email_on[-1][1]

    confirm = _reset_confirm(email, code, "brand-new-password-1")
    assert confirm.status_code == 200
    token = confirm.json()["access_token"]
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == email

    # new password works, old password rejected
    ok = client.post("/api/v1/auth/login", data={"username": email, "password": "brand-new-password-1"})
    assert ok.status_code == 200
    bad = client.post("/api/v1/auth/login", data={"username": email, "password": "old-password-12345"})
    assert bad.status_code == 401

    with SessionLocal() as db:
        assert "password_reset" in set(
            db.scalars(
                select(AnalyticsEvent.name).where(AnalyticsEvent.name == "password_reset")
            ).all()
        )


def test_reset_wrong_code_does_not_change_password(email_on):
    email = _email()
    _register_user(email)
    _reset_request(email)
    real = email_on[-1][1]
    wrong = "000000" if real != "000000" else "000001"
    resp = _reset_confirm(email, wrong, "attacker-password-123")
    assert resp.status_code == 401
    # old password still valid
    login = client.post("/api/v1/auth/login", data={"username": email, "password": "old-password-12345"})
    assert login.status_code == 200


def test_reset_code_replay_rejected(email_on):
    email = _email()
    _register_user(email)
    _reset_request(email)
    code = email_on[-1][1]
    first = _reset_confirm(email, code, "new-password-one-123")
    assert first.status_code == 200
    replay = _reset_confirm(email, code, "new-password-two-123")
    assert replay.status_code == 401


def test_purpose_isolation_login_code_cannot_reset(email_on):
    email = _email()
    _register_user(email)
    # issue a LOGIN code
    _send(email)
    login_code = email_on[-1][1]
    # try to use the login code for a password reset -> must fail
    resp = _reset_confirm(email, login_code, "cross-purpose-pw-123")
    assert resp.status_code == 401
    # old password still valid
    login = client.post("/api/v1/auth/login", data={"username": email, "password": "old-password-12345"})
    assert login.status_code == 200


def test_reset_multi_workspace_email_asks_admin(email_on):
    email = _email()
    suffix = uuid.uuid4().hex[:6]
    with SessionLocal() as db:
        for index in (1, 2):
            auth.create_tenant_and_owner(
                BootstrapRequest(
                    tenant_name=f"重置多租户 {suffix}-{index}",
                    tenant_slug=f"resetmulti-{suffix}-{index}",
                    owner_email=email,
                    owner_name="多面手",
                    owner_password="integration-password-123",
                ),
                db,
            )
    _reset_request(email)
    code = email_on[-1][1]
    resp = _reset_confirm(email, code, "new-password-xyz-123")
    assert resp.status_code == 400
    assert "多个工作区" in resp.json()["detail"]
