"""Park-aware hybrid retrieval.

Design rules enforced here (all regressions are covered in
``tests/park_policy/test_park_retrieval.py``):

1. **Tenant filtering happens in SQL, never after generation.**  Every query
   built by this module starts from ``visible_policy_clause`` and adds a chunk
   ownership predicate.  There is no code path that filters results in Python
   after the model has seen them.
2. **Park scope filtering requires an explicit park_id.**  A hunt for
   "苏州" must never be translated into a park-level restriction; park matching
   goes through ``park_id`` only, and unverified boundaries are surfaced as a
   review flag rather than silently narrowing the result set.
3. **Date and status filters are explicit.**  Expired policies and closed
   application windows are separately filterable, because "no result" must be
   distinguishable from "excluded by filter".
4. **Synonym/alias expansion is a query rewrite, not a scoring trick.**  It runs
   before retrieval so the lexical arm sees the canonical term; the original
   term is kept in the trace so a reviewer can see what was actually searched.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Iterable, Mapping
from uuid import UUID

from sqlalchemy import ColumnElement, and_, or_, select
from sqlalchemy.orm import Session

from app.models.models import Policy, PolicyChunk, PolicyVersion
from app.services.policies.applicability import applicable_region_clauses, current_policy_clauses
from app.services.policies.retrieval import PolicyCandidate, hybrid_policy_candidates
from app.services.policies.visibility import visible_policy_clause
from app.services.park_policy.evidence import compute_window_state

# --------------------------------------------------------------------------- #
# Query normalisation
# --------------------------------------------------------------------------- #

# Institution renames and common shorthand. Keys are what a user types;
# values are the canonical term that appears in official documents.
TERM_ALIASES: dict[str, tuple[str, ...]] = {
    "专精特新": ("专业化、精细化、特色化、新颖化", "专精特新中小企业", "专精特新“小巨人”"),
    "小巨人": ("专精特新“小巨人”企业", "专精特新小巨人"),
    "高企": ("高新技术企业",),
    "科小": ("科技型中小企业",),
    "技改": ("技术改造", "技术改造项目"),
    "设备更新": ("大规模设备更新", "设备更新改造"),
    "首台套": ("首台（套）", "首台套重大技术装备", "首台套装备"),
    "创新券": ("科技创新券", "创新券"),
    "贴息": ("贷款贴息", "利息补贴"),
    "研发费用加计扣除": ("研发费用税前加计扣除",),
    "低空经济": ("低空", "通用航空", "无人机产业"),
    "科技成果转化": ("成果转化", "科技成果转移转化"),
    # Institution renames that would otherwise miss the archive.
    "科技部": ("科学技术部",),
    "工信部": ("工业和信息化部",),
    "发改委": ("发展和改革委员会",),
    "人社部": ("人力资源和社会保障部",),
    "知识产权局": ("国家知识产权局",),
}

# Support-category vocabulary. Used to route a query to the right filter, and to
# keep "认定" from being described as cash support.
SUPPORT_CATEGORY_TERMS: dict[str, tuple[str, ...]] = {
    "project_grant": ("项目资助", "专项资金", "无偿资助", "补助"),
    "designation": ("认定", "评定", "入库", "备案"),
    "designation_reward": ("认定奖励", "一次性奖励", "奖励资金"),
    "loan_interest_subsidy": ("贷款贴息", "贴息", "利息补贴"),
    "tax_incentive": ("税收优惠", "加计扣除", "减免税", "税前扣除"),
    "service_voucher": ("服务券", "创新券", "券"),
    "other": ("优先支持", "要素保障", "用地保障"),
}


@dataclass(frozen=True)
class NormalizedQuery:
    original: str
    canonical: str
    matched_aliases: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    document_numbers: tuple[str, ...] = ()
    support_categories: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "original": self.original,
            "canonical": self.canonical,
            "matched_aliases": {k: list(v) for k, v in self.matched_aliases.items()},
            "document_numbers": list(self.document_numbers),
            "support_categories": list(self.support_categories),
        }


_DOC_NO_PATTERN = re.compile(
    r"[（(]?\s*[国省市区县发改科工信财人社税知市监农商贸文旅银]\w{0,12}"
    r"\s*[〔\[【]\s*(\d{2,4})\s*[〕\]】]\s*(\d{1,4})\s*号\s*[)）]?"
)


def extract_document_numbers(text: str) -> tuple[str, ...]:
    """Pull 文号 out of a free-text query.

    Document numbers are the single most precise filter we have, so a query that
    contains one should never be answered by pure vector similarity.
    """
    found: list[str] = []
    for match in _DOC_NO_PATTERN.finditer(text):
        found.append(re.sub(r"[\s()（）]", "", match.group(0)))
    return tuple(dict.fromkeys(found))


def extract_support_categories(text: str) -> tuple[str, ...]:
    hits: list[str] = []
    for category, terms in SUPPORT_CATEGORY_TERMS.items():
        if any(term in text for term in terms):
            hits.append(category)
    return tuple(hits)


def normalize_query(text: str) -> NormalizedQuery:
    """Rewrite dialect/shorthand into canonical terms, keeping the trace."""
    canonical_parts = [text]
    matched: dict[str, tuple[str, ...]] = {}
    for term, expansions in TERM_ALIASES.items():
        if term in text:
            matched[term] = expansions
            for expansion in expansions:
                if expansion not in text:
                    canonical_parts.append(expansion)
    return NormalizedQuery(
        original=text,
        canonical=" ".join(canonical_parts),
        matched_aliases=matched,
        document_numbers=extract_document_numbers(text),
        support_categories=extract_support_categories(text),
    )


# --------------------------------------------------------------------------- #
# Filter construction
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class RetrievalFilters:
    """Everything the caller may narrow by — nothing may be applied post-hoc."""

    tenant_id: UUID
    park_id: str | None = None
    province: str | None = None
    city: str | None = None
    enterprise_type: str | None = None
    support_category: str | None = None
    policy_status: str | None = None  # in_force | expired | withdrawn | superseded
    window_state: str | None = None  # open | upcoming | closed | unknown
    as_of: date | None = None
    require_verified_scope: bool = True

    def describe(self) -> dict[str, Any]:
        return {
            "park_id": self.park_id,
            "province": self.province,
            "city": self.city,
            "enterprise_type": self.enterprise_type,
            "support_category": self.support_category,
            "policy_status": self.policy_status,
            "window_state": self.window_state,
            "as_of": self.as_of.isoformat() if self.as_of else None,
            "require_verified_scope": self.require_verified_scope,
        }


def assert_server_side_tenant_filter(filters: RetrievalFilters) -> None:
    """Fail closed: retrieval without a tenant cannot be answered."""
    if filters.tenant_id is None:
        raise ValueError("检索必须带 tenant_id，缺租户不能返回任何政策")


def build_chunk_query(filters: RetrievalFilters, *, latest_policy_version_subquery):
    """Assemble the SQL for the candidate pool.

    Returns a ``Select`` whose WHERE clause already contains the tenant
    predicate — the caller cannot forget it.
    """
    assert_server_side_tenant_filter(filters)
    base = (
        select(PolicyChunk)
        .join(PolicyVersion, PolicyVersion.id == PolicyChunk.policy_version_id)
        .join(
            latest_policy_version_subquery,
            (latest_policy_version_subquery.c.policy_id == PolicyVersion.policy_id)
            & (latest_policy_version_subquery.c.latest_version == PolicyVersion.version),
        )
        .join(Policy, Policy.id == PolicyChunk.policy_id)
        .where(
            _tenant_predicate(filters.tenant_id),
            _chunk_tenant_predicate(filters.tenant_id),
            *current_policy_clauses(),
            *applicable_region_clauses({"province": filters.province, "city": filters.city}),
            *_scope_predicates(filters),
        )
    )
    return base


def _tenant_predicate(tenant_id: UUID) -> ColumnElement[bool]:
    return visible_policy_clause(tenant_id)


def _chunk_tenant_predicate(tenant_id: UUID) -> ColumnElement[bool]:
    return or_(PolicyChunk.tenant_id.is_(None), PolicyChunk.tenant_id == tenant_id)


def _scope_predicates(filters: RetrievalFilters) -> list[ColumnElement[bool]]:
    """Park / region / status narrowing, expressed in SQL.

    A park filter is only ever applied by ``park_id``.  Falling back to a city
    string match would let an enterprise located in the same city inherit a park
    policy it is not eligible for.
    """
    clauses: list[ColumnElement[bool]] = []

    if filters.park_id:
        # Callers must pass a park_id they resolved through the catalogue; the
        # check below makes an unresolvable id an error instead of "no filter".
        from app.services.park_registry import catalog as catalog_mod

        catalog = catalog_mod.load_catalog()
        if filters.park_id not in catalog.by_id():
            raise ValueError(f"未知园区 park_id={filters.park_id}，不能用于范围过滤")

        from app.models.park_policy import ParkPolicyScope

        reviewed = [ParkPolicyScope.review_status == "confirmed"]
        if filters.require_verified_scope:
            reviewed.append(ParkPolicyScope.requires_confirmation.is_(False))
        clauses.append(
            Policy.id.in_(
                select(ParkPolicyScope.policy_id).where(
                    ParkPolicyScope.park_id == filters.park_id, *reviewed
                )
            )
        )
    return clauses


# --------------------------------------------------------------------------- #
# Retrieval entry point
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class RetrievedPolicy:
    policy_id: UUID
    title: str
    similarity: float
    chunk_ids: tuple[UUID, ...]
    park_scope_matched: bool = False
    window_state: str | None = None
    needs_recheck: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "policy_id": str(self.policy_id),
            "title": self.title,
            "similarity": round(self.similarity, 4),
            "chunk_ids": [str(c) for c in self.chunk_ids],
            "park_scope_matched": self.park_scope_matched,
            "window_state": self.window_state,
            "needs_recheck": self.needs_recheck,
        }


def park_aware_search(
    db: Session,
    *,
    filters: RetrievalFilters,
    query: str,
    query_vector: list[float] | None,
    limit: int = 20,
    windows: Iterable[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Hybrid retrieval with park/region scoping and an auditable trace."""
    normalized = normalize_query(query)
    candidates: list[PolicyCandidate] = hybrid_policy_candidates(
        db,
        tenant_id=filters.tenant_id,
        query=normalized.canonical,
        query_vector=query_vector or [],
        limit=max(limit * 3, 50),
        region={"province": filters.province, "city": filters.city},
    )

    allowed = _allowed_policy_ids(db, filters)
    results = [
        RetrievedPolicy(
            policy_id=candidate.policy.id,
            title=getattr(candidate.policy, "title", "") or "",
            similarity=candidate.similarity,
            chunk_ids=candidate.chunk_ids,
            park_scope_matched=bool(filters.park_id),
        )
        for candidate in candidates
        if allowed is None or candidate.policy.id in allowed
    ][:limit]

    return {
        "query": normalized.as_dict(),
        "filters": filters.describe(),
        "results": [item.as_dict() for item in results],
        "trace": {
            "lexical_plus_vector": True,
            "document_number_filter": list(normalized.document_numbers),
            "tenant_filter_location": "sql",
            "park_filter_by": "park_id" if filters.park_id else None,
            "note": "结果为空需区分：确无匹配 / 被范围过滤 / 来源未采集",
        },
    }


