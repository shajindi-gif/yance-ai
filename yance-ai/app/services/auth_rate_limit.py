"""Shared DB-backed fixed-window rate limiting for auth endpoints (S1 fix).

The previous in-memory counter (`auth._register_rate`) kept separate state per
uvicorn worker (4 workers → 4x the intended threshold) and reset on every
deploy/restart. Login had no rate limit at all. Both now count against the
auth_rate_limit table with a single atomic upsert, so limits hold across
workers and survive restarts.

Counters are ephemeral operational data, not business records: dropping the
table (migration downgrade) is a safe rollback.
"""

from __future__ import annotations

from datetime import UTC, timedelta

from sqlalchemy import case, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.models import AuthRateLimit, now_utc

REGISTER_WINDOW_SECONDS = 3600
REGISTER_LIMIT = 5  # per IP per hour (matches the previous documented intent)
LOGIN_FAIL_WINDOW_SECONDS = 900
# Failed logins per *account* per 15 minutes. Cleared only by that account's own
# successful login. Trade-off: anyone can lock a known account for one window by
# guessing wrong, so the limit is not set lower and the 429 text never reveals
# whether the account exists.
LOGIN_FAIL_LIMIT = 10
# Failed logins per *source IP* per 15 minutes, across all accounts (stops
# password spraying). Never cleared by a successful login — any account's
# success resetting it was the ACC-02 bypass. Higher than the account limit so
# one office NAT is not locked out by a few typos.
LOGIN_IP_FAIL_LIMIT = 30


def _upsert_hit(db: Session, key: str, window_seconds: int, limit: int) -> int | None:
    """Atomically start/extend a fixed window and return the new count."""
    now = now_utc()
    stale_before = now - timedelta(seconds=window_seconds)
    stmt = insert(AuthRateLimit).values(key=key, window_start=now, count=1)
    stmt = stmt.on_conflict_do_update(
        index_elements=[AuthRateLimit.key],
        set_={
            "count": case(
                (AuthRateLimit.window_start < stale_before, 1),
                else_=AuthRateLimit.count + 1,
            ),
            "window_start": case(
                (AuthRateLimit.window_start < stale_before, now),
                else_=AuthRateLimit.window_start,
            ),
        },
        where=or_(AuthRateLimit.window_start < stale_before, AuthRateLimit.count < limit),
    )
    count = db.scalar(stmt.returning(AuthRateLimit.count))
    db.commit()
    return count


def is_allowed(db: Session, key: str, *, limit: int, window_seconds: int) -> bool:
    """Current count (before this request) within limit? Read-only check."""
    now = now_utc()
    window_start = db.scalar(select(AuthRateLimit.window_start).where(AuthRateLimit.key == key))
    if window_start is None:
        return True
    if window_start.tzinfo is None:
        window_start = window_start.replace(tzinfo=UTC)
    if now - window_start >= timedelta(seconds=window_seconds):
        return True  # stale window will reset on next hit
    count = db.scalar(select(AuthRateLimit.count).where(AuthRateLimit.key == key)) or 0
    return count < limit


def register_attempt(db: Session, client_ip: str) -> bool:
    """Record a registration attempt; False means over limit (429)."""
    key = f"register:{client_ip}"
    return _upsert_hit(db, key, REGISTER_WINDOW_SECONDS, REGISTER_LIMIT) is not None


def _account_key(email: str) -> str:
    return f"loginfail-acct:{email.strip().lower()}"


def _ip_key(client_ip: str) -> str:
    return f"loginfail:{client_ip}"


def login_is_limited(db: Session, client_ip: str, email: str) -> bool:
    """True when either the source IP or the target account is currently blocked."""
    return not is_allowed(
        db, _ip_key(client_ip), limit=LOGIN_IP_FAIL_LIMIT, window_seconds=LOGIN_FAIL_WINDOW_SECONDS
    ) or not is_allowed(
        db, _account_key(email), limit=LOGIN_FAIL_LIMIT, window_seconds=LOGIN_FAIL_WINDOW_SECONDS
    )


def login_failure(db: Session, client_ip: str, email: str) -> bool:
    """Record a failed login against both the IP and the account; False means over limit."""
    ip_ok = _upsert_hit(db, _ip_key(client_ip), LOGIN_FAIL_WINDOW_SECONDS, LOGIN_IP_FAIL_LIMIT)
    account_ok = _upsert_hit(db, _account_key(email), LOGIN_FAIL_WINDOW_SECONDS, LOGIN_FAIL_LIMIT)
    return ip_ok is not None and account_ok is not None


def login_success(db: Session, email: str) -> None:
    """Clear only the authenticated account's own counter (never the shared IP counter)."""
    db.query(AuthRateLimit).filter(AuthRateLimit.key == _account_key(email)).delete()
    db.commit()
