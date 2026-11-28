"""Unit tests for deterministic EligibilityRule candidate extraction."""

from __future__ import annotations

from app.services.policies.rule_seeding import (
    RuleCandidate,
    extract_rule_candidates,
    validate_candidate_against_version,
)


def test_extracts_shanghai_and_high_tech_with_exact_quotes():
    content = (
        "本办法适用于注册地在上海市的高新技术企业。"
        "申报单位应为人工智能领域相关企业。"
    )
    chunks = [content]
    # 1449500/24486c9: a province gate attaches only when the policy is recorded
    # for that province, and keyword industry gates were dropped as noise.
    candidates = extract_rule_candidates(content, chunks, policy_province="上海市")
    names = {item.name for item in candidates}
    assert "适用地域为上海市" in names
    assert "高新技术企业要求" in names
    assert "人工智能产业要求" not in names
    assert "适用地域为上海市" not in {
        item.name for item in extract_rule_candidates(content, chunks, policy_province="广东省")
    }
    for item in candidates:
        assert item.is_hard_gate is True
        assert item.source_quote in content
        assert validate_candidate_against_version(
            content=content, chunk_texts=chunks, candidate=item
        ) is None


def test_rejects_fabricated_quote():
    content = "支持本市科技型中小企业发展。"
    chunks = [content]
    bad = RuleCandidate(
        name="伪造",
        fact_key="province",
        operator="eq",
        expected_json={"value": "上海市"},
        source_quote="最高补贴五百万元且无需审核",
    )
    assert validate_candidate_against_version(
        content=content, chunk_texts=chunks, candidate=bad
    ) == "quote_not_in_version"


def test_keyword_must_remain_inside_quote():
    content = "第一条 总则。第二条 支持专精特新企业做强做大。第三条 附则。"
    chunks = [content]
    candidates = extract_rule_candidates(content, chunks)
    specialized = next(item for item in candidates if item.fact_key == "specialized_sme_status")
    assert "专精特新" in specialized.source_quote
