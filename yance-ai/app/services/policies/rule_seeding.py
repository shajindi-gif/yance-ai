"""Deterministic EligibilityRule candidates from policy text (no LLM fabrication).

Quotes must exact-span match PolicyVersion.content and at least one PolicyChunk.
Intended for ops coverage of high-priority slices (e.g. Shanghai + tech SMEs).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.models import EligibilityRule, Policy, PolicyChunk, PolicyVersion
from app.services.policies.eligibility import exact_quote_span

# Templates: keyword must appear in the chosen quote. expected values map to company profile facts.
RULE_TEMPLATES: tuple[dict[str, Any], ...] = (
    {
        "name": "适用地域为上海市",
        "fact_key": "province",
        "operator": "eq",
        "expected_json": {"value": "上海市"},
        "keywords": ("注册地在上海市", "本市注册", "上海市内", "上海市"),
    },
    {
        "name": "高新技术企业要求",
        "fact_key": "high_tech_status",
        "operator": "contains",
        "expected_json": {"value": "已认定"},
        "keywords": ("高新技术企业",),
    },
    {
        "name": "专精特新要求",
        "fact_key": "specialized_sme_status",
        "operator": "contains",
        "expected_json": {"value": "已认定"},
        "keywords": ("专精特新",),
    },
    {
        "name": "科技型中小企业要求",
        "fact_key": "tech_sme_status",
        "operator": "contains",
        "expected_json": {"value": "已认定"},
        "keywords": ("科技型中小企业",),
    },
    {
        "name": "人工智能产业要求",
        "fact_key": "industry",
        "operator": "contains",
        "expected_json": {"value": "人工智能"},
        "keywords": ("人工智能", "智能经济", "智能产业"),
    },
    {
        "name": "中小企业适用",
        "fact_key": "company_scale",
        "operator": "in",
        "expected_json": {"value": ["小型", "微型", "中型"]},
        "keywords": ("中小企业", "小型微型企业", "民营中小企业"),
    },
)


@dataclass(frozen=True)
class RuleCandidate:
    name: str
    fact_key: str
    operator: str
    expected_json: dict[str, Any]
    source_quote: str
    is_hard_gate: bool = True
    article: str | None = None


def _clause_around(content: str, start: int, end: int, *, max_len: int = 60) -> str:
    """Prefer a short punctuation-bounded clause that still contains the match."""

    left_break = max(content.rfind("。", 0, start), content.rfind("；", 0, start), content.rfind("\n", 0, start))
    right_break_candidates = [
        content.find("。", end),
        content.find("；", end),
        content.find("\n", end),
    ]
    right_break = min((i for i in right_break_candidates if i >= 0), default=-1)
    left = 0 if left_break < 0 else left_break + 1
    right = len(content) if right_break < 0 else right_break
    phrase = content[left:right].strip()
    if 6 <= len(phrase) <= max_len:
        return phrase
    # Symmetric window around the keyword.
    pad = max(0, (max_len - (end - start)) // 2)
    window = content[max(0, start - pad) : min(len(content), end + pad)].strip()
    return window if window else content[start:end]


def extract_rule_candidates(
    content: str,
    chunk_texts: list[str],
    *,
    include_shanghai_geo: bool = True,
) -> list[RuleCandidate]:
    """Extract hard-gate rule candidates whose quotes resolve in content and chunks."""

    if not content or not chunk_texts:
        return []
    found: list[RuleCandidate] = []
    seen_keys: set[str] = set()
    for template in RULE_TEMPLATES:
        if not include_shanghai_geo and template["fact_key"] == "province":
            continue
        for keyword in template["keywords"]:
            index = content.find(keyword)
            if index < 0:
                continue
            quote = _clause_around(content, index, index + len(keyword))
            if keyword not in quote:
                quote = keyword
            if exact_quote_span(content, quote) is None:
                continue
            if not any(exact_quote_span(chunk, quote) is not None for chunk in chunk_texts if chunk):
                # Fall back to the keyword token if the clause spans chunk boundaries.
                quote = keyword
                if exact_quote_span(content, quote) is None:
                    continue
                if not any(exact_quote_span(chunk, quote) is not None for chunk in chunk_texts if chunk):
                    continue
            key = f"{template['fact_key']}:{quote}"
            if key in seen_keys:
                break
            seen_keys.add(key)
            found.append(
                RuleCandidate(
                    name=str(template["name"]),
                    fact_key=str(template["fact_key"]),
                    operator=str(template["operator"]),
                    expected_json=dict(template["expected_json"]),
                    source_quote=quote,
                    is_hard_gate=True,
                )
            )
            break
    return found


def validate_candidate_against_version(
    *, content: str, chunk_texts: list[str], candidate: RuleCandidate
) -> str | None:
    """Return an error code or None when the candidate is import-safe."""

    if not candidate.source_quote.strip():
        return "empty_quote"
    if exact_quote_span(content, candidate.source_quote) is None:
        return "quote_not_in_version"
    if not any(exact_quote_span(chunk, candidate.source_quote) is not None for chunk in chunk_texts if chunk):
        return "quote_not_in_chunk"
    if candidate.operator not in {"eq", "neq", "in", "not_in", "contains", "gte", "lte", "gt", "lt", "exists"}:
        return "unsupported_operator"
    if not candidate.is_hard_gate:
        return "soft_gate_not_allowed_for_coverage_seed"
    return None


def list_slice_policies(
    db: Session,
    *,
    province: str | None = "上海市",
    limit: int = 80,
    require_topic_keywords: tuple[str, ...] = ("人工智能", "专精特新", "高新技术", "高企", "研发", "科技型中小"),
) -> list[Policy]:
    """Published policies for a province slice, or national topic slice when province is None."""

    filters = [Policy.status == "published"]
    if province:
        filters.append((Policy.province == province) | (Policy.city == province))
    base = select(Policy).where(*filters).order_by(Policy.updated_at.desc()).limit(max(limit * 5, 200))
    policies = list(db.scalars(base).all())
    if require_topic_keywords:
        topic = []
        other = []
        for policy in policies:
            blob = f"{policy.title or ''} {policy.industry or ''} {policy.content or ''}"
            if any(keyword in blob for keyword in require_topic_keywords):
                topic.append(policy)
            else:
                other.append(policy)
        # Topic-first ordering; for national mode drop non-topic rows.
        policies = topic if province is None else (topic + other)
    return policies[:limit]


def build_candidates_for_policy(
    db: Session,
    policy: Policy,
    *,
    include_shanghai_geo: bool | None = None,
) -> tuple[PolicyVersion | None, list[RuleCandidate]]:
    version = db.scalar(
        select(PolicyVersion)
        .where(PolicyVersion.policy_id == policy.id, PolicyVersion.status == "published")
        .order_by(PolicyVersion.version.desc())
    )
    if version is None or not version.content:
        return None, []
    chunks = list(
        db.scalars(
            select(PolicyChunk)
            .where(PolicyChunk.policy_version_id == version.id)
            .order_by(PolicyChunk.chunk_index)
        ).all()
    )
    chunk_texts = [chunk.content or "" for chunk in chunks]
    if include_shanghai_geo is None:
        include_shanghai_geo = (policy.province == "上海市") or (policy.city == "上海市")
    candidates = extract_rule_candidates(
        version.content, chunk_texts, include_shanghai_geo=include_shanghai_geo
    )
    safe: list[RuleCandidate] = []
    for candidate in candidates:
        error = validate_candidate_against_version(
            content=version.content, chunk_texts=chunk_texts, candidate=candidate
        )
        if error is None:
            safe.append(candidate)
    return version, safe


def coverage_metrics(db: Session, *, province: str = "上海市") -> dict[str, Any]:
    policies = list(
        db.scalars(
            select(Policy).where(
                Policy.status == "published",
                (Policy.province == province) | (Policy.city == province),
            )
        ).all()
    )
    versions_with_rules = 0
    versions_total = 0
    active_rules = 0
    for policy in policies:
        version = db.scalar(
            select(PolicyVersion)
            .where(PolicyVersion.policy_id == policy.id, PolicyVersion.status == "published")
            .order_by(PolicyVersion.version.desc())
        )
        if version is None:
            continue
        versions_total += 1
        count = len(
            list(
                db.scalars(
                    select(EligibilityRule).where(
                        EligibilityRule.policy_version_id == version.id,
                        EligibilityRule.status == "active",
                    )
                ).all()
            )
        )
        active_rules += count
        if count:
            versions_with_rules += 1
    return {
        "province": province,
        "published_policies": len(policies),
        "published_versions_considered": versions_total,
        "versions_with_active_rules": versions_with_rules,
        "active_rules": active_rules,
        "version_rule_coverage": (versions_with_rules / versions_total) if versions_total else 0.0,
    }


def seed_rules_for_slice(
    db: Session,
    *,
    province: str | None = "上海市",
    limit: int = 40,
    dry_run: bool = True,
    tenant_id: UUID | None = None,
) -> dict[str, Any]:
    """Insert hard-gate rules for a geographic/topic slice. Global corpus uses tenant_id=None."""

    before = coverage_metrics(db, province=province or "上海市") if province else {
        "province": None,
        "note": "national_topic_slice",
    }
    created = 0
    skipped = 0
    rejected = 0
    details: list[dict[str, Any]] = []
    for policy in list_slice_policies(db, province=province, limit=limit):
        version, candidates = build_candidates_for_policy(db, policy)
        if version is None or not candidates:
            rejected += 1
            details.append(
                {
                    "policy_id": str(policy.id),
                    "title": (policy.title or "")[:80],
                    "status": "no_candidates",
                }
            )
            continue
        chunk_texts = [
            chunk.content or ""
            for chunk in db.scalars(
                select(PolicyChunk).where(PolicyChunk.policy_version_id == version.id)
            ).all()
        ]
        policy_created = 0
        for candidate in candidates:
            error = validate_candidate_against_version(
                content=version.content or "", chunk_texts=chunk_texts, candidate=candidate
            )
            if error:
                rejected += 1
                continue
            existing = db.scalar(
                select(EligibilityRule).where(
                    EligibilityRule.policy_version_id == version.id,
                    EligibilityRule.fact_key == candidate.fact_key,
                    EligibilityRule.source_quote == candidate.source_quote,
                    EligibilityRule.status == "active",
                )
            )
            if existing:
                skipped += 1
                continue
            if dry_run:
                created += 1
                policy_created += 1
                continue
            db.add(
                EligibilityRule(
                    policy_id=policy.id,
                    policy_version_id=version.id,
                    tenant_id=tenant_id,
                    name=candidate.name,
                    fact_key=candidate.fact_key,
                    operator=candidate.operator,
                    expected_json=candidate.expected_json,
                    is_hard_gate=True,
                    source_quote=candidate.source_quote,
                    article=candidate.article,
                    status="active",
                )
            )
            created += 1
            policy_created += 1
        details.append(
            {
                "policy_id": str(policy.id),
                "version_id": str(version.id),
                "title": (policy.title or "")[:80],
                "status": "seeded" if policy_created else "skipped",
                "candidates": policy_created,
            }
        )
    if not dry_run:
        db.commit()
    after = (
        coverage_metrics(db, province=province)
        if province
        else {"province": None, "active_rules_delta": created}
    )
    return {
        "dry_run": dry_run,
        "province": province,
        "limit": limit,
        "created_or_would_create": created,
        "skipped_existing": skipped,
        "rejected": rejected,
        "before": before,
        "after": after,
        "details": details[:60],
    }
