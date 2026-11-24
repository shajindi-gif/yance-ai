"""Sellable POLICY_REPORT quality gates (structured cards + citation fidelity)."""

from __future__ import annotations

import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.models import PolicyVersion
from app.services.policies.eligibility import exact_quote_span
from app.services.report.schema import (
    POSITIVE_ELIGIBILITY,
    PolicyOpportunityReportDocument,
)

# Customer-facing claim sentences that must not float without a citation on
# positive cards. Structured briefs use short summaries, not open prose.
_SENTENCE_SPLIT = re.compile(r"(?<=[。！？；\n])|(?<=[.!;])\s+")


class ReportQualityError(ValueError):
    """Raised when a deliverable must not be sold or frozen as customer-ready."""


def parse_report_document(content_json: dict[str, Any] | None) -> PolicyOpportunityReportDocument:
    if not content_json:
        raise ReportQualityError("missing_content_json")
    if content_json.get("schema_version") != "report-card-v1":
        raise ReportQualityError("missing_report_card_schema")
    try:
        return PolicyOpportunityReportDocument.model_validate(content_json)
    except Exception as exc:  # noqa: BLE001 — surface as gate failure
        raise ReportQualityError(f"invalid_report_card_schema:{exc}") from exc


def _split_claim_sentences(text: str) -> list[str]:
    parts = [part.strip() for part in _SENTENCE_SPLIT.split(text or "") if part and part.strip()]
    return parts or ([text.strip()] if (text or "").strip() else [])


