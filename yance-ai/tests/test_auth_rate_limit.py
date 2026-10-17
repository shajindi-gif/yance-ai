"""S1 fix verification: DB-backed auth rate limits shared across workers.

Audit evidence being closed: "连续 7 次失败登录全部 401、无 429（4 workers 各自
独立计数）" and register limited only in per-worker memory. Both limits now live
in auth_rate_limit, so they hold for the whole process pool and survive restarts.
"""

import os
import uuid
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.db import SessionLocal
from app.main import app
from app.models.models import AuthRateLimit, now_utc
from app.services import auth_rate_limit as rl

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(
        os.getenv("APP_ENV") != "test",
        reason="Auth rate-limit tests require the migrated PostgreSQL test database",
    ),
]

client = TestClient(app)


def _shift_window(key: str, back_seconds: int) -> None:
    with SessionLocal() as db:
        row = db.get(AuthRateLimit, key)
        assert row is not None
        row.window_start = now_utc() - timedelta(seconds=back_seconds)
        db.commit()


# ── service level ─────────────────────────────────────────────────────


def test_register_attempt_counts_in_db_and_blocks_over_limit():
    ip = f"9.9.{uuid.uuid4().int % 250}.{(uuid.uuid4().int >> 8) % 250 + 3}"
    with SessionLocal() as db:
        for _ in range(rl.REGISTER_LIMIT):
            assert rl.register_attempt(db, ip) is True
        assert rl.register_attempt(db, ip) is False
        row = db.get(AuthRateLimit, f"register:{ip}")
        assert row is not None and row.count == rl.REGISTER_LIMIT


def test_window_resets_after_expiry():
    with SessionLocal() as db:
        ip = f"8.8.{uuid.uuid4().int % 250}.7"
        for _ in range(rl.REGISTER_LIMIT):
            assert rl.register_attempt(db, ip) is True
        assert rl.register_attempt(db, ip) is False
        _shift_window(f"register:{ip}", rl.REGISTER_WINDOW_SECONDS + 60)
        assert rl.register_attempt(db, ip) is True  # fresh window
        row = db.get(AuthRateLimit, f"register:{ip}")
        assert row.count == 1


def test_login_failure_counter_and_success_clear():
    with SessionLocal() as db:
        ip = f"7.7.{uuid.uuid4().int % 250}.5"
        assert rl.login_is_limited(db, ip) is False
        for _ in range(rl.LOGIN_FAIL_LIMIT):
            assert rl.login_failure(db, ip) is True
        assert rl.login_is_limited(db, ip) is True
        rl.login_success(db, ip)
        assert rl.login_is_limited(db, ip) is False


# ── endpoint level (multi-worker-safe by construction: shared DB) ─────


def _register_payload() -> dict:
    suffix = uuid.uuid4().hex[:8]
    return {
        "company_name": f"RateLimit Co {suffix}",
        "owner_email": f"rl-{suffix}@example.com",
        "owner_name": "限流测试",
        "owner_password": "integration-password-123",
        "agreed_terms_version": "test-terms",
    }


def test_register_endpoint_429_on_sixth_same_ip():
    ip = f"172.16.{uuid.uuid4().int % 250}.9"
    headers = {"X-Forwarded-For": ip}
    for i in range(rl.REGISTER_LIMIT):
        r = client.post("/api/v1/auth/register", json=_register_payload(), headers=headers)
        assert r.status_code == 201, f"attempt {i + 1}: {r.text}"
    blocked = client.post("/api/v1/auth/register", json=_register_payload(), headers=headers)
    assert blocked.status_code == 429
    assert "过于频繁" in blocked.json()["detail"]


def test_login_endpoint_429_after_ten_failures():
    email = f"rl-login-{uuid.uuid4().hex[:8]}@example.com"
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "company_name": "登录限流公司",
            "owner_email": email,
            "owner_name": "登录限流",
            "owner_password": "integration-password-123",
            "agreed_terms_version": "test-terms",
        },
    )
    assert reg.status_code == 201
    ip = f"172.16.{uuid.uuid4().int % 250}.11"
    headers = {"X-Forwarded-For": ip}
    for i in range(rl.LOGIN_FAIL_LIMIT):
        r = client.post(
            "/api/v1/auth/login",
            data={"username": email, "password": "wrong-password-999"},
            headers=headers,
        )
        assert r.status_code == 401, f"failure {i + 1} expected 401, got {r.status_code}"
    limited = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": "integration-password-123"},  # even correct
        headers=headers,
    )
    assert limited.status_code == 429  # blocked window refuses regardless of password


def test_successful_login_clears_failure_counter():
    email = f"rl-clear-{uuid.uuid4().hex[:8]}@example.com"
    client.post(
        "/api/v1/auth/register",
        json={
            "company_name": "登录清零公司",
            "owner_email": email,
            "owner_name": "登录清零",
            "owner_password": "integration-password-123",
            "agreed_terms_version": "test-terms",
        },
    )
    ip = f"172.16.{uuid.uuid4().int % 250}.13"
    headers = {"X-Forwarded-For": ip}
    for _ in range(rl.LOGIN_FAIL_LIMIT - 1):  # 9 failures, one below the cap
        r = client.post(
            "/api/v1/auth/login",
            data={"username": email, "password": "bad"},
            headers=headers,
        )
        assert r.status_code == 401
    ok = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": "integration-password-123"},
        headers=headers,
    )
    assert ok.status_code == 200  # success resets the counter
    for _ in range(rl.LOGIN_FAIL_LIMIT - 1):  # 9 more failures must still be 401, not 429
        r = client.post(
            "/api/v1/auth/login",
            data={"username": email, "password": "bad"},
            headers=headers,
        )
        assert r.status_code == 401, "counter should have been cleared by the successful login"
    with SessionLocal() as db:
        assert db.get(AuthRateLimit, f"loginfail:{ip}") is None or (
            db.get(AuthRateLimit, f"loginfail:{ip}").count < rl.LOGIN_FAIL_LIMIT
        )
