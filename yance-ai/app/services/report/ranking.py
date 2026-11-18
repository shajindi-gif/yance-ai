"""Deterministic usefulness ranking for POLICY_REPORT opportunities.

Scores are auditable feature maps. Never invent dates, quotes, or eligibility.
usefulness ≈ relevance × actionability × trust — implemented as reweighted
additive features so existing sellable gates stay intact.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any


# Titles that rarely help an SME act on subsidies / applications.
_NOISE_TITLE_TOKENS = (
    "地理标志专用标志",
    "地理标志产品公告",
    "核准使用地理标志",
    "典型案例",
    "建设名单",
    "方案（模板）",
    "职员招聘",
    "招聘公告",
    "博士后招聘",
    "百日招聘",
    "人才服务专项行动",
    "财务决算报表",
    "决算报表",
    "公示名单",
    "入选名单",
    "拟认定名单",
    "实验动物许可",
)

# Soft promotional / planning noise: demote hard; skip when no rules.
_ACTIVITY_OR_PLAN_TOKENS = (
    "宣传月",
    "对接活动",
    "百场万企",
    "全国行",
    "巡回",
    "路演活动",
    "大赛报名",
    "竞赛",
    "规划》",
    "发展规划",
    "五年规划",
    "十五五",
    "十四五",
    "答记者问",
    "新闻发布会",
)

# Soft demotion only (do not hard-skip when rules exist).
_OPINION_TOKENS = (
    "指导意见",
    "若干意见",
    "的意见",
)
_ACTIONABLE_TOKENS = (
    "申报",
    "申请",
    "资助",
    "补贴",
    "奖补",
    "认定",
    "备案",
    "实施细则",
    "管理办法",
    "专项资金",
    "公示（申报",
    "组织申报",
    "开始申报",
    "兑现",
    "征集",
    "项目的通知",
)


@dataclass(frozen=True)
class RankFeatures:
    region_fit: float
    industry_fit: float
    actionability: float
    window_fit: float
    evidence_strength: float
    enterprise_fit: float
    noise_penalty: float
    relevance_base: float
    usefulness: float
    final_score: float
    skip: bool
    skip_reason: str | None
    ranking_note: str | None

    def as_audit(self) -> dict[str, Any]:
        return asdict(self)


def _title_blob(title: str | None, policy_type: str | None) -> str:
    return f"{title or ''} {policy_type or ''}"


def is_hard_noise_title(title: str | None, policy_type: str | None = None) -> bool:
    blob = _title_blob(title, policy_type)
    return any(token in blob for token in _NOISE_TITLE_TOKENS)


def is_activity_or_plan_title(title: str | None, policy_type: str | None = None) -> bool:
    blob = _title_blob(title, policy_type)
    return any(token in blob for token in _ACTIVITY_OR_PLAN_TOKENS)


def actionability_score(title: str | None, policy_type: str | None = None) -> float:
    """Higher = more actionable for application / funding. Range roughly [-20, +14]."""

    blob = _title_blob(title, policy_type)
    score = 0.0
    if any(token in blob for token in _ACTIONABLE_TOKENS):
        score += 14.0
    if any(token in blob for token in ("通知", "公告")) and score >= 14:
        score += 2.0
    if any(token in blob for token in _OPINION_TOKENS) and score < 14:
        score -= 10.0
    if is_activity_or_plan_title(title, policy_type):
        score -= 18.0
    if is_hard_noise_title(title, policy_type):
        score -= 25.0
    return score

def region_fit_score(
    *,
    company_province: str | None,
    company_city: str | None,
    company_district: str | None,
    policy_province: str | None,
    policy_city: str | None,
    policy_district: str | None,
    policy_level: str | None,
) -> tuple[float, bool]:
    """Return (score, out_of_region). Local beats national for local profiles."""

    level = policy_level or ""
    if company_province and policy_province and policy_province != company_province and level != "national":
        return 0.0, True
    if not company_province and policy_province and level != "national":
        # Nationwide / cross-region profiles only keep national or unscoped.
        return 0.0, True

    if company_province and policy_province and company_province == policy_province:
        score = 18.0
        if company_city and policy_city and company_city == policy_city:
            score = 20.0
        if company_district and policy_district and company_district == policy_district:
            score = 22.0
        elif company_city and policy_district and company_city == policy_district:
            score = 22.0
        return score, False

    if level == "national" or (not policy_province and not level):
        # National is applicable but must not outrank same-province items.
        if company_province:
            return 8.0, False
        return 14.0, False
    if not policy_province:
        return 8.0, False
    return 0.0, False


def window_fit_score(
    *,
    deadline: datetime | None,
    expires_at: datetime | None,
    now: datetime | None = None,
) -> float:
    """Use only stored dates; never invent. Missing dates → 0."""

    clock = now or datetime.now(UTC)
    if deadline is not None:
        aware = deadline if deadline.tzinfo else deadline.replace(tzinfo=UTC)
        if aware < clock:
            return -16.0
        days = (aware - clock).days
        if days <= 45:
            return 10.0
        if days <= 120:
            return 6.0
        return 3.0
    if expires_at is not None:
        aware = expires_at if expires_at.tzinfo else expires_at.replace(tzinfo=UTC)
        if aware < clock:
            return -12.0
        return 2.0
    return 0.0


def evidence_strength_score(active_hard_rules: int) -> float:
    if active_hard_rules > 0:
        return 16.0 + min(6.0, float(active_hard_rules - 1) * 2.0)
    return -20.0


def enterprise_fit_score(
    *,
    qualification_component: float,
    industry_component: float,
    active_hard_rules: int,
) -> float:
    """Boost when structured quals/industry already align; no LLM."""

    score = 0.0
    if qualification_component >= 15:
        score += 8.0
    elif qualification_component >= 10:
        score += 4.0
    if industry_component >= 12 and active_hard_rules > 0:
        score += 4.0
    return score


def compute_rank_features(
    *,
    title: str | None,
    policy_type: str | None,
    company_province: str | None,
    company_city: str | None,
    company_district: str | None,
    policy_province: str | None,
    policy_city: str | None,
    policy_district: str | None,
    policy_level: str | None,
    industry_component: float,
    scale_component: float,
    qualification_component: float,
    tech_component: float,
    finance_component: float,
    semantic_component: float,
    active_hard_rules: int,
    deadline: datetime | None,
    expires_at: datetime | None,
    now: datetime | None = None,
) -> RankFeatures:
    region, out_of_region = region_fit_score(
        company_province=company_province,
        company_city=company_city,
        company_district=company_district,
        policy_province=policy_province,
        policy_city=policy_city,
        policy_district=policy_district,
        policy_level=policy_level,
    )
    if out_of_region:
        return RankFeatures(
            region_fit=0,
            industry_fit=industry_component,
            actionability=0,
            window_fit=0,
            evidence_strength=0,
            enterprise_fit=0,
            noise_penalty=0,
            relevance_base=0,
            usefulness=0,
            final_score=0,
            skip=True,
            skip_reason="out_of_region",
            ranking_note="外省硬错配：已移出主列表",
        )

    hard_noise = is_hard_noise_title(title, policy_type)
    activity = is_activity_or_plan_title(title, policy_type)
    # Always drop roster/recruitment/Q&A. Promo/plan: drop when no rules; else keep but demote hard.
    if hard_noise or (activity and active_hard_rules <= 0):
        return RankFeatures(
            region_fit=region,
            industry_fit=industry_component,
            actionability=actionability_score(title, policy_type),
            window_fit=0,
            evidence_strength=evidence_strength_score(active_hard_rules),
            enterprise_fit=0,
            noise_penalty=-40,
            relevance_base=0,
            usefulness=-50,
            final_score=0,
            skip=True,
            skip_reason="hard_noise" if hard_noise else "activity_or_plan_noise",
            ranking_note="噪声/宣传活动类：已移出主列表",
        )
    # Title mentions the company's province → local signal even if metadata province null.
    if company_province and company_province[:2] in (title or ""):
        region = max(region, 17.0)

    action = actionability_score(title, policy_type)
    window = window_fit_score(deadline=deadline, expires_at=expires_at, now=now)
    evidence = evidence_strength_score(active_hard_rules)
    enterprise = enterprise_fit_score(
        qualification_component=qualification_component,
        industry_component=industry_component,
        active_hard_rules=active_hard_rules,
    )
    noise_penalty = 0.0
    if hard_noise:
        noise_penalty -= 18.0
    if activity:
        # Keep in pool when rules exist, but keep out of Top (customer Top gate).
        noise_penalty -= 40.0
    if industry_component == 0 and active_hard_rules <= 0:
        noise_penalty -= 8.0
    if "再生资源" in (title or ""):
        noise_penalty -= 14.0

    # Relevance keeps legacy interpretable components but region is local-first.
    relevance = (
        region
        + industry_component
        + scale_component * 0.6
        + qualification_component * 0.7
        + tech_component * 0.7
        + finance_component * 0.5
        + semantic_component
    )
    usefulness = action + window + evidence + enterprise + noise_penalty
    if region >= 16 and active_hard_rules > 0:
        usefulness += 10.0

    final = max(0.0, min(100.0, relevance + usefulness))
    # Activity/plan with rules may stay in the brief for sellable positives, but
    # must not occupy customer Top slots.
    if activity:
        final = min(final, 22.0)
    note = None
    if active_hard_rules <= 0:
        note = "弱匹配：尚无已审核硬门槛规则，已降权并仅作信息参考"
    elif activity:
        note = "规划/活动类：已降权，优先核对申报类政策"
    elif region >= 16:
        note = "同城/同省可行动机会优先"
    return RankFeatures(
        region_fit=region,
        industry_fit=industry_component,
        actionability=action,
        window_fit=window,
        evidence_strength=evidence,
        enterprise_fit=enterprise,
        noise_penalty=noise_penalty,
        relevance_base=round(relevance, 2),
        usefulness=round(usefulness, 2),
        final_score=round(final, 2),
        skip=False,
        skip_reason=None,
        ranking_note=note,
    )


def sort_key_for_opportunity(evidence: dict[str, Any], score: float) -> tuple:
    """Tie-break: score → rules → window → region → newer publish."""

    payload = evidence or {}
    features = payload.get("rank_features") or {}
    rules = int(payload.get("active_hard_rules") or 0)
    has_window = 1 if payload.get("deadline") else 0
    region = float(features.get("region_fit") or 0)
    # Newer publish sorts earlier when prefixed with empty-last via invert string.
    published = payload.get("published_at") or ""
    return (-float(score or 0), -rules, -has_window, -region, published == "", published)


def enforce_local_diversity(
    ordered: list[Any],
    *,
    company_province: str | None,
    top_n: int = 10,
    min_local: int = 3,
    province_getter,
) -> list[Any]:
    """Ensure Top N includes local items when the corpus has them (stable reorder)."""

    if not company_province or len(ordered) <= 1:
        return ordered
    top = list(ordered[:top_n])
    local_in_top = [item for item in top if province_getter(item) == company_province]
    if len(local_in_top) >= min_local:
        return ordered
    needed = min_local - len(local_in_top)
    locals_below = [
        item
        for item in ordered[top_n:]
        if province_getter(item) == company_province
    ][:needed]
    if not locals_below:
        return ordered
    # Insert local items just after existing local/top actionable slots.
    rebuilt = list(top)
    # Drop weakest non-local from the end of top to make room.
    for local in locals_below:
        for idx in range(len(rebuilt) - 1, -1, -1):
            if province_getter(rebuilt[idx]) != company_province:
                rebuilt.pop(idx)
                break
        rebuilt.append(local)
    rest = [item for item in ordered if item not in rebuilt]
    return rebuilt + rest
