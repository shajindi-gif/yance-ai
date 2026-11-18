"""P0-4: citation fidelity / ungrounded-sentence release gate (no database)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.services.report.quality import (
    ReportQualityError,
    assert_sellable_report_content,
    citation_fidelity_metrics,
    evaluate_report_citation_case,
    parse_report_document,
)

CASES_PATH = (
    Path(__file__).resolve().parents[1]
    / "evals"
    / "datasets"
    / "report_citation_eval"
    / "cases.json"
)


def test_report_citation_eval_dataset_passes_release_thresholds():
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    assert len(cases) >= 3
    results = [evaluate_report_citation_case(case) for case in cases]
    failed = [item for item in results if not item["passed"]]
    assert not failed, failed
    positive = next(item for item in results if item["id"] == "positive_with_exact_span")
    assert positive["metrics"]["ungrounded_sentence_ratio"] == 0
    assert positive["metrics"]["fabricated_quote_ratio"] == 0
    fabricated = next(item for item in results if item["id"] == "fabricated_quote_must_fail")
    assert fabricated["metrics"]["fabricated_quote_ratio"] == 1
    assert fabricated["metrics"]["release_gate_passed"] is False


def test_sellable_gate_rejects_fabricated_quote_when_source_provided():
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    bad = next(case for case in cases if case["id"] == "fabricated_quote_must_fail")
    with pytest.raises(ReportQualityError, match="citation_fidelity_failed"):
        assert_sellable_report_content(bad["content_json"], policy_texts=bad["policy_texts"])


def test_need_more_information_ratio_visible_without_failing_gate():
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    need_more = next(case for case in cases if case["id"] == "need_more_without_citation_ok")
    document = parse_report_document(need_more["content_json"])
    metrics = citation_fidelity_metrics(document)
    assert metrics["need_more_information_ratio"] == 1
    assert metrics["release_gate_passed"] is True
    assert_sellable_report_content(need_more["content_json"])
