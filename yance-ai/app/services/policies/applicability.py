"""Conservative metadata gates shared by retrieval and eligibility.

A missing date is unknown, never an inferred perpetual validity. Historical
versions are retained: their legacy expiry_date may have meant a deadline.
"""
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import or_

from app.models.models import Policy, PolicyVersion


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def current_policy_clauses(now: datetime | None = None) -> tuple:
    now = now or datetime.now(UTC)
    return (
        Policy.status == "published",
        or_(Policy.effective_at.is_(None), Policy.effective_at <= now),
        or_(Policy.expires_at.is_(None), Policy.expires_at >= now),
        or_(Policy.deadline.is_(None), Policy.deadline >= now),
    )


def applicable_region_clauses(region: dict[str, Any]) -> tuple:
    return tuple(
        or_(getattr(Policy, key).is_(None), getattr(Policy, key) == "", getattr(Policy, key) == region[key])
        for key in ("province", "city", "district") if region.get(key)
    )


def policy_context_issues(
    policy: Policy | None, version: PolicyVersion | None, snapshot: dict[str, Any],
    *, now: datetime | None = None,
) -> list[str]:
    now = now or datetime.now(UTC)
    if not policy:
        return ["政策记录不存在或不可访问"]
    issues = []
    if policy.status != "published" or (version and version.status != "published"):
        issues.append("政策未发布或已撤回，需人工复核")
    if not version:
        issues.append("缺少不可变来源版本")
    for value, description, future in (
        (policy.effective_at, "政策尚未生效", True),
        (policy.expires_at, "政策有效期已结束", False),
        (policy.deadline, "当期申报已截止", False),
        (version.effective_date if version else None, "来源版本尚未生效", True),
        (version.expiry_date if version else None, "来源版本标注的有效期或旧版截止日已过", False),
        (version.application_deadline if version else None, "来源版本申报已截止", False),
    ):
        if value and ((_utc(value) > now) if future else (_utc(value) < now)):
            issues.append(description)
    if not policy.effective_at or not policy.expires_at:
        issues.append("政策生效或失效日期未核实，需人工复核")
    if not policy.deadline:
        issues.append("当前申报批次与截止日未核实，需人工复核")
    for key in ("province", "city", "district"):
        required = getattr(policy, key)
        actual = snapshot.get(key)
        if required and (not actual or actual != required):
            issues.append(f"企业地域{key}缺失或不符合政策适用地域")
    if not policy.province and not policy.city and policy.level != "national":
        issues.append("政策适用地域尚未核实")
    if version and (version.tenant_id not in (None, policy.tenant_id) or version.policy_id != policy.id):
        issues.append("政策版本范围不一致")
    return list(dict.fromkeys(issues))