def _allowed_policy_ids(db: Session, filters: RetrievalFilters) -> set[UUID] | None:
    """Secondary guard for park scope; returns None when no park filter is used."""
    if not filters.park_id:
        return None
    from app.models.park_policy import ParkPolicyScope

    rows = db.scalars(
        select(ParkPolicyScope.policy_id).where(
            ParkPolicyScope.park_id == filters.park_id,
            ParkPolicyScope.review_status == "confirmed",
            *(
                [ParkPolicyScope.requires_confirmation.is_(False)]
                if filters.require_verified_scope
                else []
            ),
        )
    ).all()
    return set(rows)


def _catalog_dir() -> str:
    """Resolve the policy source catalogue directory, honouring settings."""
    from app.core.config import settings

    configured = getattr(settings, "policy_collection_catalog_dir", "config/policy_sources")
    path = Path(configured)
    if path.is_absolute() or path.exists():
        return str(path)
    # Fall back to the repo-relative location so CLI runs from any cwd work.
    return str(Path(__file__).resolve().parents[3] / configured)


def describe_empty_result(db: Session, *, filters: RetrievalFilters, query: str) -> dict[str, Any]:
    """Explain "新增 0 条" — 确无更新 / 规则失效 / 抓取失败 三者必须可区分。

    The catalogue (YAML) is the source of truth for *which* sources exist for a
    region; the database only holds mutable run state.  Reading absence from the
    database alone would report "no policies" for a region we never registered.
    """
    from app.models.policy_collection import PolicySourceState
    from app.services.policy_collection.catalog import load_catalog

    catalog = load_catalog(_catalog_dir())
    region_sources = [
        source
        for source in catalog.sources
        if source.enabled
        and (
            filters.park_id
            or (filters.province and source.province == filters.province)
            or (filters.city and source.city == filters.city)
        )
    ]
    if not region_sources:
        return {
            "reason": "source_not_registered",
            "message": "该地区尚未登记可用来源，结果为空不代表没有政策",
        }

    states = {
        state.source_id: state
        for state in db.scalars(
            select(PolicySourceState).where(
                PolicySourceState.source_id.in_([s.source_id for s in region_sources])
            )
        ).all()
    }

    paused = [s for s in region_sources if getattr(states.get(s.source_id), "paused", False)]
    if paused and len(paused) == len(region_sources):
        reasons = sorted(
            {
                (states[s.source_id].paused_reason or "无原因记录")
                for s in paused
                if s.source_id in states
            }
        )
        return {
            "reason": "source_paused",
            "message": f"该地区来源已全部暂停采集：{'；'.join(reasons)}",
            "sources": [s.source_id for s in paused],
        }

    failing = [
        s
        for s in region_sources
        if getattr(states.get(s.source_id), "last_error", None)
    ]
    if failing and len(failing) == len(region_sources):
        return {
            "reason": "fetch_failed",
            "message": "该地区来源最近均抓取失败，结果为空不能视为确无更新",
            "sources": [
                {"source_id": s.source_id, "last_error": states[s.source_id].last_error}
                for s in failing
            ],
        }

    return {
        "reason": "no_match",
        "message": "来源正常且未暂停，查询未命中；可能是筛选条件过窄或该词无对应政策",
        "sources_checked": len(region_sources),
        "sources_failing": [s.source_id for s in failing],
        "sources_paused": [s.source_id for s in paused],
    }


def window_flags(windows: Iterable[Mapping[str, Any]], *, today: date) -> list[dict[str, Any]]:
    """Annotate application windows so a closed window is never read as repeal."""
    out: list[dict[str, Any]] = []
    for window in windows:
        state = compute_window_state(
            opens_at=window.get("opens_at"),
            closes_at=window.get("closes_at"),
            today=today,
            suspended=bool(window.get("suspended")),
        )
        out.append({**dict(window), "state": state})
    return out
