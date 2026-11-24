"""Regression for acceptance ACC-02 / ACC-07 (docs/acceptance/2026-11-24-4adefc7.md).

ACC-02: a successful login from the same IP must not reset the failed-login
counter that protects a *different* account.
ACC-07: unknown and known e-mails must cost the same password-hash work.
"""
import os
import time
import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app

pytestmark = [pytest.mark.e2e, pytest.mark.skipif(os.getenv("APP_ENV") != "test", reason="isolated PostgreSQL required")]


def _register(client, email, password):
    response = client.post("/api/v1/auth/register", json={
        "company_name": "合成验收企业", "owner_email": email, "owner_name": "合成用户",
        "owner_password": password, "agreed_terms_version": "test-terms",
    })
    assert response.status_code == 201, response.text


def test_own_successful_login_does_not_reset_victim_lockout():
    client = TestClient(app)
    victim, attacker = f"v-{uuid.uuid4().hex}@example.com", f"a-{uuid.uuid4().hex}@example.com"
    _register(client, victim, "victim-secret-password-1")
    _register(client, attacker, "attacker-password-123456")
    statuses = []
    for i in range(60):
        if i and i % 9 == 0:
            client.post("/api/v1/auth/login", data={"username": attacker, "password": "attacker-password-123456"})
        statuses.append(client.post("/api/v1/auth/login", data={"username": victim, "password": f"guess-{i}"}).status_code)
    assert 429 in statuses
    assert statuses.count(401) <= 10


def test_account_lockout_holds_across_ip_reset():
    """The per-account counter alone must stop guessing even if the IP counter is cleared."""
    from sqlalchemy import text

    from app.core.db import SessionLocal

    client = TestClient(app)
    victim = f"v-{uuid.uuid4().hex}@example.com"
    _register(client, victim, "victim-secret-password-1")
    statuses = []
    for i in range(15):
        with SessionLocal() as db:  # simulate a fresh source IP for every guess
            db.execute(text("DELETE FROM auth_rate_limit WHERE key LIKE 'loginfail:%'"))
            db.commit()
        statuses.append(client.post("/api/v1/auth/login", data={"username": victim, "password": f"guess-{i}"}).status_code)
    assert 429 in statuses


def test_login_timing_does_not_reveal_account_existence():
    client = TestClient(app)
    email = f"t-{uuid.uuid4().hex}@example.com"
    _register(client, email, "timing-password-123456")

    def elapsed(username):
        start = time.perf_counter()
        client.post("/api/v1/auth/login", data={"username": username, "password": "wrong-password"})
        return time.perf_counter() - start

    existing = sorted(elapsed(email) for _ in range(5))[2]
    missing = sorted(elapsed(f"nobody-{uuid.uuid4().hex}@example.com") for _ in range(5))[2]
    assert max(existing, missing) / min(existing, missing) < 2
