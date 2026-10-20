"""Synthetic temporal/region context regressions, not policy truth labels."""
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.models.models import Policy, PolicyVersion
from app.services.policies.applicability import policy_context_issues

NOW = datetime(2026, 10, 20, tzinfo=UTC)


def _source():
    policy = Policy(id=uuid4(), title="合成测试政策", status="published", level="municipal", province="上海市", city="上海市", effective_at=NOW-timedelta(days=30), expires_at=NOW+timedelta(days=365), deadline=NOW+timedelta(days=30))
    version = PolicyVersion(id=uuid4(), policy_id=policy.id, tenant_id=None, status="published", content="合成原文")
    return policy, version


@pytest.mark.parametrize("field,value,message", [
    ("status", "withdrawn", "撤回"),
    ("effective_at", NOW+timedelta(days=1), "尚未生效"),
    ("expires_at", NOW-timedelta(days=1), "有效期已结束"),
    ("deadline", NOW-timedelta(days=1), "申报已截止"),
    ("expires_at", None, "日期未核实"),
    ("deadline", None, "批次与截止日未核实"),
])
def test_context_does_not_imply_current_eligibility(field, value, message):
    policy, version = _source()
    setattr(policy, field, value)
    issues = policy_context_issues(policy, version, {"province":"上海市", "city":"上海市"}, now=NOW)
    assert any(message in item for item in issues)


def test_wrong_or_missing_region_requires_review():
    policy, version = _source()
    assert policy_context_issues(policy, version, {"province":"北京市"}, now=NOW)
    assert policy_context_issues(policy, version, {}, now=NOW)
    assert not policy_context_issues(policy, version, {"province":"上海市", "city":"上海市"}, now=NOW)


def test_version_identity_and_historical_expiry_are_not_ignored():
    policy, version = _source()
    version.policy_id = uuid4()
    version.expiry_date = NOW-timedelta(days=1)
    issues = policy_context_issues(policy, version, {"province":"上海市", "city":"上海市"}, now=NOW)
    assert any("范围不一致" in item for item in issues)
    assert any("旧版截止日已过" in item for item in issues)
