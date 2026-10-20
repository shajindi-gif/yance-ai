"""Synthetic isolated DB checks for revocation and one-time credentials."""
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request

from app.api.routes import auth
from app.core.db import SessionLocal
from app.main import app
from app.models.models import EmailCode, now_utc
from app.services.email_code import consume_code, hash_code

pytestmark = [pytest.mark.e2e, pytest.mark.skipif(os.getenv("APP_ENV") != "test", reason="isolated PostgreSQL required")]


def _account(client):
    email = f"revoke-{uuid.uuid4().hex}@example.com"
    response = client.post("/api/v1/auth/register", json={
        "company_name": "合成撤销测试企业", "owner_email": email,
        "owner_name": "合成用户", "owner_password": "audit-password-123456",
        "agreed_terms_version": "test-terms",
    })
    assert response.status_code == 201, response.text
    return email, {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_password_reset_revokes_old_sessions(monkeypatch):
    client = TestClient(app)
    email, old_headers = _account(client)
    monkeypatch.setattr(auth, "is_email_configured", lambda: True)
    with SessionLocal() as db:
        db.add(EmailCode(email=email, code_hash=hash_code(email, "123456"), purpose="reset", expires_at=now_utc() + timedelta(minutes=10)))
        db.commit()
    reset = client.post("/api/v1/auth/password/reset/confirm", json={"email": email, "code": "123456", "new_password": "new-audit-password-123456"})
    assert reset.status_code == 200, reset.text
    assert client.get("/api/v1/auth/me", headers=old_headers).status_code == 401
    new_headers = {"Authorization": f"Bearer {reset.json()['access_token']}"}
    assert client.get("/api/v1/auth/me", headers=new_headers).status_code == 200
    login = client.post("/api/v1/auth/login", data={"username": email, "password": "new-audit-password-123456"})
    assert login.status_code == 200
    assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {login.json()['access_token']}"}).status_code == 200


def test_logout_revokes_all_existing_jwt_sessions():
    client = TestClient(app)
    email, headers = _account(client)
    second = client.post("/api/v1/auth/login", data={"username": email, "password": "audit-password-123456"})
    assert second.status_code == 200
    assert client.post("/api/v1/auth/logout", headers=headers).status_code == 204
    for saved in (headers, {"Authorization": f"Bearer {second.json()['access_token']}"}):
        assert client.get("/api/v1/auth/me", headers=saved).status_code == 401


def test_verification_code_only_consumed_once_under_concurrency():
    email = f"single-{uuid.uuid4().hex}@example.com"
    with SessionLocal() as db:
        db.add(EmailCode(email=email, code_hash=hash_code(email, "123456"), purpose="login", expires_at=now_utc() + timedelta(minutes=10)))
        db.commit()
    def consume(_):
        with SessionLocal() as db:
            return consume_code(db, email, "123456")
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(consume, range(8)))
    assert results.count("ok") == 1


def test_forwarded_header_does_not_override_verified_peer():
    request = Request({"type": "http", "client": ("192.0.2.1", 12345), "headers": [(b"x-forwarded-for", b"203.0.113.9")]})
    assert auth._client_ip(request) == "192.0.2.1"


def test_concurrent_registration_counter_cannot_oversubscribe():
    from app.services.auth_rate_limit import REGISTER_LIMIT, register_attempt
    ip = f"audit-burst-{uuid.uuid4().hex}"
    def attempt(_):
        with SessionLocal() as db:
            return register_attempt(db, ip)
    with ThreadPoolExecutor(max_workers=12) as pool:
        assert sum(pool.map(attempt, range(12))) == REGISTER_LIMIT


def test_concurrent_public_signup_creates_one_workspace_per_email():
    email = f"signup-race-{uuid.uuid4().hex}@example.com"
    payload = {"company_name":"合成并发注册", "owner_email":email, "owner_name":"合成用户", "owner_password":"test-password-123456", "agreed_terms_version":"test-terms"}
    def register(_):
        with TestClient(app) as client:
            return client.post("/api/v1/auth/register", json=payload).status_code
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(register, range(4)))
    assert results.count(201) == 1
    assert results.count(409) == 3
