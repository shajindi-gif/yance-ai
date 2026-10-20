"""Versioned synthetic safety regressions; not a real-world quality benchmark."""
import json
from decimal import Decimal
from pathlib import Path

import pytest
from test_payment_settlement import FakeSession, _records

from app.models.models import Entitlement
from app.services.payments.settlement import settle_payment, validate_settlement
from app.services.policy_engine.deterministic import _is_blocking, final_gate
from app.services.policy_engine.evaluator import validate_evidence
from app.services.policy_engine.schemas import (
    CriterionEvaluation,
    CriterionResult,
    EligibilityJudgment,
    OverallResult,
)

DATASET = json.loads(
    (Path(__file__).parents[1] / "evals/datasets/audit_safety_v1/cases.json").read_text()
)


@pytest.mark.parametrize("case", DATASET["cases"], ids=lambda c: c["id"])
def test_quote_must_support_the_actual_requirement(case):
    judgment = EligibilityJudgment(
        criteria=[CriterionEvaluation(
            criterion="资格条件", policy_requirement=case["quote"],
            evidence_quote=case["quote"], enterprise_fact="synthetic supplied fact",
            result=CriterionResult.PASS,
        )], overall_result=OverallResult.ELIGIBLE,
    )
    checked, _ = validate_evidence(judgment, case["source"])
    assert checked.criteria[0].result.value == case["expected"]


@pytest.mark.parametrize("results,blocking", [
    (["PASS"], [False]), (["UNKNOWN"], [True]), (["PASS", "FAIL"], [True]),
])
def test_incomplete_or_only_advisory_rules_cannot_confirm_eligibility(results, blocking):
    assert final_gate(results, blocking) == "INSUFFICIENT_INFO"


def test_mandatory_score_cannot_be_downgraded_to_advisory():
    assert _is_blocking("创新能力评价得分必须达到70分")
    assert _is_blocking("获得奖励的企业不得存在环境违法记录")


@pytest.mark.parametrize("amount", ["299.001", "NaN", "Infinity", "-299", True])
def test_settlement_rejects_non_exact_or_invalid_money(amount):
    order, payment, _ = _records()
    assert validate_settlement(order=order, payment=payment, paid_amount=amount, currency="CNY")


def test_settlement_checks_recorded_payment_currency():
    order, payment, _ = _records()
    payment.currency = "USD"
    assert validate_settlement(order=order, payment=payment, paid_amount=Decimal("299"), currency="CNY") == "currency_mismatch"


@pytest.mark.parametrize("state", ["cancelled", "refunded", "closed", "unknown"])
def test_late_payment_does_not_revive_terminal_order(state):
    order, payment, product = _records()
    order.status = state
    db = FakeSession([None, order, product, None, None])
    result = settle_payment(db, payment=payment, provider_event_id=f"late-{state}", event_type="TRADE_SUCCESS", paid_amount="299", currency="CNY", payload=b"synthetic")
    assert not result.accepted
    assert order.status == state
    assert not any(isinstance(item, Entitlement) for item in db.added)


def test_unreviewed_llm_extraction_never_claims_final_eligibility(monkeypatch):
    import asyncio

    from app.services.policy_engine import evaluator
    async def extracted(*args):
        return [{"criterion":"营业收入不低于100万元", "policy_quote":"营业收入不低于100万元"}]
    async def judged(*args):
        return EligibilityJudgment(criteria=[], overall_result=OverallResult.ELIGIBLE, summary="绝对符合"), {}
    monkeypatch.setattr(evaluator, "extract_criteria", extracted)
    monkeypatch.setattr(evaluator, "evaluate_criteria", judged)
    monkeypatch.setattr(evaluator, "normalize_facts", lambda _: {})
    monkeypatch.setattr(evaluator, "normalize_criteria", lambda rows: [{**rows[0], "kind":"numeric"}])
    monkeypatch.setattr(evaluator, "evaluate_deterministic", lambda *args: {"result":"PASS", "enterprise_value":200, "operator":">=", "threshold":100})
    result = asyncio.run(evaluator.evaluate_policy("test", "合成政策", "营业收入不低于100万元。", "national", "合成企业", {}))
    assert result.overall_result == OverallResult.REQUIRES_REVIEW
    assert "绝对符合" not in result.summary
    assert any(item.action == "人工复核" for item in result.next_best_actions)
