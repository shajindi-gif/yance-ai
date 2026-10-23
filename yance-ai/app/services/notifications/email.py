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
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import formataddr

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings

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
    match = re.match(r"^(.*?)<([^>]+)>$", settings.email_from.strip())
    if match and match.group(1).strip().strip('"'):
        display = match.group(1).strip().strip('"')
    return display, settings.smtp_user


@dataclass(frozen=True)
class DeliveryOutcome:
    status: str  # sent / retryable / failed / uncertain / deferred
    code: str | None = None


def _deliver_smtp(to: str, subject: str, body_text: str) -> DeliveryOutcome:
    display, address = _smtp_from_pair()
    message = EmailMessage()
    message["From"] = formataddr((display, address))
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body_text)
    message.add_alternative(_html_body(body_text), subtype="html")
    phase = "connect"
    try:
        with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=15) as server:
            server.login(address, settings.smtp_password)
            phase = "send"
            server.send_message(message)
        return DeliveryOutcome("sent")
    except (smtplib.SMTPAuthenticationError, smtplib.SMTPRecipientsRefused):
        return DeliveryOutcome("failed", "smtp_rejected")
    except smtplib.SMTPDataError as exc:
        return DeliveryOutcome(
            "retryable" if 400 <= exc.smtp_code < 500 else "failed", "smtp_data_rejected"
        )
    except (smtplib.SMTPException, OSError):
        return DeliveryOutcome(
            "uncertain" if phase == "send" else "retryable", "smtp_transport_error"
        )


def _deliver_resend(to: str, subject: str, body_text: str) -> DeliveryOutcome:
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
        if 200 <= response.status_code < 300:
            return DeliveryOutcome("sent")
        if response.status_code == 429:
            return DeliveryOutcome("retryable", "provider_rate_limited")
        if response.status_code >= 500 or response.status_code in {408, 409}:
            return DeliveryOutcome("uncertain", "provider_result_unknown")
        return DeliveryOutcome("failed", "provider_rejected")
    except httpx.HTTPError:
        return DeliveryOutcome("uncertain", "provider_transport_error")


def send_notification_email(to: str, subject: str, body_text: str) -> DeliveryOutcome:
    if not is_email_configured():
        return DeliveryOutcome("deferred", "email_not_configured")
    return (
        _deliver_smtp(to, subject, body_text)
        if settings.email_provider == "smtp"
        else _deliver_resend(to, subject, body_text)
    )


def send_email(to: str, subject: str, body_text: str) -> bool:
    """Compatibility API for synchronous login-code and existing invoice callers."""
    return send_notification_email(to, subject, body_text).status == "sent"


def dispatch_deadline_emails(db: Session, *, tenant_id=None, limit: int = 20) -> int:
    """Persist per-recipient intents, then process a bounded batch. Never mutate dedup keys."""
    from app.services.notifications.outbox import dispatch_outbox, enqueue_deadline_emails

    enqueue_deadline_emails(db, tenant_id=tenant_id)
    return dispatch_outbox(db, tenant_id=tenant_id, limit=limit)
