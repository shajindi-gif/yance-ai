"""Synthetic PostgreSQL and supplier-contract tests; never send real SMS."""

import os
import secrets
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.api.routes import sms_auth
from app.core.config import settings
from app.core.db import SessionLocal
from app.main import app
from app.models.models import SmsCode, User, now_utc
from app.services import sms

pytestmark = pytest.mark.skipif(
    os.getenv("APP_ENV") != "test", reason="isolated PostgreSQL required"
)


def phone():
    return "+86199" + f"{secrets.randbelow(100_000_000):08d}"


@pytest.fixture
def setup(monkeypatch):
    monkeypatch.setattr(sms_auth, "is_sms_configured", lambda: True)
    sent = {}
    monkeypatch.setattr(sms_auth, "send_sms", lambda number, code: sent.update({number: code}))
    return TestClient(app), sent


def seed(number, code="123456", purpose="login", **kwargs):
    with SessionLocal() as db:
        row = SmsCode(
            phone=number,
            purpose=purpose,
            code_hash=sms.digest_code(number, purpose, code),
            state="accepted",
            expires_at=now_utc() + timedelta(minutes=5),
            **kwargs,
        )
        db.add(row)
        db.commit()


def profile(number, code="123456"):
    return {
        "phone": number,
        "code": code,
        "owner_name": "合成用户",
        "company_name": "合成短信测试企业",
        "agreed_terms_version": "2026-10-30",
    }


def test_disabled_and_phone_validation(monkeypatch):
    monkeypatch.setattr(sms_auth, "is_sms_configured", lambda: False)
    c = TestClient(app)
    assert c.post("/api/v1/auth/sms/send", json={"phone": phone()}).status_code == 503
    for invalid in ("+12025550123", "123", "19900000000\nmalicious"):
        assert c.post("/api/v1/auth/sms/send", json={"phone": invalid}).status_code == 422
    assert c.post("/api/v1/auth/sms/bind/send", json={"phone": phone()}).status_code == 401


def test_registration_login_replay_and_tenant_isolation(setup):
    c, sent = setup
    a, b = phone(), phone()
    assert c.post("/api/v1/auth/sms/send", json={"phone": a[3:]}).status_code == 202
    # Missing profile only revealed after phone proof; valid OTP is preserved.
    assert c.post("/api/v1/auth/sms/verify", json={"phone": a, "code": sent[a]}).status_code == 400
    first = c.post("/api/v1/auth/sms/verify", json=profile(a, sent[a]))
    assert first.status_code == 200, first.text
    h1 = {"Authorization": "Bearer " + first.json()["access_token"]}
    me = c.get("/api/v1/auth/me", headers=h1).json()
    assert me["email"] is None and me["phone"] == a
    assert c.post("/api/v1/auth/sms/verify", json=profile(a, sent[a])).status_code == 401
    seed(b)
    second = c.post("/api/v1/auth/sms/verify", json=profile(b))
    h2 = {"Authorization": "Bearer " + second.json()["access_token"]}
    company = c.get("/api/v1/companies", headers=h1).json()[0]
    assert c.get("/api/v1/companies/" + company["id"], headers=h2).status_code == 404
    # Existing account requires no company/name fields, no duplicate workspace.
    seed(a)
    assert c.post("/api/v1/auth/sms/verify", json={"phone": a, "code": "123456"}).status_code == 200
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(User).where(User.phone == a)) == 1


def test_wrong_expired_attempt_cap_and_uncertain(setup):
    c, _ = setup
    a = phone()
    seed(a)
    for _ in range(5):
        assert c.post("/api/v1/auth/sms/verify", json=profile(a, "000000")).status_code == 401
    assert c.post("/api/v1/auth/sms/verify", json=profile(a)).status_code == 429
    b = phone()
    seed(b)
    with SessionLocal() as db:
        row = db.scalar(select(SmsCode).where(SmsCode.phone == b))
        row.expires_at = now_utc() - timedelta(seconds=1)
        db.commit()
    assert c.post("/api/v1/auth/sms/verify", json=profile(b)).status_code == 401
    d = phone()
    seed(d)
    with SessionLocal() as db:
        row = db.scalar(select(SmsCode).where(SmsCode.phone == d))
        row.state = "uncertain"
        db.commit()
    assert c.post("/api/v1/auth/sms/verify", json=profile(d)).status_code == 401


