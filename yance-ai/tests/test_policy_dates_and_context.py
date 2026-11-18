"""Date extraction and advisory vs blocking context gates."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from app.services.policies.applicability import (
    policy_context_advisory_issues,
    policy_context_blocking_issues,
)
from app.services.policies.policy_dates import extract_dates_from_text


def test_extract_explicit_deadline_and_effective_dates():
    text = (
        "本办法自2024年1月1日起施行。"
        "有效期至2026年12月31日。"
        "申报截止时间为2026年6月30日。"
    )
    extracted = extract_dates_from_text(text)
    assert extracted.effective_at is not None
    assert extracted.effective_at.date().isoformat() == "2024-01-01"
    assert extracted.expires_at is not None
    assert extracted.expires_at.date().isoformat() == "2026-12-31"
    assert extracted.deadline is not None
    assert extracted.deadline.date().isoformat() == "2026-06-30"


def test_does_not_invent_dates_from_unrelated_numbers():
    text = "支持金额不超过500万元，惠及企业超过2023家。"
    extracted = extract_dates_from_text(text)
    assert extracted.effective_at is None
    assert extracted.expires_at is None
    assert extracted.deadline is None


def test_missing_dates_are_advisory_not_blocking_when_region_ok():
    policy = SimpleNamespace(
        status="published",
        effective_at=None,
        expires_at=None,
        deadline=None,
        province="上海市",
        city="上海市",
        district=None,
        level="municipal",
        tenant_id=None,
    )
    version = SimpleNamespace(
        status="published",
        effective_date=None,
        expiry_date=None,
        application_deadline=None,
        tenant_id=None,
        policy_id=None,
    )
    # Attach policy id consistency for version check
    version.policy_id = "x"
    policy.id = "x"
    snapshot = {"province": "上海市", "city": "上海市"}
    blocking = policy_context_blocking_issues(policy, version, snapshot)
    advisory = policy_context_advisory_issues(policy, version)
    assert blocking == []
    assert any("生效日期未收录" in item for item in advisory)
    assert any("截止日未收录" in item for item in advisory)


def test_expired_deadline_still_blocks():
    policy = SimpleNamespace(
        status="published",
        effective_at=datetime.now(UTC) - timedelta(days=100),
        expires_at=datetime.now(UTC) + timedelta(days=100),
        deadline=datetime.now(UTC) - timedelta(days=1),
        province="上海市",
        city="上海市",
        district=None,
        level="municipal",
        tenant_id=None,
        id="p1",
    )
    version = SimpleNamespace(
        status="published",
        effective_date=None,
        expiry_date=None,
        application_deadline=None,
        tenant_id=None,
        policy_id="p1",
    )
    blocking = policy_context_blocking_issues(
        policy, version, {"province": "上海市", "city": "上海市"}
    )
    assert any("申报已截止" in item for item in blocking)
