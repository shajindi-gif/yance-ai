"""Email service dual-provider unit tests (no DB, no network).

Covers: is_email_configured() gating across providers, send_email routing to
SMTP vs Resend, the Tencent "From must equal authenticated user" alignment,
and honest failure (returns False, never raises) when unconfigured.
"""

import pytest

from app.core.config import settings
from app.services.notifications import email as svc


@pytest.fixture(autouse=True)
def reset_settings(monkeypatch):
    """Start every test from a clean, unconfigured email baseline."""
    monkeypatch.setattr(settings, "email_enabled", False)
    monkeypatch.setattr(settings, "email_provider", "resend")
    monkeypatch.setattr(settings, "resend_api_key", "")
    monkeypatch.setattr(settings, "smtp_user", "")
    monkeypatch.setattr(settings, "smtp_password", "")
    monkeypatch.setattr(settings, "smtp_host", "smtp.exmail.qq.com")
    monkeypatch.setattr(settings, "smtp_port", 465)
    monkeypatch.setattr(settings, "email_from", "衍策引擎AI <no-reply@mail.yance.ai>")


# ── is_email_configured gating ────────────────────────────────────────


def test_disabled_flag_blocks_even_with_credentials(monkeypatch):
    monkeypatch.setattr(settings, "email_enabled", False)
    monkeypatch.setattr(settings, "resend_api_key", "re_live_key")
    assert svc.is_email_configured() is False


def test_resend_provider_requires_real_key(monkeypatch):
    monkeypatch.setattr(settings, "email_enabled", True)
    monkeypatch.setattr(settings, "email_provider", "resend")
    monkeypatch.setattr(settings, "resend_api_key", "REPLACE_RESEND_KEY")
    assert svc.is_email_configured() is False  # placeholder rejected
    monkeypatch.setattr(settings, "resend_api_key", "re_live_key")
    assert svc.is_email_configured() is True


def test_smtp_provider_requires_user_and_password(monkeypatch):
    monkeypatch.setattr(settings, "email_enabled", True)
    monkeypatch.setattr(settings, "email_provider", "smtp")
    assert svc.is_email_configured() is False
    monkeypatch.setattr(settings, "smtp_user", "no-reply@mail.yance.ai")
    assert svc.is_email_configured() is False  # still missing password
    monkeypatch.setattr(settings, "smtp_password", "REPLACE_SMTP_CLIENT_AUTH_CODE")
    assert svc.is_email_configured() is False  # placeholder rejected
    monkeypatch.setattr(settings, "smtp_password", "smtp-auth-code-123")
    assert svc.is_email_configured() is True


# ── send_email routing ────────────────────────────────────────────────


def test_send_email_returns_false_when_unconfigured():
    # email_enabled is False via autouse fixture
    assert svc.send_email("user@example.com", "hi", "body") is False


def test_send_email_routes_to_resend(monkeypatch):
    monkeypatch.setattr(settings, "email_enabled", True)
    monkeypatch.setattr(settings, "email_provider", "resend")
    monkeypatch.setattr(settings, "resend_api_key", "re_live_key")

    captured = {}

    class FakeResponse:
        status_code = 200

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["json"] = json
        return FakeResponse()

    monkeypatch.setattr(svc.httpx, "post", fake_post)
    assert svc.send_email("user@example.com", "主题", "正文") is True
    assert captured["url"] == svc.RESEND_API
    assert captured["json"]["to"] == ["user@example.com"]
    assert captured["json"]["subject"] == "主题"
    assert "正文" in captured["json"]["html"]


def test_send_email_routes_to_smtp_and_aligns_from(monkeypatch):
    monkeypatch.setattr(settings, "email_enabled", True)
    monkeypatch.setattr(settings, "email_provider", "smtp")
    monkeypatch.setattr(settings, "smtp_user", "no-reply@mail.yance.ai")
    monkeypatch.setattr(settings, "smtp_password", "smtp-auth-code-123")
    # EMAIL_FROM display name differs from the authenticated mailbox address;
    # the From ADDRESS must still be forced to smtp_user (Tencent requirement).
    monkeypatch.setattr(settings, "email_from", "衍策引擎AI <other@yance.ai>")

    sent = {}

    class FakeSMTP:
        def __init__(self, host, port, timeout=None):
            sent["host"] = host
            sent["port"] = port

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def login(self, user, password):
            sent["login_user"] = user
            sent["login_password"] = password

        def send_message(self, message):
            sent["message"] = message
            sent["to"] = message["To"]
            sent["from"] = message["From"]

    monkeypatch.setattr(svc.smtplib, "SMTP_SSL", FakeSMTP)
    assert svc.send_email("user@example.com", "登录验证码", "您的验证码是：123456") is True

    assert sent["host"] == "smtp.exmail.qq.com"
    assert sent["port"] == 465
    assert sent["login_user"] == "no-reply@mail.yance.ai"
    assert sent["login_password"] == "smtp-auth-code-123"
    assert sent["to"] == "user@example.com"
    # From address aligned to authenticated user; display name preserved.
    assert "no-reply@mail.yance.ai" in sent["from"]
    assert "other@yance.ai" not in sent["from"]
    assert "衍策引擎AI" in sent["from"]
    # multipart/alternative carries both plain and html bodies
    assert sent["message"].get_content_type() == "multipart/alternative"


def test_smtp_send_failure_returns_false_never_raises(monkeypatch):
    monkeypatch.setattr(settings, "email_enabled", True)
    monkeypatch.setattr(settings, "email_provider", "smtp")
    monkeypatch.setattr(settings, "smtp_user", "no-reply@mail.yance.ai")
    monkeypatch.setattr(settings, "smtp_password", "smtp-auth-code-123")

    class BoomSMTP:
        def __init__(self, *a, **k):
            raise OSError("connection reset")

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    monkeypatch.setattr(svc.smtplib, "SMTP_SSL", BoomSMTP)
    assert svc.send_email("user@example.com", "s", "b") is False


def test_smtp_login_rejected_returns_false(monkeypatch):
    import smtplib

    monkeypatch.setattr(settings, "email_enabled", True)
    monkeypatch.setattr(settings, "email_provider", "smtp")
    monkeypatch.setattr(settings, "smtp_user", "no-reply@mail.yance.ai")
    monkeypatch.setattr(settings, "smtp_password", "wrong")

    class RejectSMTP:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def login(self, user, password):
            raise smtplib.SMTPAuthenticationError(535, b"auth failed")

        def send_message(self, message):
            raise AssertionError("must not send after failed login")

    monkeypatch.setattr(svc.smtplib, "SMTP_SSL", RejectSMTP)
    assert svc.send_email("user@example.com", "s", "b") is False
