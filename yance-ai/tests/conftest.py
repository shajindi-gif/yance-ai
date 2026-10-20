"""Shared test fixtures.

The authoritative backend suite always runs against a migrated PostgreSQL test
database (see repo README). auth_rate_limit and email_codes are ephemeral
counter/state tables; clearing them before each test isolates cases so the new
DB-backed register/login rate limits (S1) don't leak across tests that share
the default "testclient" IP.
"""

import os

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url

from app.core.db import SessionLocal


def pytest_sessionstart(session):
    """Never let the destructive integration fixtures infer their database."""
    if os.environ.get("APP_ENV") != "test":
        return
    raw_url = os.environ.get("DATABASE_URL")
    database = make_url(raw_url).database if raw_url else None
    if (
        not database
        or "prod" in database.lower()
        or os.environ.get("YANCE_TEST_DATABASE_ACK") != database
    ):
        raise pytest.UsageError(
            "Integration tests require an explicit DATABASE_URL and "
            "YANCE_TEST_DATABASE_ACK equal to the isolated database name; "
            "production database names are forbidden."
        )


@pytest.fixture(autouse=True)
def _clear_ephemeral_auth_state():
    if os.environ.get("APP_ENV") == "test":
        with SessionLocal() as db:
            db.execute(text("DELETE FROM auth_rate_limit"))
            db.execute(text("DELETE FROM email_codes"))
            db.commit()
    yield
