"""Shared test fixtures.

The authoritative backend suite always runs against a migrated PostgreSQL test
database (see repo README). auth_rate_limit and email_codes are ephemeral
counter/state tables; clearing them before each test isolates cases so the new
DB-backed register/login rate limits (S1) don't leak across tests that share
the default "testclient" IP.
"""

import pytest
from sqlalchemy import text

from app.core.db import SessionLocal


@pytest.fixture(autouse=True)
def _clear_ephemeral_auth_state():
    try:
        with SessionLocal() as db:
            db.execute(text("DELETE FROM auth_rate_limit"))
            db.execute(text("DELETE FROM email_codes"))
            db.commit()
    except Exception:
        # Tables may be absent in pure-unit contexts; e2e tests would fail loudly anyway.
        pass
    yield
