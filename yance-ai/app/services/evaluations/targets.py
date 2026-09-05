import io
import json
import zipfile
from collections.abc import Callable

from app.services.applications.artifacts import render_artifact
from app.services.evaluations.contracts import EvalCaseContract, TargetOutput
from app.services.policies.eligibility import _evaluate, exact_quote_span
from app.services.policies.retrieval import _lexical_score, _tokens


def _retrieval(case: EvalCaseContract) -> TargetOutput:
    query = str(case.input["query"])
    candidates = list(case.input["candidates"])
    k = max(1, int(case.input.get("k", 10)))
    query_tokens = _tokens(query)
    ranked = sorted(
        candidates,
        key=lambda item: (
            -_lexical_score(
                query_tokens,
                f"{item.get('title', '')} {item.get('content', '')}",
            ),
            str(item["id"]),
        ),
    )[:k]
    ids = [str(item["id"]) for item in ranked]
    return TargetOutput(
        answer={"ranked_ids": ids, "k": k},
        evidence=[
            {
                "expectation": str(item),
                "observed": str(item) if item in ids else "not retrieved",
                "source_reference": str(item),
                "passed": item in ids,
            }
            for item in case.ground_truth.get("relevant_ids", [])
        ],
    )


def _eligibility(case: EvalCaseContract) -> TargetOutput:
    facts = case.input["facts"]
    criteria: dict[str, str] = {}
    missing_information: list[str] = []
    hard_failures: list[str] = []
    observations = []
    for rule in case.input["rules"]:
        name = str(rule["name"])
        actual = facts.get(rule["fact_key"])
        quote = str(rule["source_quote"])
        source_text = str(rule["source_text"])
        span = exact_quote_span(source_text, quote)
        missing = actual in (None, "", []) and rule["operator"] != "exists"
        if span is None:
            status = "UNVERIFIED_SOURCE"
            missing_information.append(f"{name}: source")
        elif missing:
            status = "MISSING"
            missing_information.append(str(rule["fact_key"]))
        else:
            passed = _evaluate(actual, str(rule["operator"]), rule.get("expected"))
            status = "PASS" if passed else "FAIL"
            if not passed and rule.get("is_hard_gate"):
                hard_failures.append(name)
        criteria[name] = status
        observations.append(
            {
                "expectation": str(rule.get("article") or name),
                "observed": quote if span else "exact quote not found",
                "source_reference": str(rule.get("article") or ""),
                "passed": span is not None,
            }
        )
    if hard_failures:
        overall = "NOT_ELIGIBLE"
        required_action = "stop_and_explain"
    elif missing_information:
        overall = "NEED_MORE_INFORMATION"
        required_action = "collect_missing_information"
    else:
        overall = "POTENTIALLY_ELIGIBLE"
        required_action = "human_review"
    return TargetOutput(
        answer={
            "overall_status": overall,
            "criteria": criteria,
            "missing_information": missing_information,
            "hard_failures": hard_failures,
            "required_action": required_action,
        },
        evidence=observations,
    )


def _citation(case: EvalCaseContract) -> TargetOutput:
    source_text = str(case.input["source_text"])
    support = {}
    observations = []
    for claim in case.input["claims"]:
        claim_id = str(claim["claim_id"])
        quote = str(claim["quote"])
        span = exact_quote_span(source_text, quote)
        is_supported = span is not None
        support[claim_id] = is_supported
        expected_support = bool(case.ground_truth["support"][claim_id])
        observations.append(
            {
                "expectation": claim_id,
                "observed": f"span:{span[0]}-{span[1]}" if span else "exact quote not found",
                "source_reference": str(case.input["source_id"]),
                "passed": is_supported == expected_support,
            }
        )
    return TargetOutput(answer={"support": support}, evidence=observations)


def _hallucination(case: EvalCaseContract) -> TargetOutput:
    source_text = str(case.input["source_text"])
    requested = [str(item) for item in case.input["requested_claims"]]
    returned = [claim for claim in requested if exact_quote_span(source_text, claim) is not None]
    blocked = [claim for claim in requested if claim not in returned]
    return TargetOutput(
        answer={"returned_claims": returned, "blocked_claims": blocked},
        evidence=[
            {
                "expectation": claim,
                "observed": claim,
                "source_reference": str(case.input["source_id"]),
                "passed": True,
            }
            for claim in returned
        ],
    )


def _valid_export(content: dict, export_format: str) -> bool:
    payload, _, _ = render_artifact(content, export_format)
    if export_format == "pdf":
        return payload.startswith(b"%PDF-")
    if export_format == "json":
        return json.loads(payload)["schema_version"] == "application-brief-v1"
    if export_format in {"docx", "xlsx"}:
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            required = "word/document.xml" if export_format == "docx" else "xl/worksheets/sheet1.xml"
            return required in archive.namelist()
    return False


def _document_generation(case: EvalCaseContract) -> TargetOutput:
    facts = case.input["approved_facts"]
    content = {
        "schema_version": "application-brief-v1",
        "title": facts["title"],
        "company_name": facts["company_name"],
        "disclaimer": "本文件为证据型工作稿，正式提交前必须由授权人员复核。",
        "executive_summary": facts["executive_summary"],
        "eligibility": case.input["eligibility"],
        "criteria": case.input["criteria"],
        "requirements": case.input["requirements"],
        "evidence": case.input["evidence"],
    }
    valid_formats = [
        export_format
        for export_format in case.input["formats"]
        if _valid_export(content, str(export_format))
    ]
    observations = []
    for evidence in case.input["evidence"]:
        quote = str(evidence["quote"])
        passed = bool(evidence.get("verified")) and exact_quote_span(
            str(evidence.get("source_text", "")), quote
        ) is not None
        observations.append(
            {
                "expectation": str(evidence["source_title"]),
                "observed": quote if passed else "unverified evidence",
                "source_reference": str(evidence["source_title"]),
                "passed": passed,
            }
        )
    return TargetOutput(
        answer={"content": content, "valid_formats": valid_formats},
        evidence=observations,
    )


TARGETS: dict[str, Callable[[EvalCaseContract], TargetOutput]] = {
    "policy_retrieval_eval": _retrieval,
    "eligibility_eval": _eligibility,
    "citation_eval": _citation,
    "hallucination_eval": _hallucination,
    "document_generation_eval": _document_generation,
}


def execute_target(case: EvalCaseContract) -> TargetOutput:
    return TARGETS[case.eval_type](case)
