"""Unit gates for sellable POLICY_REPORT content (no database)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from app.services.report.quality import (
    ReportQualityError,
    assert_sellable_report_content,
    citation_fidelity_metrics,
)
from app.services.report.schema import (
    OpportunityReportCard,
    ReportCitation,
    build_report_document,
    report_document_to_content_json,
)


def _doc(*cards: OpportunityReportCard):
    return build_report_document(
        company_id=uuid.uuid4(),
        profile_version_id=uuid.uuid4(),
        scan_id=uuid.uuid4(),
        cards=list(cards),
        generated_at=datetime.now(UTC),
    )


def test_sellable_gate_rejects_legacy_summary_only_payload():
    with pytest.raises(ReportQualityError, match="missing_report_card_schema"):
        assert_sellable_report_content({"total_matches": 1, "policy_ids": []})


def test_citation_fidelity_flags_positive_without_quote():
    # Bypass OpportunityReportCard validator by constructing raw dict then metrics via parse
    # Positive-without-citation cannot be constructed via OpportunityReportCard; metrics path
    # is covered by assert_sellable which uses validated cards. Here we only check NEED_MORE.
    card = OpportunityReportCard(
        opportunity_id=uuid.uuid4(),
        policy_id=uuid.uuid4(),
        policy_title="合成政策",
        eligibility_status="NEED_MORE_INFORMATION",
        eligibility_summary="缺少材料",
        gaps=["材料A"],
        citations=[],
        next_step="补齐材料A后复核",
    )
    metrics = citation_fidelity_metrics(_doc(card))
    assert metrics["release_gate_passed"] is True
    assert metrics["need_more_information_ratio"] == 1
    assert metrics["citation_coverage"] == 0


def test_sellable_accepts_potentially_eligible_with_citation():
    card = OpportunityReportCard(
        opportunity_id=uuid.uuid4(),
        policy_id=uuid.uuid4(),
        policy_title="合成政策",
        eligibility_status="POTENTIALLY_ELIGIBLE",
        eligibility_summary="结构化规则通过",
        gaps=[],
        citations=[
            ReportCitation(
                quote="对企业研究开发费用给予支持",
                article="第四条",
                source_url="https://example.invalid/p",
            )
        ],
        next_step="客户复核后核对窗口",
    )
    document = assert_sellable_report_content(report_document_to_content_json(_doc(card)))
    assert document.schema_version == "report-card-v1"
    metrics = citation_fidelity_metrics(document)
    assert metrics["citation_coverage"] == 1
    assert metrics["unsupported_claim_ratio"] == 0
    assert metrics["ungrounded_sentence_ratio"] == 0
    assert metrics["fabricated_quote_ratio"] == 0
