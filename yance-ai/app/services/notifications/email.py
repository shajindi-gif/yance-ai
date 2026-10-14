"""Transactional email via Resend (deadline digests).

Feature-flagged: disabled until RESEND_API_KEY + EMAIL_ENABLED are set, so
local/CI runs never send mail. High-severity deadline bands (T-7/T-3/T-1) and
overdue items are emailed to tenant owners/admins; lower bands stay in-app.
"""

from __future__ import annotations

import html

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import Membership, Notification, User, UserRole

RESEND_API = "https://api.resend.com/emails"
# Only these bands warrant an email; T-30/T-14 remain in-app to avoid noise.
EMAIL_BANDS = {"critical", "warning"}


def is_email_configured() -> bool:
    return bool(settings.resend_api_key and settings.email_enabled and not settings.resend_api_key.startswith("REPLACE"))


def send_email(to: str, subject: str, body_text: str) -> bool:
    """Send one email via Resend. Returns True on 2xx. Never raises."""
    if not is_email_configured():
        return False
    try:
        response = httpx.post(
            RESEND_API,
            headers={
                "Authorization": f"Bearer {settings.resend_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "from": settings.email_from,
                "to": [to],
                "subject": subject,
                "html": f"<div style='font-family:sans-serif;line-height:1.7'>{html.escape(body_text).replace(chr(10), '<br>')}</div>",
            },
            timeout=15,
        )
        return 200 <= response.status_code < 300
    except httpx.HTTPError:
        return False


def _recipient_emails(db: Session, tenant_id) -> list[str]:
    rows = db.execute(
        select(User.email)
        .join(Membership, Membership.user_id == User.id)
        .where(
            Membership.tenant_id == tenant_id,
            Membership.role.in_([UserRole.owner, UserRole.admin]),
            Membership.status == "active",
            User.is_active.is_(True),
        )
    ).all()
    return sorted({row[0] for row in rows})


def dispatch_deadline_emails(db: Session, *, tenant_id=None) -> int:
    """Email unread deadline notifications in high-severity bands.

    Marks each emailed notification with an email_sent_at timestamp via a
    dedup key suffix so a notification is emailed at most once. Returns count
    of notifications emailed.
    """
    if not is_email_configured():
        return 0
    query = select(Notification).where(
        Notification.kind == "deadline",
        Notification.read_at.is_(None),
        Notification.severity.in_(EMAIL_BANDS),
    )
    if tenant_id:
        query = query.where(Notification.tenant_id == tenant_id)
    sent = 0
    for notification in db.scalars(query).all():
        if notification.dedup_key.endswith(":emailed"):
            continue
        recipients = _recipient_emails(db, notification.tenant_id)
        delivered = False
        for email in recipients:
            if send_email(email, notification.title, notification.body or notification.title):
                delivered = True
        if delivered:
            notification.dedup_key = notification.dedup_key + ":emailed"
            sent += 1
    if sent:
        db.commit()
    return sent