def test_concurrent_code_consumption(setup):
    c, _ = setup
    a = phone()
    seed(a)
    with ThreadPoolExecutor(max_workers=4) as pool:
        statuses = list(
            pool.map(
                lambda _: c.post("/api/v1/auth/sms/verify", json=profile(a)).status_code, range(4)
            )
        )
    assert statuses.count(200) == 1 and statuses.count(401) == 3


def test_send_cooldown_and_failure_budget(setup, monkeypatch):
    c, _ = setup
    a = phone()
    with ThreadPoolExecutor(max_workers=3) as pool:
        statuses = list(
            pool.map(
                lambda _: c.post("/api/v1/auth/sms/send", json={"phone": a}).status_code, range(3)
            )
        )
    assert statuses.count(202) == 1 and statuses.count(429) == 2

    def fail(*args):
        raise sms.SmsDeliveryError("synthetic")

    monkeypatch.setattr(sms_auth, "send_sms", fail)
    b = phone()
    assert c.post("/api/v1/auth/sms/send", json={"phone": b}).status_code == 503
    assert c.post("/api/v1/auth/sms/send", json={"phone": b}).status_code == 429
    with SessionLocal() as db:
        row = db.scalar(select(SmsCode).where(SmsCode.phone == b))
        assert row.state == "uncertain" and len(row.code_hash) == 64


def test_binding_requires_current_user_proof_and_no_merge(setup):
    c, sent = setup
    registered = c.post(
        "/api/v1/auth/register",
        json={
            "company_name": "合成邮箱企业",
            "owner_email": secrets.token_hex(8) + "@example.com",
            "owner_name": "合成用户",
            "owner_password": "long-synthetic-123456",
            "agreed_terms_version": "2026-10-30",
        },
    )
    h = {"Authorization": "Bearer " + registered.json()["access_token"]}
    a = phone()
    assert c.post("/api/v1/auth/sms/bind/send", headers=h, json={"phone": a}).status_code == 202
    assert c.post("/api/v1/auth/sms/verify", json=profile(a, sent[a])).status_code == 401
    assert (
        c.post("/api/v1/auth/sms/bind", headers=h, json={"phone": a, "code": sent[a]}).status_code
        == 200
    )
    seed(a)
    login = c.post("/api/v1/auth/sms/verify", json={"phone": a, "code": "123456"})
    assert (
        c.get(
            "/api/v1/auth/me", headers={"Authorization": "Bearer " + login.json()["access_token"]}
        ).json()["id"]
        == c.get("/api/v1/auth/me", headers=h).json()["id"]
    )
    b = phone()
    seed(b)
    second = c.post("/api/v1/auth/sms/verify", json=profile(b)).json()
    other = {"Authorization": "Bearer " + second["access_token"]}
    assert (
        c.post(
            "/api/v1/auth/sms/bind", headers=other, json={"phone": a, "code": "123456"}
        ).status_code
        == 401
    )


