from statistics import mean

from app.services.evaluations.contracts import (
    DIMENSIONS,
    CaseExecution,
    DatasetCard,
    Dimension,
    DimensionResult,
    EvalCaseContract,
    TargetOutput,
)


def _ratio(matches: int, total: int) -> float:
    return matches / total if total else 1.0


def _score_retrieval(case: EvalCaseContract, output: TargetOutput) -> dict[Dimension, tuple]:
    predicted = output.answer["ranked_ids"]
    relevant = set(case.ground_truth["relevant_ids"])
    candidates = {str(item["id"]) for item in case.input["candidates"]}
    first_rank = next((index for index, item in enumerate(predicted, 1) if item in relevant), None)
    precision = _ratio(sum(item in relevant for item in predicted), len(predicted))
    recall = _ratio(sum(item in relevant for item in predicted), len(relevant))
    return {
        "correctness": (0 if first_rank is None else 1 / first_rank, True, "MRR for the first relevant policy."),
        "completeness": (recall, True, "Recall@k against relevant policy identifiers."),
        "evidence": (precision, True, "Precision@k of source policy identifiers."),
        "citation_accuracy": (None, False, "Retrieval does not emit claim citations."),
        "hallucination": (float(set(predicted) <= candidates), True, "Returned identifiers must exist in the candidate corpus."),
        "actionability": (None, False, "Retrieval ranking has no next-action contract."),
    }


def _score_eligibility(case: EvalCaseContract, output: TargetOutput) -> dict[Dimension, tuple]:
    expected = case.ground_truth
    actual = output.answer
    expected_criteria = expected["criteria"]
    actual_criteria = actual["criteria"]
    criterion_accuracy = _ratio(
        sum(actual_criteria.get(key) == value for key, value in expected_criteria.items()),
        len(expected_criteria),
    )
    evidence_score = _ratio(sum(item.passed for item in output.evidence), len(output.evidence))
    return {
        "correctness": (float(actual["overall_status"] == expected["overall_status"]), True, "Exact four-state overall decision."),
        "completeness": (criterion_accuracy, True, "Every expected rule has the expected state."),
        "evidence": (evidence_score, True, "Rules retain an exact policy-source observation."),
        "citation_accuracy": (evidence_score, True, "Rule quotations resolve to exact source spans."),
        "hallucination": (float(set(actual_criteria) <= {str(rule["name"]) for rule in case.input["rules"]}), True, "No rule may be invented outside the input contract."),
        "actionability": (float(actual["required_action"] == expected["required_action"]), True, "Next action must follow the resulting state."),
    }


def _score_citation(case: EvalCaseContract, output: TargetOutput) -> dict[Dimension, tuple]:
    expected = case.ground_truth["support"]
    actual = output.answer["support"]
    accuracy = _ratio(sum(actual.get(key) == value for key, value in expected.items()), len(expected))
    false_positive = any(actual.get(key) and not value for key, value in expected.items())
    return {
        "correctness": (accuracy, True, "Exact support decision per claim."),
        "completeness": (_ratio(sum(key in actual for key in expected), len(expected)), True, "All claims receive a support decision."),
        "evidence": (accuracy, True, "Support decisions reconcile to the expected source."),
        "citation_accuracy": (accuracy, True, "Exact-span citation decision accuracy."),
        "hallucination": (float(not false_positive), True, "Unsupported citations must never pass."),
        "actionability": (None, False, "Citation validation has no workflow recommendation."),
    }


