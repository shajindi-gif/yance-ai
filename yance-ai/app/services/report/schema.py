"""Frozen POLICY_REPORT opportunity cards.

Hard facts come from Opportunity / EligibilityResult / Evidence.
LLM must not rewrite these fields; next_step is deterministic from status + gaps.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

POSITIVE_ELIGIBILITY = frozenset({"ELIGIBLE", "POTENTIALLY_ELIGIBLE"})
ALLOWED_ELIGIBILITY = frozenset(
    {"ELIGIBLE", "POTENTIALLY_ELIGIBLE", "NOT_ELIGIBLE", "NEED_MORE_INFORMATION"}
)


class ReportCitation(BaseModel):
    quote: str = Field(min_length=1)
    article: str | None = None
    source_url: str | None = None
    quote_start: int | None = None
    quote_end: int | None = None
    verified: bool = True


class ReportCriterion(BaseModel):
    name: str
    status: str
    expected: Any = None
    actual: Any = None
    is_hard_gate: bool = False
    article: str | None = None


class OpportunityReportCard(BaseModel):
    opportunity_id: UUID
    policy_id: UUID
    policy_version_id: UUID | None = None
    profile_version_id: UUID | None = None
    policy_title: str = Field(min_length=1)
    eligibility_status: str
    eligibility_summary: str = Field(min_length=1)
    criteria: list[ReportCriterion] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    citations: list[ReportCitation] = Field(default_factory=list)
    next_step: str = Field(min_length=1)
    match_score: float | None = None
    support_amount: str | None = None
    deadline: str | None = None
    issuing_authority: str | None = None

    @field_validator("eligibility_status")
    @classmethod
    def _status_allowed(cls, value: str) -> str:
        if value not in ALLOWED_ELIGIBILITY:
            raise ValueError(f"invalid_eligibility_status:{value}")
        return value

    @model_validator(mode="after")
    def _positive_needs_citation(self) -> OpportunityReportCard:
        if self.eligibility_status in POSITIVE_ELIGIBILITY and not self.citations:
            raise ValueError("positive_eligibility_requires_verified_citation")
        return self


class PolicyOpportunityReportDocument(BaseModel):
    """Deliverable.content_json contract for POLICY_REPORT scans."""

    schema_version: str = "report-card-v1"
    company_id: UUID
    profile_version_id: UUID | None = None
    scan_id: UUID | None = None
    generated_at: datetime
    total_matches: int
    opportunities: list[OpportunityReportCard] = Field(default_factory=list)
    disclaimer: str = (
        "本报告基于企业提供资料与已入库政策快照生成，仅供客户自行复核。"
        "核对结果不代表政府认定或获批；匹配分不是获批概率。"
    )

    @model_validator(mode="after")
    def _counts_match(self) -> PolicyOpportunityReportDocument:
        if self.total_matches != len(self.opportunities):
            raise ValueError("total_matches_mismatch")
        return self


def deterministic_next_step(
    *,
    eligibility_status: str,
    gaps: list[str],
    deadline: str | None,
) -> str:
    gap_text = "；".join(gaps[:5]) if gaps else "当前无结构化缺口字段"
    if eligibility_status == "NOT_ELIGIBLE":
        base = f"资格引擎判定硬门槛不满足。请客户对照原文后决定是否停止投入。缺口：{gap_text}。"
    elif eligibility_status == "NEED_MORE_INFORMATION":
        base = f"证据不足。请先补齐并核对：{gap_text}；补齐后再复核资格，勿当作已符合。"
    elif eligibility_status in POSITIVE_ELIGIBILITY:
        base = (
            f"结构化规则未否决，但仍须客户复核固定版本后再行动。"
            f"下一步：核对申报窗口与材料。缺口：{gap_text}。"
        )
    else:
        base = f"状态未确认。请先复核原文与企业事实。缺口：{gap_text}。"
    if deadline:
        return f"{base} 已知截止日字段：{deadline}（以原文当期通知为准）。"
    return f"{base} 截止日字段未收录或待核实。"


def build_opportunity_card(
    *,
    opportunity: Any,
    eligibility: Any | None,
    citations: list[dict[str, Any]],
    policy: Any | None = None,
) -> OpportunityReportCard:
    snapshot = opportunity.policy_snapshot_json or {}
    status = (
        (eligibility.status if eligibility is not None else None)
        or opportunity.eligibility_status
        or "NEED_MORE_INFORMATION"
    )
    summary = (
        (eligibility.summary if eligibility is not None else None)
        or "尚未形成可验证资格结论。"
    )
    criteria_raw = list(eligibility.criteria_json or []) if eligibility is not None else []
    criteria = [
        ReportCriterion(
            name=str(item.get("name") or item.get("fact_key") or "条件"),
            status=str(item.get("status") or "UNKNOWN"),
            expected=item.get("expected"),
            actual=item.get("actual"),
            is_hard_gate=bool(item.get("is_hard_gate")),
            article=item.get("article"),
        )
        for item in criteria_raw
        if isinstance(item, dict)
    ]
    gaps = []
    if eligibility is not None:
        gaps.extend(str(item) for item in (eligibility.missing_information_json or []) if item)
    # Heuristic matcher materials are non-authoritative; only append when eligibility gaps empty.
    if not gaps:
        heuristic = (opportunity.evidence_json or {}).get("missing_materials") or []
        gaps.extend(f"待核实材料（非资格引擎）：{item}" for item in heuristic if item)

    title = (
        (policy.title if policy is not None and getattr(policy, "title", None) else None)
        or snapshot.get("title")
        or opportunity.title
        or "未命名政策"
    )
    deadline_value = None
    if policy is not None and getattr(policy, "deadline", None):
        deadline_value = policy.deadline.date().isoformat()
    elif snapshot.get("deadline"):
        deadline_value = str(snapshot.get("deadline"))

    support_amount = None
    if policy is not None and getattr(policy, "support_amount", None):
        support_amount = policy.support_amount
    elif snapshot.get("support_amount"):
        support_amount = str(snapshot.get("support_amount"))

    authority = None
    if policy is not None and getattr(policy, "issuing_authority", None):
        authority = policy.issuing_authority
    elif snapshot.get("issuing_authority"):
        authority = str(snapshot.get("issuing_authority"))

    policy_id = opportunity.policy_id or snapshot.get("policy_id")
    if policy_id is None:
        raise ValueError("opportunity_missing_policy_id")
    if not isinstance(policy_id, UUID):
        policy_id = UUID(str(policy_id))

    citation_models = [
        ReportCitation(
            quote=str(item["quote"]),
            article=item.get("article"),
            source_url=item.get("source_url"),
            quote_start=item.get("start", item.get("quote_start")),
            quote_end=item.get("end", item.get("quote_end")),
            verified=bool(item.get("verified", True)),
        )
        for item in citations
        if item.get("quote")
    ]

    return OpportunityReportCard(
        opportunity_id=opportunity.id,
        policy_id=policy_id,
        policy_version_id=opportunity.policy_version_id,
        profile_version_id=opportunity.profile_version_id,
        policy_title=str(title)[:500],
        eligibility_status=status,
        eligibility_summary=str(summary)[:2000],
        criteria=criteria,
        gaps=list(dict.fromkeys(gaps)),
        citations=citation_models,
        next_step=deterministic_next_step(
            eligibility_status=status, gaps=list(dict.fromkeys(gaps)), deadline=deadline_value
        ),
        match_score=float(opportunity.score) if opportunity.score is not None else None,
        support_amount=support_amount,
        deadline=deadline_value,
        issuing_authority=authority,
    )


def build_report_document(
    *,
    company_id: UUID,
    profile_version_id: UUID | None,
    scan_id: UUID | None,
    cards: list[OpportunityReportCard],
    generated_at: datetime | None = None,
) -> PolicyOpportunityReportDocument:
    return PolicyOpportunityReportDocument(
        company_id=company_id,
        profile_version_id=profile_version_id,
        scan_id=scan_id,
        generated_at=generated_at or datetime.now(UTC),
        total_matches=len(cards),
        opportunities=cards,
    )


def report_document_to_content_json(document: PolicyOpportunityReportDocument) -> dict[str, Any]:
    """Persist schema plus legacy summary keys used by older readers."""

    payload = document.model_dump(mode="json")
    payload["policy_ids"] = [card["policy_id"] for card in payload["opportunities"]]
    return payload
