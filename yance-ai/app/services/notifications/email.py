"""Transactional email (deadline digests, login verification codes).

Dual provider via EMAIL_PROVIDER: "resend" (HTTP API) or "smtp" (e.g. Tencent
Exmail smtp.exmail.qq.com:465). Feature-flagged: disabled until EMAIL_ENABLED
plus the provider's credentials are configured, so local/CI runs never send
mail and callers degrade honestly (in-app only / 503). High-severity deadline
bands (T-7/T-3/T-1) and overdue items are emailed to tenant owners/admins;
lower bands stay in-app.
"""

from __future__ import annotations

import html
import re
import smtplib
from email.message import EmailMessage
from email.utils import formataddr

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import Membership, Notification, User, UserRole

RESEND_API = "https://api.resend.com/emails"
# Only these bands warrant an email; T-30/T-14 remain in-app to avoid noise.
EMAIL_BANDS = {"critical", "warning"}

_PLACEHOLDER_PREFIXES = ("REPLACE", "CHANGE-ME")


def _is_placeholder(value: str) -> bool:
    return not value or value.upper().startswith(_PLACEHOLDER_PREFIXES)


def _resend_configured() -> bool:
    return bool(settings.resend_api_key) and not _is_placeholder(settings.resend_api_key)


def _smtp_configured() -> bool:
    return not _is_placeholder(settings.smtp_user) and not _is_placeholder(settings.smtp_password)


def is_email_configured() -> bool:
    if not settings.email_enabled:
        return False
    if settings.email_provider == "smtp":
        return _smtp_configured()
    return _resend_configured()


def _html_body(body_text: str) -> str:
    return (
        f"<div style='font-family:sans-serif;line-height:1.7'>"
        f"{html.escape(body_text).replace(chr(10), '<br>')}"
        f"</div>"
    )


def _smtp_from_pair() -> tuple[str, str]:
    """(display_name, address) for the SMTP From header.

    Tencent Exmail rejects messages whose From address differs from the
    authenticated mailbox, so the address is always SMTP_USER; the display
    name is taken from EMAIL_FROM when present.
    """
    display = settings.smtp_user.split("@", 1)[0]
    match = re.match(r'^(.*?)<([^>]+)>$', settings.email_from.strip())
    if match and match.group(1).strip().strip('"'):
        display = match.group(1).strip().strip('"')
    return display, settings.smtp_user


def _send_via_smtp(to: str, subject: str, body_text: str) -> bool:
    display, address = _smtp_from_pair()
    message = EmailMessage()
    message["From"] = formataddr((display, address))
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body_text)
    message.add_alternative(_html_body(body_text), subtype="html")
    try:
        with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=15) as server:
            server.login(address, settings.smtp_password)
            server.send_message(message)
        return True
    except (smtplib.SMTPException, OSError):
        return False


def _send_via_resend(to: str, subject: str, body_text: str) -> bool:
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
                "html": _html_body(body_text),
            },
            timeout=15,
        )
        return 200 <= response.status_code < 300
    except httpx.HTTPError:
        return False


def send_email(to: str, subject: str, body_text: str) -> bool:
    """Send one email through the configured provider. True on success. Never raises."""
    if not is_email_configured():
        return False
    if settings.email_provider == "smtp":
        return _send_via_smtp(to, subject, body_text)
    return _send_via_resend(to, subject, body_text)


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
