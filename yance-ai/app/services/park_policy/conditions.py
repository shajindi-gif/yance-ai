"""Evidence-bearing policy conditions and the eligibility matrix.

Design constraints that come straight from the product requirements:

* A condition must be *addressable*: clause reference + verbatim quote + character
  offsets, so a reviewer can jump back to the original sentence.
* Evaluation is deterministic code.  No model call happens here, and a condition
  whose operator cannot be evaluated returns ``needs_review`` rather than a
  guessed boolean.
* Four outcomes are never collapsed into a score: satisfied / not_satisfied /
  insufficient / needs_review.
* An amount ceiling is never reported as "money the company will get".
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

MONETARY_UNITS = ("元", "万元", "亿元", "人民币元", "人民币万元")

# How an amount may be read.  Only ``entitlement_cap`` may be phrased as an
# upper bound of support; ``threshold`` is a floor the company must exceed.
AMOUNT_KINDS = (
    "entitlement_cap",   # 最高不超过 X —— 上限，不是可得金额
    "threshold",         # 须达到 X 以上
    "fixed_amount",      # 定额资助
    "ratio_cap",         # 比例上限
    "unknown",
)


class ConditionResult(StrEnum):
    SATISFIED = "satisfied"
    NOT_SATISFIED = "not_satisfied"
    INSUFFICIENT = "insufficient"
    NEEDS_REVIEW = "needs_review"


class MatrixVerdict(StrEnum):
    LIKELY_SATISFIED = "likely_satisfied"
    NOT_SATISFIED = "not_satisfied"
    INSUFFICIENT = "insufficient"
    NEEDS_REVIEW = "needs_review"


SUPPORTED_OPERATORS = (
    "eq", "ne", "in", "not_in", "gte", "lte", "between",
    "contains_any", "contains_all", "exists", "not_exists",
)


@dataclass(frozen=True)
class ConditionEvaluation:
    condition_id: str
    result: ConditionResult
    operator: str
    fact_key: str | None
    required: Any
    actual: Any = None
    unit: str | None = None
    period: str | None = None
    amount_kind: str | None = None
    clause_ref: str | None = None
    quote: str | None = None
    char_start: int | None = None
    char_end: int | None = None
    note: str | None = None
    review_required: bool = False

    @property
    def has_locatable_evidence(self) -> bool:
        return bool(self.quote) and self.char_start is not None and self.char_end is not None

    def as_dict(self) -> dict[str, Any]:
        return {
            "condition_id": self.condition_id,
            "result": str(self.result),
            "operator": self.operator,
            "fact_key": self.fact_key,
            "required": self.required,
            "actual": self.actual,
            "unit": self.unit,
            "period": self.period,
            "amount_kind": self.amount_kind,
            "clause_ref": self.clause_ref,
            "quote": self.quote,
            "char_start": self.char_start,
            "char_end": self.char_end,
            "has_locatable_evidence": self.has_locatable_evidence,
            "note": self.note,
            "review_required": self.review_required,
        }


@dataclass(frozen=True)
class EligibilityMatrix:
    policy_id: str
    policy_version_id: str | None
    verdict: MatrixVerdict
    conditions: tuple[ConditionEvaluation, ...]
    missing_facts: tuple[str, ...] = ()
    blocked_by: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()
    requires_human_confirmation: bool = True

    @property
    def counts(self) -> dict[str, int]:
        out = {str(item): 0 for item in ConditionResult}
        for condition in self.conditions:
            out[str(condition.result)] += 1
        return out

    def as_dict(self) -> dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "policy_version_id": self.policy_version_id,
            "verdict": str(self.verdict),
            "counts": self.counts,
            "missing_facts": list(self.missing_facts),
            "blocked_by": list(self.blocked_by),
            "notes": list(self.notes),
            # Explicit product statement: never presented as a probability.
            "disclaimer": (
                "结论仅表示在所列资料与政策版本范围内满足已核对条件，"
                "不构成政府认定、审核意见或获批承诺。"
            ),
            "requires_human_confirmation": True,
            "conditions": [item.as_dict() for item in self.conditions],
        }


def _fact_snapshot(facts: Mapping[str, Any], key: str) -> tuple[Any, str | None, str | None]:
    """Return (value, period, status) for a fact key.

    Facts may be plain scalars or records shaped like
    ``{"value": ..., "period": "2025", "confirmed": true}``.
    """
    raw = facts.get(key)
    if raw is None:
        return None, None, None
    if isinstance(raw, Mapping):
        return raw.get("value"), raw.get("period"), raw.get("status")
    return raw, None, None


def _to_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.replace(",", "").strip())
        except ValueError:
            return None
    return None


def _normalize_unit(unit: str | None) -> str | None:
    if not unit:
        return None
    unit = unit.strip()
    return unit or None


def evaluate_condition(
    condition: Mapping[str, Any],
    facts: Mapping[str, Any],
    *,
    policy_version_id: str | None = None,
) -> ConditionEvaluation:
    """Evaluate one stored ``policy_conditions`` row."""
    condition_id = str(condition.get("condition_id") or condition.get("id") or "unknown")
    operator = str(condition.get("operator") or "exists")
    fact_key = condition.get("fact_key")
    required = condition.get("expected_value")
    unit = _normalize_unit(condition.get("unit"))
    required_period = condition.get("period")
    amount_kind = condition.get("amount_kind")
    review_status = condition.get("review_status")
    common = {
        "clause_ref": condition.get("clause_ref"),
        "quote": condition.get("quote"),
        "char_start": condition.get("char_start"),
        "char_end": condition.get("char_end"),
    }

    # 1. A condition that has not been reviewed against the source text cannot
    #    produce a positive conclusion, even if it would evaluate cleanly.
    if review_status in {"draft", "needs_review"}:
        return ConditionEvaluation(
            condition_id=condition_id,
            result=ConditionResult.NEEDS_REVIEW,
            operator=operator,
            fact_key=fact_key,
            required=required,
            unit=unit,
            period=required_period,
            amount_kind=amount_kind,
            note=f"条件尚未与原文核对（review_status={review_status}）",
            review_required=True,
            **common,
        )

    if operator not in SUPPORTED_OPERATORS:
        return ConditionEvaluation(
            condition_id=condition_id,
            result=ConditionResult.NEEDS_REVIEW,
            operator=operator,
            fact_key=fact_key,
            required=required,
            unit=unit,
            period=required_period,
            amount_kind=amount_kind,
            note=f"运算符 {operator} 无法确定性求值，需人工复核",
            review_required=True,
            **common,
        )

    if not fact_key:
        return ConditionEvaluation(
            condition_id=condition_id,
            result=ConditionResult.NEEDS_REVIEW,
            operator=operator,
            fact_key=None,
            required=required,
            unit=unit,
            period=required_period,
            amount_kind=amount_kind,
            note="条件未绑定企业事实字段",
            review_required=True,
            **common,
        )

    actual, actual_period, actual_status = _fact_snapshot(facts, fact_key)

    if operator in {"exists", "not_exists"}:
        present = actual is not None and str(actual).strip() != ""
        if operator == "exists":
            result = ConditionResult.SATISFIED if present else ConditionResult.INSUFFICIENT
            note = None if present else f"缺少企业事实 {fact_key}"
        else:
            result = ConditionResult.SATISFIED if not present else ConditionResult.NOT_SATISFIED
            note = None if not present else f"企业存在 {fact_key}，命中排除条件"
        return ConditionEvaluation(
            condition_id=condition_id, result=result, operator=operator, fact_key=fact_key,
            required=required, actual=actual, unit=unit, period=required_period,
            amount_kind=amount_kind, note=note, **common,
        )

    if actual is None or str(actual).strip() == "":
        return ConditionEvaluation(
            condition_id=condition_id,
            result=ConditionResult.INSUFFICIENT,
            operator=operator,
            fact_key=fact_key,
            required=required,
            actual=None,
            unit=unit,
            period=required_period,
            amount_kind=amount_kind,
            note=f"企业事实 {fact_key} 缺失",
            **common,
        )

    if actual_status in {"conflicted", "unverified"}:
        return ConditionEvaluation(
            condition_id=condition_id,
            result=ConditionResult.NEEDS_REVIEW,
            operator=operator,
            fact_key=fact_key,
            required=required,
            actual=actual,
            unit=unit,
            period=required_period,
            amount_kind=amount_kind,
            note=f"企业事实 {fact_key} 状态为 {actual_status}，需客户确认后再判定",
            review_required=True,
            **common,
        )

    # 2. Statistics period mismatch: comparing 2025 R&D spend with a 2024
    #    threshold silently produces a wrong yes/no.
    if required_period and actual_period and str(required_period) != str(actual_period):
        return ConditionEvaluation(
            condition_id=condition_id,
            result=ConditionResult.NEEDS_REVIEW,
            operator=operator,
            fact_key=fact_key,
            required=required,
            actual=actual,
            unit=unit,
            period=required_period,
            amount_kind=amount_kind,
            note=f"统计期间不一致：政策要求 {required_period}，企业事实为 {actual_period}",
            review_required=True,
            **common,
        )
    if required_period and not actual_period:
        return ConditionEvaluation(
            condition_id=condition_id,
            result=ConditionResult.INSUFFICIENT,
            operator=operator,
            fact_key=fact_key,
            required=required,
            actual=actual,
            unit=unit,
            period=required_period,
            amount_kind=amount_kind,
            note=f"企业事实 {fact_key} 未标注统计期间，政策要求 {required_period}",
            **common,
        )

    # 3. Numeric operators require a comparable unit.  The unit check runs before
    #    numeric parsing so that "4.2万元" against a "%" threshold reports the real
    #    cause (unit mismatch) instead of a generic "not a number".
    if operator in {"gte", "lte", "between"}:
        actual_unit = None
        raw = facts.get(fact_key)
        if isinstance(raw, Mapping):
            actual_unit = _normalize_unit(raw.get("unit"))
        if unit and actual_unit and unit != actual_unit:
            return ConditionEvaluation(
                condition_id=condition_id,
                result=ConditionResult.NEEDS_REVIEW,
                operator=operator,
                fact_key=fact_key,
                required=required,
                actual=actual,
                unit=unit,
                period=required_period,
                amount_kind=amount_kind,
                note=f"单位不一致：政策要求 {unit}，企业事实为 {actual_unit}",
                review_required=True,
                **common,
            )

        left = _to_number(actual)
        if left is None:
            return ConditionEvaluation(
                condition_id=condition_id,
                result=ConditionResult.NEEDS_REVIEW,
                operator=operator,
                fact_key=fact_key,
                required=required,
                actual=actual,
                unit=unit,
                period=required_period,
                amount_kind=amount_kind,
                note=f"企业事实 {fact_key} 不是可比较数值（{actual!r}）",
                review_required=True,
                **common,
            )

        if operator == "between":
            bounds = required if isinstance(required, (list, tuple)) and len(required) == 2 else None
            if not bounds:
                return ConditionEvaluation(
                    condition_id=condition_id,
                    result=ConditionResult.NEEDS_REVIEW,
                    operator=operator,
                    fact_key=fact_key,
                    required=required,
                    actual=actual,
                    unit=unit,
                    period=required_period,
                    amount_kind=amount_kind,
                    note="between 需要两个边界值",
                    review_required=True,
                    **common,
                )
            low, high = _to_number(bounds[0]), _to_number(bounds[1])
            if low is None or high is None:
                return ConditionEvaluation(
                    condition_id=condition_id, result=ConditionResult.NEEDS_REVIEW,
                    operator=operator, fact_key=fact_key, required=required, actual=actual,
                    unit=unit, period=required_period, amount_kind=amount_kind,
                    note="区间边界不是数值", review_required=True, **common,
                )
            ok = low <= left <= high
        else:
            right = _to_number(required)
            if right is None:
                return ConditionEvaluation(
                    condition_id=condition_id, result=ConditionResult.NEEDS_REVIEW,
                    operator=operator, fact_key=fact_key, required=required, actual=actual,
                    unit=unit, period=required_period, amount_kind=amount_kind,
                    note="阈值不是数值", review_required=True, **common,
                )
            ok = left >= right if operator == "gte" else left <= right

        return ConditionEvaluation(
            condition_id=condition_id,
            result=ConditionResult.SATISFIED if ok else ConditionResult.NOT_SATISFIED,
            operator=operator,
            fact_key=fact_key,
            required=required,
            actual=actual,
            unit=unit,
            period=required_period,
            amount_kind=amount_kind,
            note=None if ok else "企业实际值未达到政策要求",
            **common,
        )

    if operator in {"in", "not_in"}:
        options = required if isinstance(required, (list, tuple, set)) else [required]
        options = {str(item) for item in options if item is not None}
        hit = str(actual) in options
        if operator == "in":
            result = ConditionResult.SATISFIED if hit else ConditionResult.NOT_SATISFIED
        else:
            result = ConditionResult.NOT_SATISFIED if hit else ConditionResult.SATISFIED
        return ConditionEvaluation(
            condition_id=condition_id, result=result, operator=operator, fact_key=fact_key,
            required=required, actual=actual, unit=unit, period=required_period,
            amount_kind=amount_kind, **common,
        )

    if operator in {"contains_any", "contains_all"}:
        options = required if isinstance(required, (list, tuple, set)) else [required]
        options = {str(item) for item in options if item is not None}
        values = actual if isinstance(actual, (list, tuple, set)) else [actual]
        values = {str(item) for item in values}
        ok = bool(options & values) if operator == "contains_any" else options.issubset(values)
        return ConditionEvaluation(
            condition_id=condition_id,
            result=ConditionResult.SATISFIED if ok else ConditionResult.NOT_SATISFIED,
            operator=operator, fact_key=fact_key, required=required, actual=actual,
            unit=unit, period=required_period, amount_kind=amount_kind, **common,
        )

    if operator in {"eq", "ne"}:
        ok = str(actual).strip() == str(required).strip()
        if operator == "ne":
            ok = not ok
        return ConditionEvaluation(
            condition_id=condition_id,
            result=ConditionResult.SATISFIED if ok else ConditionResult.NOT_SATISFIED,
            operator=operator, fact_key=fact_key, required=required, actual=actual,
            unit=unit, period=required_period, amount_kind=amount_kind, **common,
        )

    return ConditionEvaluation(
        condition_id=condition_id, result=ConditionResult.NEEDS_REVIEW, operator=operator,
        fact_key=fact_key, required=required, actual=actual, unit=unit,
        period=required_period, amount_kind=amount_kind,
        note="未覆盖的求值分支", review_required=True, **common,
    )


def build_matrix(
    *,
    policy_id: str,
    policy_version_id: str | None,
    conditions: Sequence[Mapping[str, Any]],
    facts: Mapping[str, Any],
    scope_results: Sequence[Mapping[str, Any]] = (),
) -> EligibilityMatrix:
    """Combine condition results and jurisdiction results into one matrix.

    Precedence is fixed and deliberately conservative:

    not_satisfied (any hard condition / scope) > needs_review > insufficient > likely_satisfied
    """
    evaluations = tuple(
        evaluate_condition(condition, facts, policy_version_id=policy_version_id)
        for condition in conditions
    )

    blocked: list[str] = []
    for scope in scope_results:
        if str(scope.get("verdict")) == "not_satisfied":
            blocked.append(f"scope:{scope.get('basis') or scope.get('scope_type')}")

    missing = sorted({
        str(item.fact_key)
        for item in evaluations
        if item.result is ConditionResult.INSUFFICIENT and item.fact_key
    })

    notes: list[str] = []
    hard_not_satisfied = [item for item in evaluations if item.result is ConditionResult.NOT_SATISFIED]
    needs_review = [item for item in evaluations if item.result is ConditionResult.NEEDS_REVIEW]

    if hard_not_satisfied or blocked:
        verdict = MatrixVerdict.NOT_SATISFIED
        if blocked:
            notes.append("政策适用范围不满足，其余条件不再作为符合依据")
    elif needs_review:
        verdict = MatrixVerdict.NEEDS_REVIEW
        notes.append(f"{len(needs_review)} 项条件需人工复核，暂不出具符合结论")
    elif missing:
        verdict = MatrixVerdict.INSUFFICIENT
        notes.append("存在缺失企业事实，需补证后再判定")
    else:
        verdict = MatrixVerdict.LIKELY_SATISFIED
        notes.append("在当前资料与政策版本范围内未见不符条件")

    locatable = sum(1 for item in evaluations if item.has_locatable_evidence)
    if evaluations and locatable < len(evaluations):
        notes.append(
            f"{len(evaluations) - locatable}/{len(evaluations)} 项条件缺少可定位的原文引用"
        )

    return EligibilityMatrix(
        policy_id=policy_id,
        policy_version_id=policy_version_id,
        verdict=verdict,
        conditions=evaluations,
        missing_facts=tuple(missing),
        blocked_by=tuple(blocked),
        notes=tuple(notes),
    )


def amount_display(condition: Mapping[str, Any]) -> str:
    """Human-readable amount label that never overstates support."""
    kind = condition.get("amount_kind") or "unknown"
    value = condition.get("expected_value")
    unit = condition.get("unit") or ""
    if kind == "entitlement_cap":
        return f"支持上限 {value}{unit}（上限不等于企业实际可得金额）"
    if kind == "threshold":
        return f"门槛要求 {value}{unit}（企业须达到的最低值）"
    if kind == "ratio_cap":
        return f"比例上限 {value}{unit}"
    if kind == "fixed_amount":
        return f"定额 {value}{unit}"
    return f"金额依据不足，需回原文核对：{value}{unit}"
