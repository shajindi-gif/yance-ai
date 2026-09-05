from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.models import (
    EligibilityResult,
    EligibilityRule,
    Evidence,
    Opportunity,
    PolicyBenefit,
    PolicyChunk,
    PolicyVersion,
    RequiredMaterial,
)
from app.services.policies.ingestion import latest_policy_version

ENGINE_VERSION = "deterministic-v1"
ALLOWED_OPERATORS = {"eq", "in", "contains", "gte", "lte", "exists"}


def exact_quote_span(content: str, quote: str) -> tuple[int, int] | None:
    """Find a literal quote while preventing numeric token substring matches."""
    if not quote:
        return None
    offset = 0
    while True:
        start = content.find(quote, offset)
        if start < 0:
            return None
        end = start + len(quote)
        left_numeric_collision = quote[0].isdigit() and start > 0 and content[start - 1].isdigit()
        right_numeric_collision = (
            quote[-1].isdigit() and end < len(content) and content[end].isdigit()
        )
        if not left_numeric_collision and not right_numeric_collision:
            return start, end
        offset = start + 1


def _expected(rule: EligibilityRule) -> Any:
    if "value" in rule.expected_json:
        return rule.expected_json["value"]
    return rule.expected_json.get("values")


def _evaluate(actual: Any, operator: str, expected: Any) -> bool:
    if operator == "exists":
        return actual not in (None, "", [])
    if operator == "eq":
        return actual == expected
    if operator == "in":
        return actual in (expected if isinstance(expected, list) else [expected])
    if operator == "contains":
        values = actual if isinstance(actual, list) else [actual]
        targets = expected if isinstance(expected, list) else [expected]
        return any(
            str(target).lower() in str(value).lower() for value in values for target in targets
        )
    if operator in {"gte", "lte"}:
        try:
            left, right = float(actual), float(expected)
        except (TypeError, ValueError):
            return False
        return left >= right if operator == "gte" else left <= right
    return False


def _exact_source(
    db: Session, version: PolicyVersion, rule: EligibilityRule
) -> tuple[PolicyChunk, int, int] | None:
    version_span = exact_quote_span(version.content, rule.source_quote)
    if version_span is None:
        return None
    chunks = db.scalars(
        select(PolicyChunk)
        .where(PolicyChunk.policy_version_id == version.id)
        .order_by(PolicyChunk.chunk_index)
    ).all()
    for chunk in chunks:
        chunk_span = exact_quote_span(chunk.content, rule.source_quote)
        if chunk_span is None:
            continue
        local_start, _ = chunk_span
        start = chunk.char_start + local_start
        end = start + len(rule.source_quote)
        if (start, end) == version_span and version.content[start:end] == rule.source_quote:
            return chunk, start, end
    return None


