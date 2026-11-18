"""POLICY_REPORT ReportCard contract — structured facts before PDF freeze."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.services.report.pdf import generate_match_report_pdf
from app.services.report.schema import (
    OpportunityReportCard,
    ReportCitation,
    build_opportunity_card,
    build_report_document,
    deterministic_next_step,
    report_document_to_content_json,
)
from app.services.safe_rendering import deny_external_url_fetcher


class CapturingHTML:
    last_string = ""

    def __init__(self, *, string, url_fetcher):
        type(self).last_string = string
        assert url_fetcher is deny_external_url_fetcher

    def write_pdf(self, target):
        target.write(b"%PDF-report-card")


def test_positive_eligibility_requires_citation():
    with pytest.raises(ValidationError, match="positive_eligibility_requires_verified_citation"):
        OpportunityReportCard(
            opportunity_id=uuid.uuid4(),
            policy_id=uuid.uuid4(),
            policy_title="合成政策",
            eligibility_status="POTENTIALLY_ELIGIBLE",
            eligibility_summary="可能符合",
            citations=[],
            next_step="复核",
        )


def test_build_card_uses_eligibility_gaps_not_only_heuristics():
    opportunity = SimpleNamespace(
        id=uuid.uuid4(),
        policy_id=uuid.uuid4(),
        policy_version_id=uuid.uuid4(),
        profile_version_id=uuid.uuid4(),
        title="合成机会",
        score=0.8,
        eligibility_status="NEED_MORE_INFORMATION",
        policy_snapshot_json={"title": "合成政策标题"},
        evidence_json={"missing_materials": ["启发式材料不应优先"]},
    )
    eligibility = SimpleNamespace(
        status="NEED_MORE_INFORMATION",
        summary="缺少研发费用证明",
        criteria_json=[
            {
                "name": "研发费用占比",
                "fact_key": "rd_ratio",
                "status": "MISSING",
                "expected": ">=5%",
                "actual": None,
                "is_hard_gate": True,
                "article": "第三条",
            }
        ],
        missing_information_json=["近三年研发费用专项审计"],
    )
    card = build_opportunity_card(
        opportunity=opportunity,
        eligibility=eligibility,
        citations=[],
        policy=None,
    )
    assert card.gaps == ["近三年研发费用专项审计"]
    assert "启发式" not in "".join(card.gaps)
    assert "补齐" in card.next_step
    assert card.criteria[0].name == "研发费用占比"


def test_report_document_content_json_and_pdf_render_structured_facts(monkeypatch):
    from app.models.models import Company, Opportunity, Policy
    from app.services.report import pdf as report_pdf

    monkeypatch.setattr(report_pdf, "HTML", CapturingHTML)
    company_id = uuid.uuid4()
    policy_id = uuid.uuid4()
    opportunity_id = uuid.uuid4()
    profile_version_id = uuid.uuid4()
    scan_id = uuid.uuid4()
    card = OpportunityReportCard(
        opportunity_id=opportunity_id,
        policy_id=policy_id,
        policy_version_id=uuid.uuid4(),
        profile_version_id=profile_version_id,
        policy_title="合成专项资金管理办法",
        eligibility_status="NEED_MORE_INFORMATION",
        eligibility_summary="缺少企业事实",
        gaps=["知识产权证明"],
        citations=[],
        next_step=deterministic_next_step(
            eligibility_status="NEED_MORE_INFORMATION",
            gaps=["知识产权证明"],
            deadline=None,
        ),
    )
    document = build_report_document(
        company_id=company_id,
        profile_version_id=profile_version_id,
        scan_id=scan_id,
        cards=[card],
        generated_at=datetime(2026, 11, 18, 12, 0, tzinfo=UTC),
    )
    payload = report_document_to_content_json(document)
    assert payload["schema_version"] == "report-card-v1"
    assert payload["total_matches"] == 1
    assert payload["opportunities"][0]["policy_id"] == str(policy_id)
    assert payload["opportunities"][0]["gaps"] == ["知识产权证明"]
    assert payload["opportunities"][0]["next_step"]

    company = Company(id=company_id, tenant_id=uuid.uuid4(), name="合成企业", metadata_json={})
    policy = Policy(id=policy_id, title="合成专项资金管理办法", status="published")
    opportunity = Opportunity(
        id=opportunity_id,
        tenant_id=company.tenant_id,
        company_id=company_id,
        policy_id=policy_id,
        profile_version_id=profile_version_id,
        scan_id=scan_id,
        title="合成机会",
        score=0.7,
        evidence_json={},
        eligibility_status="NEED_MORE_INFORMATION",
    )
    pdf = generate_match_report_pdf(
        company, [opportunity], [policy], report_document=document
    )
    assert pdf.startswith(b"%PDF")
    html = CapturingHTML.last_string
    assert "待系统判断" not in html
    assert "营业执照副本" not in html
    assert "知识产权证明" in html
    assert "report-card-v1" in html
    assert str(scan_id) in html
    assert "证据不足" in html or "NEED_MORE_INFORMATION" in html


def test_positive_card_with_citation_serializes():
    citation = ReportCitation(
        quote="对企业研究开发费用给予支持",
        article="第四条",
        source_url="https://example.invalid/policy",
        quote_start=10,
        quote_end=24,
    )
    card = OpportunityReportCard(
        opportunity_id=uuid.uuid4(),
        policy_id=uuid.uuid4(),
        policy_title="合成政策",
        eligibility_status="POTENTIALLY_ELIGIBLE",
        eligibility_summary="已通过结构化规则检查",
        citations=[citation],
        gaps=[],
        next_step="客户复核后核对申报窗口",
    )
    assert card.citations[0].verified is True