def test_provider_contract_no_network(monkeypatch):
    for key, val in {
        "sms_enabled": True,
        "tencent_sms_secret_id": "synthetic-id",
        "tencent_sms_secret_key": "synthetic-key",
        "tencent_sms_app_id": "1401206912",
        "tencent_sms_sign_name": "上海衍策引擎人工智能",
        "tencent_sms_template_id": "2749303",
    }.items():
        monkeypatch.setattr(settings, key, val)
    number = phone()
    import json

    real_client = httpx.Client

    def handler(request):
        assert str(request.url) == "https://sms.tencentcloudapi.com"
        data = json.loads(request.content)
        assert data["PhoneNumberSet"] == [number]
        assert data["TemplateParamSet"] == ["123456", "5"]
        assert data["SmsSdkAppId"] == "1401206912" and data["TemplateId"] == "2749303"
        assert request.headers["X-TC-Version"] == "2021-01-11"
        assert request.headers["Authorization"].startswith(
            "TC3-HMAC-SHA256 Credential=synthetic-id/"
        )
        return httpx.Response(
            200, json={"Response": {"SendStatusSet": [{"Code": "Ok", "PhoneNumber": number}]}}
        )

    monkeypatch.setattr(
        sms.httpx, "Client", lambda **kw: real_client(transport=httpx.MockTransport(handler), **kw)
    )
    sms.send_sms(number, "123456")

    def rejected(request):
        return httpx.Response(200, json={"Response": {"Error": {"Code": "synthetic"}}})

    monkeypatch.setattr(
        sms.httpx, "Client", lambda **kw: real_client(transport=httpx.MockTransport(rejected), **kw)
    )
    with pytest.raises(sms.SmsDeliveryError):
        sms.send_sms(number, "123456")


def test_existing_phone_cannot_be_taken_by_another_account(setup):
    c, sent = setup
    a = phone()
    seed(a)
    owner = c.post("/api/v1/auth/sms/verify", json=profile(a)).json()
    other = c.post(
        "/api/v1/auth/register",
        json={
            "company_name": "合成禁止合并企业",
            "owner_email": secrets.token_hex(8) + "@example.com",
            "owner_name": "合成用户",
            "owner_password": "synthetic-password-123456",
            "agreed_terms_version": "2026-10-30",
        },
    ).json()
    h = {"Authorization": "Bearer " + other["access_token"]}
    # Even a correct binding OTP cannot take a phone from its current owner.
    b = phone()
    seed(b, purpose="bind:" + c.get("/api/v1/auth/me", headers=h).json()["id"])
    # A phone without an owner is bindable; simulate another owner winning before verification.
    with SessionLocal() as db:
        current = db.scalar(select(User).where(User.phone == a))
        current.phone = b
        db.commit()
    assert (
        c.post("/api/v1/auth/sms/bind", headers=h, json={"phone": b, "code": "123456"}).status_code
        == 409
    )
    assert c.get("/api/v1/auth/me", headers=h).json()["phone"] is None
    first = {"Authorization": "Bearer " + owner["access_token"]}
    assert c.get("/api/v1/auth/me", headers=first).json()["phone"] == b


def test_daily_budget_and_disabled_account(setup, monkeypatch):
    c, _ = setup
    monkeypatch.setattr(settings, "sms_daily_limit", 1)
    assert c.post("/api/v1/auth/sms/send", json={"phone": phone()}).status_code == 202
    assert c.post("/api/v1/auth/sms/send", json={"phone": phone()}).status_code == 429
    a = phone()
    seed(a)
    assert c.post("/api/v1/auth/sms/verify", json=profile(a)).status_code == 200
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.phone == a))
        user.is_active = False
        db.commit()
    seed(a)
    assert c.post("/api/v1/auth/sms/verify", json={"phone": a, "code": "123456"}).status_code == 403


@pytest.mark.parametrize("version", ["2026-10-29", "2026-10-30"])
def test_consent_bundle_compatibility_retains_the_exact_agreed_version(setup, version):
    from app.models.models import AnalyticsEvent
    c, _ = setup
    number = phone()
    seed(number)
    response = c.post('/api/v1/auth/sms/verify', json={**profile(number), 'agreed_terms_version': version})
    assert response.status_code == 200
    me = c.get('/api/v1/auth/me', headers={'Authorization': 'Bearer '+response.json()['access_token']}).json()
    with SessionLocal() as db:
        event = db.scalar(select(AnalyticsEvent).where(AnalyticsEvent.user_id == me['id'], AnalyticsEvent.name == 'terms_accepted'))
        assert event.properties['terms_version'] == version