def evaluate_opportunity(
    db: Session, opportunity: Opportunity, snapshot: dict[str, Any]
) -> EligibilityResult:
    existing = db.scalar(
        select(EligibilityResult).where(
            EligibilityResult.opportunity_id == opportunity.id,
            EligibilityResult.tenant_id == opportunity.tenant_id,
        )
    )
    if existing:
        db.execute(delete(Evidence).where(Evidence.eligibility_result_id == existing.id))
        result = existing
    else:
        result = EligibilityResult(
            tenant_id=opportunity.tenant_id,
            opportunity_id=opportunity.id,
            profile_version_id=opportunity.profile_version_id,
            status="NEED_MORE_INFORMATION",
            confidence=0,
            summary="尚未形成可验证资格结论。",
        )
        db.add(result)
        db.flush()

    version = (
        db.get(PolicyVersion, opportunity.policy_version_id)
        if opportunity.policy_version_id
        else latest_policy_version(db, opportunity.policy_id)
        if opportunity.policy_id
        else None
    )
    rules = (
        list(
            db.scalars(
                select(EligibilityRule).where(
                    EligibilityRule.policy_version_id == version.id,
                    EligibilityRule.status == "active",
                )
            ).all()
        )
        if version
        else []
    )
    criteria: list[dict[str, Any]] = []
    missing: list[str] = []
    hard_failed = False
    evidence_rows: list[tuple[EligibilityRule, PolicyChunk, int, int]] = []

    if not version:
        missing.append("政策尚无不可变来源版本")
    if version and not rules:
        missing.append("政策尚无已审核的结构化资格规则")
    for rule in rules:
        actual = snapshot.get(rule.fact_key)
        source = _exact_source(db, version, rule)
        missing_fact = actual in (None, "", []) and rule.operator != "exists"
        if rule.operator not in ALLOWED_OPERATORS:
            state = "UNSUPPORTED"
            missing.append(f"规则“{rule.name}”使用了不支持的运算符")
        elif source is None:
            state = "UNVERIFIED_SOURCE"
            missing.append(f"规则“{rule.name}”缺少可逐字核验的政策原文")
        elif missing_fact:
            state = "MISSING"
            missing.append(f"企业画像缺少：{rule.fact_key}")
        else:
            passed = _evaluate(actual, rule.operator, _expected(rule))
            state = "PASS" if passed else "FAIL"
            if not passed and rule.is_hard_gate:
                hard_failed = True
            evidence_rows.append((rule, *source))
        criteria.append(
            {
                "rule_id": str(rule.id),
                "name": rule.name,
                "fact_key": rule.fact_key,
                "operator": rule.operator,
                "expected": _expected(rule),
                "actual": actual,
                "is_hard_gate": rule.is_hard_gate,
                "status": state,
                "article": rule.article,
            }
        )

    if hard_failed:
        status, summary = "NOT_ELIGIBLE", "至少一项已核验硬门槛不满足。"
    elif missing:
        status, summary = "NEED_MORE_INFORMATION", "缺少企业事实、规则或可核验政策原文。"
    elif rules:
        status, summary = (
            "POTENTIALLY_ELIGIBLE",
            "已通过结构化规则检查，仍需人工复核后方可确认符合。",
        )
    else:
        status, summary = "NEED_MORE_INFORMATION", "尚未形成可验证资格结论。"

    passed_count = sum(item["status"] == "PASS" for item in criteria)
    confidence = passed_count / len(criteria) if criteria and not missing else 0
    result.policy_version_id = version.id if version else None
    result.profile_version_id = opportunity.profile_version_id
    result.status = status
    result.confidence = confidence
    result.summary = summary
    result.criteria_json = criteria
    result.missing_information_json = list(dict.fromkeys(missing))
    result.engine_version = ENGINE_VERSION
    result.review_status = "not_reviewed"
    result.verified_at = datetime.now(UTC) if version and evidence_rows else None
    db.flush()

    for rule, chunk, start, end in evidence_rows:
        db.add(
            Evidence(
                tenant_id=opportunity.tenant_id,
                opportunity_id=opportunity.id,
                eligibility_result_id=result.id,
                policy_version_id=version.id,
                policy_chunk_id=chunk.id,
                eligibility_rule_id=rule.id,
                source_title=version.title,
                source_url=version.source_url,
                issuer=version.issuer,
                article=rule.article or chunk.article,
                quote=rule.source_quote,
                quote_start=start,
                quote_end=end,
                confidence=1,
                verifier="exact_span_v1",
                verified=version.content[start:end] == rule.source_quote,
            )
        )
    opportunity.eligibility_status = status
    opportunity.eligibility_confidence = confidence
    return result


def policy_supporting_data(db: Session, policy_version_id: UUID | None) -> tuple[list, list]:
    if not policy_version_id:
        return [], []
    materials = list(
        db.scalars(
            select(RequiredMaterial).where(RequiredMaterial.policy_version_id == policy_version_id)
        ).all()
    )
    benefits = list(
        db.scalars(
            select(PolicyBenefit).where(PolicyBenefit.policy_version_id == policy_version_id)
        ).all()
    )
    return materials, benefits