def _score_hallucination(case: EvalCaseContract, output: TargetOutput) -> dict[Dimension, tuple]:
    expected_returned = set(case.ground_truth["returned_claims"])
    expected_blocked = set(case.ground_truth["blocked_claims"])
    actual_returned = set(output.answer["returned_claims"])
    actual_blocked = set(output.answer["blocked_claims"])
    exact = actual_returned == expected_returned and actual_blocked == expected_blocked
    unsafe = bool(actual_returned & expected_blocked)
    return {
        "correctness": (float(exact), True, "Returned and blocked claim sets must match ground truth."),
        "completeness": (float(actual_returned | actual_blocked == expected_returned | expected_blocked), True, "Every requested claim is classified."),
        "evidence": (_ratio(sum(item.passed for item in output.evidence), len(output.evidence)), bool(output.evidence), "Returned claims retain exact source evidence."),
        "citation_accuracy": (_ratio(sum(item.passed for item in output.evidence), len(output.evidence)), bool(output.evidence), "Returned claims resolve to source spans."),
        "hallucination": (float(not unsafe), True, "Safety score is one only when no blocked claim is returned."),
        "actionability": (float(actual_blocked == expected_blocked), True, "Unsupported claims are explicitly blocked."),
    }


def _score_document(case: EvalCaseContract, output: TargetOutput) -> dict[Dimension, tuple]:
    content = output.answer["content"]
    expected = case.ground_truth
    required_fields = expected["required_fields"]
    field_score = _ratio(sum(field in content for field in required_fields), len(required_fields))
    valid_formats = set(output.answer["valid_formats"])
    expected_formats = set(expected["valid_formats"])
    evidence_score = _ratio(sum(item.passed for item in output.evidence), len(output.evidence))
    source_values = {
        str(case.input["approved_facts"]["company_name"]),
        str(case.input["approved_facts"]["title"]),
        str(case.input["approved_facts"]["executive_summary"]),
    }
    no_invented_primary_fact = all(
        str(content[key]) in source_values for key in ("company_name", "title", "executive_summary")
    )
    return {
        "correctness": (float(content["company_name"] == expected["company_name"] and content["eligibility"]["status"] == expected["eligibility_status"]), True, "Approved company fact and eligibility state are preserved."),
        "completeness": (mean([field_score, float(valid_formats == expected_formats)]), True, "Required fields and requested file formats are present."),
        "evidence": (evidence_score, bool(output.evidence), "Included evidence remains verified against its supplied source."),
        "citation_accuracy": (evidence_score, bool(output.evidence), "Document citations resolve to exact source spans."),
        "hallucination": (float(no_invented_primary_fact), True, "Primary narrative facts must come from approved inputs."),
        "actionability": (float(bool(content.get("disclaimer")) and bool(content.get("eligibility"))), True, "Output includes review guardrail and decision state."),
    }


SCORERS = {
    "policy_retrieval_eval": _score_retrieval,
    "eligibility_eval": _score_eligibility,
    "citation_eval": _score_citation,
    "hallucination_eval": _score_hallucination,
    "document_generation_eval": _score_document,
}


def score_output(case: EvalCaseContract, output: TargetOutput, card: DatasetCard) -> CaseExecution:
    raw = SCORERS[case.eval_type](case, output)
    dimensions = [
        DimensionResult(
            dimension=dimension,
            score=raw[dimension][0],
            is_applicable=raw[dimension][1],
            rationale=raw[dimension][2],
        )
        for dimension in DIMENSIONS
    ]
    applicable = [item.score for item in dimensions if item.is_applicable and item.score is not None]
    overall = mean(applicable) if applicable else None
    by_name = {item.dimension: item.score for item in dimensions}
    passed = overall is not None and overall >= card.thresholds.get("overall", 0)
    for name, threshold in card.thresholds.items():
        if name == "overall":
            continue
        passed = passed and by_name.get(name) is not None and by_name[name] >= threshold
    hallucination_score = by_name.get("hallucination")
    return CaseExecution(
        case_id=case.case_id,
        status="completed",
        model_answer=output.answer,
        dimensions=dimensions,
        evidence=output.evidence,
        error_types=output.error_types,
        hallucination_detected=hallucination_score is not None and hallucination_score < 1,
        overall_score=overall,
        passed=passed,
        cost_usd=0,
    )
