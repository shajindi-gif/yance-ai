from app.services.policy_engine.deterministic import _is_blocking, final_gate
from app.services.policy_engine.evaluator import validate_evidence
from app.services.policy_engine.schemas import (
    CriterionEvaluation,
    CriterionResult,
    EligibilityJudgment,
    OverallResult,
)


def test_safety_environment_and_credit_requirements_are_blocking():
    assert _is_blocking("近三年未发生重大安全事故") is True
    assert _is_blocking("企业不得存在环境违法记录") is True
    assert _is_blocking("企业社会信用记录良好") is True


def test_advisory_awards_remain_non_blocking():
    assert _is_blocking("获得创新创业大赛奖励可加分") is False


def test_failed_blocking_criterion_cannot_be_eligible():
    assert final_gate(["PASS", "FAIL"], [True, True]) == "NOT_ELIGIBLE"
    assert final_gate(["PASS", "INSUFFICIENT"], [True, True]) == "INSUFFICIENT_INFO"


def test_evidence_gate_rejects_numeric_substring_as_source():
    judgment = EligibilityJudgment(
        criteria=[
            CriterionEvaluation(
                criterion="研发费用比例",
                enterprise_fact="45%",
                policy_requirement="研发费用占比不低于40%",
                evidence_quote="研发费用占比不低于40%",
                result=CriterionResult.PASS,
            )
        ],
        overall_result=OverallResult.ELIGIBLE,
    )

    checked, hallucinations = validate_evidence(
        judgment,
        "研发费用占比不低于140%的企业可以申报。",
    )

    assert hallucinations
    assert checked.criteria[0].result == CriterionResult.INSUFFICIENT


def test_evidence_gate_relabels_unverified_quote_source():
    """ACC-19: a quote the gate could not find in the policy must not stay labelled 政策原文."""
    judgment = EligibilityJudgment(
        criteria=[
            CriterionEvaluation(
                criterion="研发费用比例",
                enterprise_fact="45%",
                policy_requirement="研发费用占比不低于40%",
                evidence_quote="研发费用占比不低于40%",
                evidence_source="政策原文",
                result=CriterionResult.PASS,
            ),
            CriterionEvaluation(
                criterion="注册地",
                enterprise_fact="上海",
                policy_requirement="注册地在上海市",
                evidence_quote="注册地在上海市",
                evidence_source="政策原文",
                result=CriterionResult.PASS,
            ),
        ],
        overall_result=OverallResult.ELIGIBLE,
    )

    checked, _ = validate_evidence(judgment, "申报企业注册地在上海市，研发费用占比不低于140%。")

    unverified, verified = checked.criteria
    assert unverified.evidence_source == "模型提议，未核验"
    assert verified.evidence_source == "政策原文"
