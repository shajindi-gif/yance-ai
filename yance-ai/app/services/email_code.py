"""Email verification codes for passwordless login (DB-backed rate limiting).

Security posture (ported rules from the fengyuxueye audit fixes):
- Codes are stored only as SHA-256 hashes, 10-minute TTL, single-use.
- Rate limits are enforced by querying the email_codes table, so they hold
  across all 4 uvicorn workers (the in-memory _register_rate counter does not).
- When the Resend channel is not configured the endpoint must return 503 —
  never a fake ``success: true``.
- Failed sends roll back so they do not consume a rate-limit slot.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.models import EmailCode, now_utc
from app.services.notifications.email import send_email

CODE_TTL = timedelta(minutes=10)
MAX_ATTEMPTS = 5
SEND_COOLDOWN = timedelta(seconds=60)  # per email
PER_EMAIL_PER_HOUR = 5
PER_IP_PER_HOUR = 10


class RateLimited(Exception):
    def __init__(self, retry_after: int):
        self.retry_after = retry_after
        super().__init__(f"retry after {retry_after}s")


class EmailSendError(Exception):
    """Code was generated but could not be delivered."""


def generate_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_code(email: str, code: str) -> str:
    return hashlib.sha256(f"{email}|{code}".encode()).hexdigest()


def check_send_limits(db: Session, email: str, ip: str | None) -> None:
    """Raise RateLimited if this email/IP may not receive a new code now."""
    now = now_utc()
    last_created = db.scalar(
        select(func.max(EmailCode.created_at)).where(EmailCode.email == email)
    )
    if last_created is not None:
        if last_created.tzinfo is None:
            last_created = last_created.replace(tzinfo=now.timezone)
        elapsed = now - last_created
        if elapsed < SEND_COOLDOWN:
            raise RateLimited(int((SEND_COOLDOWN - elapsed).total_seconds()) or 1)

    window_start = now - timedelta(hours=1)
    per_email = db.scalar(
        select(func.count())
        .select_from(EmailCode)
        .where(EmailCode.email == email, EmailCode.created_at >= window_start)
    )
    if (per_email or 0) >= PER_EMAIL_PER_HOUR:
        raise RateLimited(3600)

    if ip:
        per_ip = db.scalar(
            select(func.count())
            .select_from(EmailCode)
            .where(EmailCode.ip_address == ip, EmailCode.created_at >= window_start)
        )
        if (per_ip or 0) >= PER_IP_PER_HOUR:
            raise RateLimited(3600)


def send_login_code(db: Session, email: str, ip: str | None) -> None:
    """Invalidate outstanding codes for this email, issue and deliver a new one.

    Commits only after successful delivery; a failed send rolls back so the
    cooldown slot is not consumed.
    """
    now = now_utc()
    stale = db.scalars(
        select(EmailCode).where(
            EmailCode.email == email,
            EmailCode.used_at.is_(None),
            EmailCode.expires_at > now,
        )
    ).all()
    for row in stale:
        row.used_at = now  # superseded — only the newest code can be used

    code = generate_code()
    db.add(
        EmailCode(
            email=email,
            code_hash=hash_code(email, code),
            purpose="login",
            expires_at=now + CODE_TTL,
            ip_address=ip,
        )
    )
    db.flush()
    delivered = send_email(
        email,
        "登录衍策引擎AI 的验证码",
        f"您的登录验证码是：{code}\n\n验证码 10 分钟内有效，仅可使用一次。\n"
        "如果这不是您本人的操作，请忽略本邮件，并检查账号安全。",
    )
    if not delivered:
        db.rollback()
        raise EmailSendError("verification email could not be delivered")
    db.commit()


def consume_login_code(db: Session, email: str, code: str) -> str:
    """Try to consume the newest live code for ``email``.

    Returns "ok" | "invalid" | "expired" | "too_many". Commits its own state
    changes (attempt counter / used marker) so failed verifications cannot be
    rewound by an unrelated rollback.
    """
    now = now_utc()
    row = db.scalar(
        select(EmailCode)
        .where(
            EmailCode.email == email,
            EmailCode.purpose == "login",
            EmailCode.used_at.is_(None),
        )
        .order_by(EmailCode.created_at.desc())
        .limit(1)
    )
    if row is None:
        return "invalid"
    expires_at = row.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=now.timezone)
    if expires_at < now:
        row.used_at = now  # burn expired code so it never lingers
        db.commit()
        return "expired"
    if row.attempts >= MAX_ATTEMPTS:
        return "too_many"
    if not secrets.compare_digest(row.code_hash, hash_code(email, code)):
        row.attempts += 1
        db.commit()
        return "invalid"
    row.used_at = now  # single-use: commit before provisioning so replay is impossible
    db.commit()
    return "ok"