def citation_fidelity_metrics(
    document: PolicyOpportunityReportDocument,
    *,
    policy_texts: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Measure citation coverage and ungrounded-claim ratio for report cards.

    - positive statuses require verified citations (schema already enforces)
    - unsupported_claim_ratio: share of opportunities with no citation while
      asserting a positive eligibility status
    - ungrounded_sentence_ratio: share of customer-facing claim sentences on
      positive cards that lack a verified exact-span citation
    - fabricated_quote_ratio: citations whose quote is absent from policy text
      when policy_texts is supplied
    """

    sources = policy_texts or {}
    total = len(document.opportunities) or 1
    with_citation = 0
    positive_without_citation = 0
    empty_summary = 0
    need_more = 0
    claim_sentences = 0
    ungrounded_sentences = 0
    quote_checks = 0
    fabricated_quotes = 0
    unverified_flags = 0

    for card in document.opportunities:
        if card.citations:
            with_citation += 1
        if card.eligibility_status in POSITIVE_ELIGIBILITY and not card.citations:
            positive_without_citation += 1
        if not (card.eligibility_summary or "").strip():
            empty_summary += 1
        if card.eligibility_status == "NEED_MORE_INFORMATION":
            need_more += 1

        source_text = sources.get(str(card.policy_id), "")
        for citation in card.citations:
            quote_checks += 1
            if not citation.verified:
                unverified_flags += 1
            if source_text:
                if exact_quote_span(source_text, citation.quote) is None:
                    fabricated_quotes += 1

        if card.eligibility_status in POSITIVE_ELIGIBILITY:
            sentences = _split_claim_sentences(card.eligibility_summary)
            claim_sentences += len(sentences)
            grounded = bool(card.citations) and all(item.verified for item in card.citations)
            if source_text:
                grounded = grounded and all(
                    exact_quote_span(source_text, item.quote) is not None for item in card.citations
                )
            if not grounded:
                ungrounded_sentences += len(sentences)

    sentence_denom = claim_sentences or 1
    quote_denom = quote_checks or 1
    return {
        "opportunity_count": len(document.opportunities),
        "citation_coverage": with_citation / total,
        "positive_without_citation": positive_without_citation,
        "unsupported_claim_ratio": positive_without_citation / total,
        "empty_summary_ratio": empty_summary / total,
        "need_more_information_ratio": need_more / total,
        "claim_sentence_count": claim_sentences,
        "ungrounded_sentence_ratio": ungrounded_sentences / sentence_denom,
        "fabricated_quote_ratio": fabricated_quotes / quote_denom if quote_checks else 0.0,
        "unverified_citation_count": unverified_flags,
        "release_gate_passed": (
            positive_without_citation == 0
            and empty_summary == 0
            and ungrounded_sentences == 0
            and fabricated_quotes == 0
            and unverified_flags == 0
        ),
    }


def load_policy_texts_for_document(
    db: Session, document: PolicyOpportunityReportDocument
) -> dict[str, str]:
    """Resolve immutable PolicyVersion text for each card (prefer pinned version)."""

    texts: dict[str, str] = {}
    for card in document.opportunities:
        content = None
        if card.policy_version_id:
            version = db.get(PolicyVersion, card.policy_version_id)
            if version is not None:
                content = version.content
        if content is None:
            version = db.scalar(
                select(PolicyVersion)
                .where(PolicyVersion.policy_id == card.policy_id)
                .order_by(PolicyVersion.version.desc())
            )
            if version is not None:
                content = version.content
        if content:
            texts[str(card.policy_id)] = content
    return texts


def assert_sellable_report_content(
    content_json: dict[str, Any] | None,
    *,
    policy_texts: dict[str, str] | None = None,
) -> PolicyOpportunityReportDocument:
    """Hard gate before order creation / payment settlement for report SKUs."""

    document = parse_report_document(content_json)
    if document.total_matches < 1:
        raise ReportQualityError("no_opportunities")
    metrics = citation_fidelity_metrics(document, policy_texts=policy_texts)
    if not metrics["release_gate_passed"]:
        raise ReportQualityError(
            "citation_fidelity_failed:"
            f"unsupported={metrics['unsupported_claim_ratio']}:"
            f"ungrounded_sentences={metrics['ungrounded_sentence_ratio']}:"
            f"fabricated={metrics['fabricated_quote_ratio']}:"
            f"empty_summary={metrics['empty_summary_ratio']}"
        )
    for card in document.opportunities:
        if not card.next_step.strip():
            raise ReportQualityError(f"missing_next_step:{card.opportunity_id}")
        if not card.policy_title.strip():
            raise ReportQualityError(f"missing_policy_title:{card.opportunity_id}")
        if card.eligibility_status in POSITIVE_ELIGIBILITY:
            if any(not item.verified for item in card.citations):
                raise ReportQualityError(f"unverified_citation:{card.opportunity_id}")
    return document


def assert_sellable_report_in_db(
    db: Session, content_json: dict[str, Any] | None
) -> PolicyOpportunityReportDocument:
    """Parse + fidelity gate with exact-span checks against pinned policy versions."""

    document = parse_report_document(content_json)
    texts = load_policy_texts_for_document(db, document)
    return assert_sellable_report_content(content_json, policy_texts=texts)


def evaluate_report_citation_case(case: dict[str, Any]) -> dict[str, Any]:
    """Offline eval harness for synthetic company×policy report cards.

    Case shape:
      {
        "id": "...",
        "content_json": {...report-card-v1...},
        "policy_texts": {"<policy_id>": "..."},
        "expect_release_gate_passed": true|false,
        "max_ungrounded_sentence_ratio": 0.0,
        "max_fabricated_quote_ratio": 0.0,
      }
    """

    document = parse_report_document(case["content_json"])
    metrics = citation_fidelity_metrics(document, policy_texts=case.get("policy_texts") or {})
    max_ungrounded = float(case.get("max_ungrounded_sentence_ratio", 0.0))
    max_fabricated = float(case.get("max_fabricated_quote_ratio", 0.0))
    expect_pass = bool(case.get("expect_release_gate_passed", True))
    ratios_ok = (
        metrics["ungrounded_sentence_ratio"] <= max_ungrounded
        and metrics["fabricated_quote_ratio"] <= max_fabricated
    )
    if expect_pass:
        passed = bool(metrics["release_gate_passed"] and ratios_ok)
    else:
        passed = not bool(metrics["release_gate_passed"] and ratios_ok)
    return {
        "id": case.get("id") or str(document.company_id),
        "passed": passed,
        "metrics": metrics,
        "policy_ids": [str(card.policy_id) for card in document.opportunities],
    }
