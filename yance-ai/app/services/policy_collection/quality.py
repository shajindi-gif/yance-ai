"""Policy quality rubric — 信度 / 效度 / 有效性 (reliability, validity, utility).

Why a rubric instead of a single "score"
---------------------------------------
A policy document can be perfectly authentic and still be useless to a customer
(it was repealed last year), or genuinely in force and impossible to verify (no
official snapshot was stored).  Collapsing those two failures into one number
hides *which* failure happened, and a customer cannot act on a number they cannot
interrogate.  So every document is judged on three independent axes, each built
from named sub-signals:

* **Reliability 信度** — can we prove this text is what the issuing authority
  actually published?  Source authority (official domain + issuing level),
  stored original snapshot, body completeness, metadata completeness, text
  cleanliness.
* **Validity 效度** — is the document actually in force, and does it apply to the
  region it claims?  Validity status (repealed / repealed-adjacent), time window,
  region self-consistency, version recency, topic relevance.
* **Utility 有效性/可用性** — can a customer do anything with it?  Actionable
  elements (eligibility, materials, process, contact), structured funding facts,
  application window, retrieval chunk quality, traceable URL.

Nothing here calls an LLM.  Every sub-signal is a deterministic regex, length
bucket or metadata lookup, so the same document always scores the same and any
verdict can be re-derived by hand from the stored text.  That property is what
makes the rubric auditable; an opaque model score could not be defended to a
customer who disputes a deletion from the deliverable set.

Hard vetoes
-----------
Some findings are not "a few points off".  A repealed policy, an expired policy,
a 200-character stub, a region that contradicts its own level, or a version that
has been superseded must never reach a customer, whatever the weighted score
says.  Those set ``deliverable = False`` and force grade ``D``, and each one is
reported as an explicit issue code rather than being folded into the score.

Grades and delivery tiers
-------------------------
========================  ========================  ==================================
Grade                     Total score               Delivery tier
========================  ========================  ==================================
A                         >= 85                     ``deliverable`` — quote freely
B                         70 – 84.9                 ``deliverable_with_note`` — quote,
                                                    carry the caveat list
C                         55 – 69.9                 ``internal_only`` — not shown to
                                                    customers, kept for review
D                         < 55 or hard veto         ``withheld`` — archived only
========================  ========================  ==================================

Thresholds live in :data:`GRADE_THRESHOLDS` so a future rubric revision can move
them without touching the scoring code.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Any, Iterable, Sequence

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

RUBRIC_VERSION = "quality-rubric-v1.1"

# Keep in lockstep with ``service.PUBLISH_MIN_CHARS``: the structural gate refuses to
# publish a body shorter than this, and the rubric must not call such a row deliverable.
_MIN_DOCUMENT_CHARS = 300

#: (grade, minimum total score), highest first.
GRADE_THRESHOLDS: tuple[tuple[str, float], ...] = (("A", 85.0), ("B", 70.0), ("C", 55.0))

#: Axis weights — reliability carries the most because a customer's first question
#: is "is this really what the ministry said", not "is it nicely written".
AXIS_WEIGHTS: dict[str, float] = {"reliability": 0.40, "validity": 0.35, "utility": 0.25}

DELIVERY_TIERS: dict[str, str] = {
    "A": "deliverable",
    "B": "deliverable_with_note",
    "C": "internal_only",
    "D": "withheld",
}

#: How long a document with no stated expiry stays "fresh" for validity purposes.
FRESH_YEARS = 3
AGING_YEARS = 5

_AUTHORITY_SCORE = {"A": 100.0, "B": 88.0, "C": 65.0, "D": 35.0}

_DOC_NUMBER_RE = re.compile(
    r"〔\s*\d{4}\s*〕\s*\d{1,4}\s*号|\[\s*\d{4}\s*\]\s*\d{1,4}\s*号|\(\s*\d{4}\s*\)\s*\d{1,4}\s*号"
)
_EFFECTIVE_RE = re.compile(
    r"自\s*(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日\s*起\s*(?:施行|实施|执行|试行|生效)"
)
_EXPIRY_RE = re.compile(
    r"有效期(?:限)?\s*(?:至|到|为)?\s*(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日"
)
_EXPIRY_YEARS_RE = re.compile(r"有效期(?:限)?\s*(?:为)?\s*([1-9])\s*年")
_STRONG_ABOLISH_RE = re.compile(r"予以废止|自行废止|宣布失效|即行废止|停止执行|一律废止")
_WEAK_ABOLISH_RE = re.compile(r"废止|失效")
_TITLE_ABOLISH_TOKENS = ("废止", "失效", "停止执行")

#: Announcement genres that live on the same portals as policy but are not policy text
#: (a list of 326 approved companies, a recruitment notice, a tender result).  They pass
#: every structural check — real page, real issuer, real date — so only the genre tells
#: them apart, and a customer receiving them as "policy" is being sold inventory.
_NON_POLICY_GENRE_TOKENS = (
    "名单", "公示", "招聘", "中标", "成交", "采购", "机构简介", "工作动态",
    "新闻发布会", "拟支持", "拟认定", "征询", "征求意见",
)
#: A title containing one of these is a normative document even if it also carries a
#: genre word (e.g. "关于印发《X办法》的通知（公示）").
_POLICY_FORM_RE = re.compile(r"办法|规定|条例|细则|决定|实施方案|若干措施|若干政策|规划|行动计划|指引|标准")

_ALWAYS_ACCEPT_RE = re.compile(r"常年受理|常年申报|长期有效|长期受理|滚动申报")

_HTML_TAG_RE = re.compile(r"<[a-zA-Z/!][^>]{0,120}>")
_NAV_TOKENS = (
    "首页",
    "上一页",
    "下一页",
    "打印本页",
    "字号",
    "分享到",
    "当前位置",
    "无障碍",
    "网站地图",
    "扫一扫",
    "关闭窗口",
    "版权所有",
)

#: Labels are customer-facing: they end up in the caveat list shown next to a quote.
_ACTIONABLE_TERMS: dict[str, str] = {
    "适用对象/申报条件": r"申报条件|申请条件|支持对象|申报对象|适用范围|适用对象|申报主体",
    "支持标准": r"支持标准|补助标准|奖励标准|资助额度|补贴标准|支持额度|最高不超过",
    "申报材料": r"申报材料|申请材料|申报资料|需提交|提交材料",
    "办理流程": r"申报流程|办理流程|申请流程|审核流程|工作流程|申报程序",
    "受理时间": r"申报时间|受理时间|截止时间|申报期限|受理期限|申报截止|报送时间",
    "联系方式": r"联系方式|联系电话|咨询电话|受理单位|联系单位|咨询方式",
}

_TOPIC_TERMS = (
    "科技",
    "研发",
    "创新",
    "专精特新",
    "人才",
    "资金",
    "补助",
    "奖励",
    "税收",
    "知识产权",
    "成果转化",
    "高企",
    "高新技术企业",
    "孵化器",
    "技术改造",
    "数字化",
    "平台",
    "申报",
)


@dataclass(slots=True)
class DocumentFacts:
    """Everything the rubric is allowed to look at, collected in one query."""

    policy_id: str
    version_id: str
    title: str
    content: str
    issuer: str | None = None
    level: str | None = None
    province: str | None = None
    city: str | None = None
    district: str | None = None
    jurisdiction: str | None = None
    source_url: str | None = None
    source_name: str | None = None
    publish_date: date | None = None
    effective_date: date | None = None
    expiry_date: date | None = None
    deadline: date | None = None
    support_amount: str | None = None
    support_type: str | None = None
    funding_amount_max: float | None = None
    evidence_snapshots: int = 0
    evidence_urls: int = 0
    chunk_count: int = 0
    avg_chunk_chars: float = 0.0
    is_latest_version: bool = True
    duplicate_group_size: int = 1


@dataclass(slots=True)
class Assessment:
    policy_id: str
    version_id: str
    rubric_version: str
    reliability: float
    validity: float
    utility: float
    total: float
    grade: str
    delivery_tier: str
    deliverable: bool
    timeline_state: str
    source_tier: str
    verdict: str
    issues: list[dict[str, str]] = field(default_factory=list)
    signals: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "version_id": self.version_id,
            "rubric_version": self.rubric_version,
            "reliability": round(self.reliability, 2),
            "validity": round(self.validity, 2),
            "utility": round(self.utility, 2),
            "total": round(self.total, 2),
            "grade": self.grade,
            "delivery_tier": self.delivery_tier,
            "deliverable": self.deliverable,
            "timeline_state": self.timeline_state,
            "source_tier": self.source_tier,
            "verdict": self.verdict,
            "issues": self.issues,
            "signals": self.signals,
        }


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _issue(code: str, message: str, severity: str = "warn", axis: str = "validity") -> dict[str, str]:
    return {"code": code, "message": message, "severity": severity, "axis": axis}


def _bucket(value: float, steps: Sequence[tuple[float, float]], default: float = 0.0) -> float:
    """First (threshold, score) whose threshold ``value`` reaches, else ``default``."""
    for threshold, score in steps:
        if value >= threshold:
            return score
    return default


def _parse_date(text_value: str | None) -> date | None:
    if not text_value:
        return None
    try:
        return datetime.fromisoformat(str(text_value).replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _domain(url: str | None) -> str:
    if not url:
        return ""
    match = re.match(r"https?://([^/:\s]+)", url.strip(), flags=re.IGNORECASE)
    return match.group(1).lower() if match else ""


def _text_date(year: str, month: str, day: str) -> date | None:
    try:
        return date(int(year), int(month), int(day))
    except ValueError:
        return None


# --------------------------------------------------------------------------- #
# sub-signal extraction
# --------------------------------------------------------------------------- #
def source_tier(level: str | None, domain: str, issuer: str | None) -> tuple[str, str]:
    """Classify provenance authority.

    National/provincial documents on a ``gov.cn`` host with an issuing authority
    are tier A; municipal/district official pages are tier B; a ``gov.cn`` page
    that is clearly a reprint of another body's document is tier C; anything else
    (aggregator, commercial repost) is tier D.
    """
    issuer_text = (issuer or "").strip()
    is_gov = domain.endswith("gov.cn")
    if not domain:
        return "D", "no source url"
    if not is_gov:
        return "D", f"non-official host {domain}"
    if not issuer_text:
        return "C", "official host but no issuing authority recorded"
    if level in {"national", "provincial"}:
        return "A", f"{level} document on {domain}"
    if level in {"municipal", "district"}:
        return "B", f"{level} document on {domain}"
    if level:
        return "B", f"level={level} on {domain}"
    return "C", "official host, level unknown"


def _region_consistency(facts: DocumentFacts) -> tuple[bool | None, str]:
    """True when level and the administrative names do not contradict each other."""
    level = (facts.level or "").strip()
    province = (facts.province or "").strip()
    city = (facts.city or "").strip()
    district = (facts.district or "").strip()
    if not level:
        return None, "level missing"
    if level == "national":
        return (province in {"", "全国", "国家"}), "national document"
    if level == "provincial":
        return (bool(province), "provincial document without province")
    if level == "municipal":
        return (bool(city), "municipal document without city")
    if level == "district":
        return (bool(district), "district document without district")
    return None, f"unknown level {level}"


def _timeline_state(
    facts: DocumentFacts, today: date, abolished_strength: str
) -> tuple[str, str]:
    if abolished_strength == "strong":
        return "abolished", "text states the document is repealed or void"
    if facts.expiry_date and facts.expiry_date < today:
        return "expired", f"expired {facts.expiry_date.isoformat()}"
    if facts.effective_date and facts.effective_date > today:
        return "upcoming", f"takes effect {facts.effective_date.isoformat()}"
    if not facts.expiry_date and not facts.effective_date:
        return "unknown", "no effective/expiry date in the document body"
    return "effective", "within its stated validity window"


def _cleanliness(content: str) -> tuple[float, int, int]:
    tag_chars = sum(len(m.group(0)) for m in _HTML_TAG_RE.finditer(content))
    nav_hits = sum(content.count(token) for token in _NAV_TOKENS)
    replacement = content.count("\ufffd") + content.count("锟斤拷")
    penalty = min(100.0, tag_chars * 0.5 + nav_hits * 6.0 + replacement * 10.0)
    return max(0.0, 100.0 - penalty), nav_hits, tag_chars


# --------------------------------------------------------------------------- #
# the rubric
# --------------------------------------------------------------------------- #
def evaluate(facts: DocumentFacts, *, today: date | None = None) -> Assessment:
    """Score one document. Pure function: same input, same output, forever."""
    today = today or datetime.now(UTC).date()
    content = facts.content or ""
    title = (facts.title or "").strip()
    issues: list[dict[str, str]] = []

    # ---- provenance / authority ------------------------------------------ #
    domain = _domain(facts.source_url)
    tier, tier_reason = source_tier(facts.level, domain, facts.issuer)

    # ---- reliability ------------------------------------------------------ #
    authority = _AUTHORITY_SCORE[tier]
    evidence = 100.0 if facts.evidence_snapshots > 0 else (60.0 if facts.evidence_urls > 0 else 0.0)
    if facts.evidence_snapshots == 0:
        issues.append(_issue("no_original_snapshot", "未留存原始页面快照，无法回溯官方原文", "warn", "reliability"))

    content_chars = len(content.strip())
    completeness = _bucket(
        content_chars,
        ((3000, 100.0), (1500, 85.0), (800, 65.0), (300, 40.0)),
        default=10.0,
    )
    if content_chars < 800:
        issues.append(_issue("short_body", f"正文仅 {content_chars} 字，可能为列表页或摘要页", "warn", "reliability"))
    # A body this short is not a document, it is a headline or a navigation page.
    # Scoring only would let it land in B (a link-rich summary page scores well on
    # authority and metadata), so the length is a *veto*, kept identical to the
    # structural gate in ``service.promote_ready_documents`` — the two gates must not
    # disagree about what counts as a document.
    if content_chars < _MIN_DOCUMENT_CHARS:
        issues.append(
            _issue(
                "text_incomplete",
                f"有效正文仅 {content_chars} 字（低于 {_MIN_DOCUMENT_CHARS} 字），不足以构成可交付文件",
                "blocker",
                "reliability",
            )
        )

    meta_hits = sum(
        1
        for present in (
            bool(title),
            bool((facts.issuer or "").strip()),
            facts.publish_date is not None,
            bool(facts.level),
            bool(facts.source_url),
            bool(_DOC_NUMBER_RE.search(content[:2000])),
        )
        if present
    )
    metadata = meta_hits / 6.0 * 100.0
    if meta_hits < 6:
        issues.append(
            _issue("metadata_incomplete", f"元数据完整度 {meta_hits}/6（标题/机关/发布日期/层级/来源/文号）", "info", "reliability")
        )

    cleanliness, nav_hits, tag_chars = _cleanliness(content)
    if cleanliness < 80:
        issues.append(_issue("text_noise", f"正文含导航词 {nav_hits} 处、HTML 残留 {tag_chars} 字符", "info", "reliability"))

    reliability = (
        authority * 0.35
        + evidence * 0.25
        + completeness * 0.18
        + metadata * 0.12
        + cleanliness * 0.10
    )

    # ---- validity --------------------------------------------------------- #
    head = content[:600]
    abolished_strength = "none"
    if any(token in title for token in _TITLE_ABOLISH_TOKENS):
        abolished_strength = "strong"
    elif _STRONG_ABOLISH_RE.search(head):
        abolished_strength = "strong"
    elif _WEAK_ABOLISH_RE.search(f"{title}{head}"):
        abolished_strength = "weak"

    body_effective = _EFFECTIVE_RE.search(content)
    body_expiry = _EXPIRY_RE.search(content)
    effective_date = facts.effective_date or (
        _text_date(*body_effective.groups()) if body_effective else None
    )
    expiry_date = facts.expiry_date or (
        _text_date(*body_expiry.groups()) if body_expiry else None
    )
    if expiry_date is None:
        years = _EXPIRY_YEARS_RE.search(content)
        if years and effective_date:
            try:
                expiry_date = date(effective_date.year + int(years.group(1)), effective_date.month, effective_date.day)
            except ValueError:
                expiry_date = None

    # The helper only needs the two resolved dates, so hand it a minimal fact set
    # rather than mutating the caller's facts.
    timeline_state, timeline_reason = _timeline_state(
        DocumentFacts(
            policy_id=facts.policy_id,
            version_id=facts.version_id,
            title=title,
            content=content,
            effective_date=effective_date,
            expiry_date=expiry_date,
        ),
        today,
        abolished_strength,
    )

    if abolished_strength == "strong":
        status_score = 0.0
        issues.append(_issue("policy_abolished", "正文/标题显示该文件已废止或失效", "blocker", "validity"))
    elif abolished_strength == "weak":
        status_score = 50.0
        issues.append(_issue("abolish_mention", "正文提及废止/失效，需人工确认是废止旧规还是本文件被废止", "warn", "validity"))
    else:
        status_score = 100.0

    publish = facts.publish_date
    if timeline_state == "expired":
        time_score = 0.0
        issues.append(_issue("policy_expired", f"有效期已于 {expiry_date.isoformat()} 结束", "blocker", "validity"))
    elif timeline_state == "upcoming":
        time_score = 85.0
        issues.append(_issue("not_yet_effective", "尚未生效，可作为政策储备，不可作为现行依据", "warn", "validity"))
    elif expiry_date:
        time_score = 100.0
    elif publish:
        age_years = (today - publish).days / 365.25
        if age_years <= FRESH_YEARS:
            time_score = 92.0
        elif age_years <= AGING_YEARS:
            time_score = 70.0
            issues.append(_issue("aging_no_expiry", f"发布已 {age_years:.1f} 年且未标注有效期，需确认是否仍有效", "warn", "validity"))
        else:
            time_score = 45.0
            issues.append(_issue("stale_no_expiry", f"发布已 {age_years:.1f} 年且未标注有效期", "warn", "validity"))
    else:
        time_score = 55.0
        issues.append(_issue("publish_date_missing", "缺少发布日期，无法判断时效", "warn", "validity"))

    region_ok, region_reason = _region_consistency(facts)
    if region_ok is True:
        region_score = 100.0
    elif region_ok is None:
        region_score = 45.0
        issues.append(_issue("region_unknown", f"适用范围不明确（{region_reason}）", "warn", "validity"))
    else:
        region_score = 0.0
        issues.append(_issue("region_conflict", f"层级与行政区划不一致（{region_reason}）", "blocker", "validity"))

    version_score = 100.0 if facts.is_latest_version else 40.0
    if not facts.is_latest_version:
        issues.append(_issue("superseded_version", "该版本已被同政策的更新版本取代", "blocker", "validity"))

    topic_hits = sum(1 for term in _TOPIC_TERMS if term in f"{title}{content[:4000]}")
    topic_relevance = min(1.0, topic_hits / 6.0)
    if topic_relevance < 0.34:
        issues.append(_issue("off_topic", "主题命中度低，可能不属于科技创新/产业扶持口径", "info", "validity"))

    # Genre check: a clean, well-sourced page can still be an announcement rather than
    # a policy.  Deliberately a score deduction, not a veto — the customer may still want
    # the list, they just must not receive it labelled as a document to apply.
    genre_penalty = 0.0
    genre_hits = [token for token in _NON_POLICY_GENRE_TOKENS if token in title]
    if genre_hits and not _POLICY_FORM_RE.search(title):
        genre_penalty = 15.0
        issues.append(
            _issue("non_policy_genre", f"标题含「{genre_hits[0]}」，属公告/名单类而非政策文本", "warn", "validity")
        )

    validity = max(
        0.0,
        (
            status_score * 0.32
            + time_score * 0.28
            + region_score * 0.18
            + version_score * 0.12
            + topic_relevance * 100.0 * 0.10
        )
        - genre_penalty,
    )

    # ---- utility ---------------------------------------------------------- #
    actionability_hits = [label for label, pattern in _ACTIONABLE_TERMS.items() if re.search(pattern, content)]
    actionable = _bucket(
        float(len(actionability_hits)),
        ((4, 100.0), (3, 80.0), (2, 65.0), (1, 45.0)),
        default=20.0,
    )
    if len(actionability_hits) < 2:
        issues.append(_issue("thin_actionability", "可执行要素较少（申报条件/材料/流程/时限/联系方式）", "info", "utility"))

    if facts.funding_amount_max is not None or (facts.support_amount or "").strip():
        funding = 100.0
    elif (facts.support_type or "").strip():
        funding = 70.0
    else:
        funding = 40.0

    if facts.deadline:
        if facts.deadline >= today:
            window = 100.0
        else:
            window = 20.0
            issues.append(_issue("window_closed", f"申报截止 {facts.deadline.isoformat()} 已过", "warn", "utility"))
    elif _ALWAYS_ACCEPT_RE.search(content):
        window = 90.0
    else:
        window = 55.0

    if facts.chunk_count <= 0:
        retrieval = 0.0
        issues.append(_issue("no_chunks", "无可检索段落，无法支撑引用", "blocker", "utility"))
    elif 150 <= facts.avg_chunk_chars <= 1500:
        retrieval = 100.0
    elif 100 <= facts.avg_chunk_chars < 150 or 1500 < facts.avg_chunk_chars <= 3000:
        retrieval = 70.0
    else:
        retrieval = 45.0

    if not facts.source_url:
        traceability = 0.0
        issues.append(_issue("no_source_url", "缺少官方来源链接", "blocker", "utility"))
    elif tier in {"A", "B"}:
        traceability = 100.0 if (facts.source_url or "").startswith("https://") else 85.0
    else:
        traceability = 55.0

    utility = (
        actionable * 0.30
        + funding * 0.22
        + window * 0.20
        + retrieval * 0.16
        + traceability * 0.12
    )

    # ---- total, veto, grade ----------------------------------------------- #
    total = (
        reliability * AXIS_WEIGHTS["reliability"]
        + validity * AXIS_WEIGHTS["validity"]
        + utility * AXIS_WEIGHTS["utility"]
    )

    blockers = [issue for issue in issues if issue["severity"] == "blocker"]
    grade = "D"
    if not blockers:
        for label, threshold in GRADE_THRESHOLDS:
            if total >= threshold:
                grade = label
                break

    deliverable = grade in {"A", "B"}
    warn_notes = [issue["message"] for issue in issues if issue["severity"] == "warn"]
    if blockers:
        verdict = "；".join(issue["message"] for issue in blockers)
    elif grade == "B":
        verdict = "可对外引用，需同时标注：" + "；".join(warn_notes) if warn_notes else "可对外引用"
    elif grade == "A":
        verdict = "通过信度/效度/有效性三重校验，可直接对外引用"
    else:
        verdict = "综合分不足交付线，仅内部留档：" + "；".join(warn_notes)

    return Assessment(
        policy_id=facts.policy_id,
        version_id=facts.version_id,
        rubric_version=RUBRIC_VERSION,
        reliability=reliability,
        validity=validity,
        utility=utility,
        total=total,
        grade=grade,
        delivery_tier=DELIVERY_TIERS[grade],
        deliverable=deliverable,
        timeline_state=timeline_state,
        source_tier=tier,
        verdict=verdict[:400],
        issues=issues,
        signals={
            "source_tier_reason": tier_reason,
            "domain": domain,
            "content_chars": content_chars,
            "chunk_count": facts.chunk_count,
            "avg_chunk_chars": round(facts.avg_chunk_chars, 1),
            "evidence_snapshots": facts.evidence_snapshots,
            "meta_fields_present": meta_hits,
            "abolished_signal": abolished_strength,
            "effective_date": effective_date.isoformat() if effective_date else None,
            "expiry_date": expiry_date.isoformat() if expiry_date else None,
            "deadline": facts.deadline.isoformat() if facts.deadline else None,
            "publish_date": publish.isoformat() if publish else None,
            "timeline_reason": timeline_reason,
            "actionability_hits": actionability_hits,
            "topic_relevance": round(topic_relevance, 3),
            "cleanliness": round(cleanliness, 1),
            "is_latest_version": facts.is_latest_version,
            "duplicate_group_size": facts.duplicate_group_size,
        },
    )


# --------------------------------------------------------------------------- #
# DB binding
# --------------------------------------------------------------------------- #
_FACTS_SQL = """
SELECT
    p.id::text                                   AS policy_id,
    v.id::text                                   AS version_id,
    v.title                                      AS title,
    v.content                                    AS content,
    COALESCE(p.issuing_authority, v.issuer)      AS issuer,
    p.level                                      AS level,
    p.province                                   AS province,
    p.city                                       AS city,
    p.district                                   AS district,
    p.jurisdiction                               AS jurisdiction,
    COALESCE(v.source_url, p.source_url)         AS source_url,
    v.source_name                                AS source_name,
    COALESCE(v.publish_date, p.published_at)     AS publish_date,
    COALESCE(v.effective_date, p.effective_at)   AS effective_date,
    COALESCE(v.expiry_date, p.expires_at)        AS expiry_date,
    COALESCE(v.application_deadline, p.deadline) AS deadline,
    p.support_amount                             AS support_amount,
    p.support_type                               AS support_type,
    p.funding_amount_max                         AS funding_amount_max,
    (SELECT count(*) FROM policy_raw_evidence e
      WHERE e.policy_version_id = v.id
        AND e.purpose = 'document'
        AND e.storage_path IS NOT NULL)          AS evidence_snapshots,
    (SELECT count(*) FROM policy_raw_evidence e
      WHERE e.policy_version_id = v.id)          AS evidence_urls,
    (SELECT count(*) FROM policy_chunks c
      WHERE c.policy_version_id = v.id)          AS chunk_count,
    (SELECT COALESCE(avg(length(c.content)), 0) FROM policy_chunks c
      WHERE c.policy_version_id = v.id)          AS avg_chunk_chars,
    (v.version = (SELECT max(v2.version) FROM policy_versions v2
                   WHERE v2.policy_id = p.id))   AS is_latest_version
FROM policy_versions v
JOIN policies p ON p.id = v.policy_id
-- Two casts on the same placeholder, both to uuid[]: PostgreSQL refuses to plan a
-- bare "placeholder IS NULL OR id = ANY(CAST(placeholder AS uuid[]))" because the
-- uncast reference gives it nothing to infer from (AmbiguousParameter).  Naming the
-- type in both places keeps inference working and lets None mean "no filter".
WHERE (CAST(:version_ids AS uuid[]) IS NULL OR v.id = ANY(CAST(:version_ids AS uuid[])))
  AND (CAST(:policy_ids AS uuid[]) IS NULL OR p.id = ANY(CAST(:policy_ids AS uuid[])))
  AND (CAST(:only_latest AS boolean) IS false OR v.version = (SELECT max(v3.version) FROM policy_versions v3 WHERE v3.policy_id = p.id))
  AND (CAST(:only_tenant_null AS boolean) IS false OR p.tenant_id IS NULL)
ORDER BY COALESCE(v.publish_date, p.published_at) DESC NULLS LAST, v.id
LIMIT :row_limit
"""


def _facts_from_row(row: Any) -> DocumentFacts:
    return DocumentFacts(
        policy_id=row.policy_id,
        version_id=row.version_id,
        title=row.title or "",
        content=row.content or "",
        issuer=row.issuer,
        level=row.level,
        province=row.province,
        city=row.city,
        district=row.district,
        jurisdiction=row.jurisdiction,
        source_url=row.source_url,
        source_name=row.source_name,
        publish_date=_parse_date(row.publish_date),
        effective_date=_parse_date(row.effective_date),
        expiry_date=_parse_date(row.expiry_date),
        deadline=_parse_date(row.deadline),
        support_amount=row.support_amount,
        support_type=row.support_type,
        funding_amount_max=float(row.funding_amount_max) if row.funding_amount_max is not None else None,
        evidence_snapshots=int(row.evidence_snapshots or 0),
        evidence_urls=int(row.evidence_urls or 0),
        chunk_count=int(row.chunk_count or 0),
        avg_chunk_chars=float(row.avg_chunk_chars or 0),
        is_latest_version=bool(row.is_latest_version),
    )


_UPSERT_SQL = """
INSERT INTO policy_quality_assessments (
    id, policy_id, policy_version_id, rubric_version,
    reliability, validity, utility, total, grade, delivery_tier, deliverable,
    timeline_state, source_tier, verdict, issues, signals, assessed_at,
    created_at, updated_at
) VALUES (
    gen_random_uuid(), CAST(:policy_id AS uuid), CAST(:version_id AS uuid), :rubric_version,
    :reliability, :validity, :utility, :total, :grade, :delivery_tier, :deliverable,
    :timeline_state, :source_tier, :verdict,
    CAST(:issues AS jsonb), CAST(:signals AS jsonb), now(), now(), now()
)
ON CONFLICT (policy_version_id, rubric_version) DO UPDATE SET
    reliability = EXCLUDED.reliability,
    validity = EXCLUDED.validity,
    utility = EXCLUDED.utility,
    total = EXCLUDED.total,
    grade = EXCLUDED.grade,
    delivery_tier = EXCLUDED.delivery_tier,
    deliverable = EXCLUDED.deliverable,
    timeline_state = EXCLUDED.timeline_state,
    source_tier = EXCLUDED.source_tier,
    verdict = EXCLUDED.verdict,
    issues = EXCLUDED.issues,
    signals = EXCLUDED.signals,
    assessed_at = now(),
    updated_at = now()
"""

_UPDATE_POLICY_SQL = """
UPDATE policies SET
    quality_score = :total,
    quality_grade = :grade,
    quality_deliverable = :deliverable,
    quality_assessed_at = now(),
    updated_at = now()
WHERE id = CAST(:policy_id AS uuid)
"""


def assess_versions(
    db: Session,
    *,
    version_ids: Iterable[str] | None = None,
    policy_ids: Iterable[str] | None = None,
    only_latest: bool = True,
    only_public: bool = True,
    row_limit: int = 5000,
    persist: bool = True,
    today: date | None = None,
) -> list[Assessment]:
    """Assess and (by default) persist. Returns every assessment, in input order."""
    params = {
        "version_ids": [str(v) for v in version_ids] if version_ids else None,
        "policy_ids": [str(p) for p in policy_ids] if policy_ids else None,
        "only_latest": bool(only_latest),
        "only_tenant_null": bool(only_public),
        "row_limit": int(row_limit),
    }
    rows = db.execute(text(_FACTS_SQL), params).all()
    assessments: list[Assessment] = []
    for row in rows:
        assessment = evaluate(_facts_from_row(row), today=today)
        assessments.append(assessment)
        if persist:
            db.execute(
                text(_UPSERT_SQL),
                {
                    "policy_id": assessment.policy_id,
                    "version_id": assessment.version_id,
                    "rubric_version": assessment.rubric_version,
                    "reliability": round(assessment.reliability, 2),
                    "validity": round(assessment.validity, 2),
                    "utility": round(assessment.utility, 2),
                    "total": round(assessment.total, 2),
                    "grade": assessment.grade,
                    "delivery_tier": assessment.delivery_tier,
                    "deliverable": assessment.deliverable,
                    "timeline_state": assessment.timeline_state,
                    "source_tier": assessment.source_tier,
                    "verdict": assessment.verdict,
                    "issues": json.dumps(assessment.issues, ensure_ascii=False),
                    "signals": json.dumps(assessment.signals, ensure_ascii=False),
                },
            )
            if assessment.signals.get("is_latest_version"):
                db.execute(
                    text(_UPDATE_POLICY_SQL),
                    {
                        "policy_id": assessment.policy_id,
                        "total": round(assessment.total, 2),
                        "grade": assessment.grade,
                        "deliverable": assessment.deliverable,
                    },
                )
    if persist:
        db.commit()
    return assessments


def summary(db: Session, *, rubric_version: str = RUBRIC_VERSION) -> dict[str, Any]:
    """Distribution a customer can read without reading code."""
    grade_rows = db.execute(
        text(
            "SELECT grade, count(*) AS cnt, round(avg(total),1) AS avg_total "
            "FROM policy_quality_assessments WHERE rubric_version = :v GROUP BY grade ORDER BY grade"
        ),
        {"v": rubric_version},
    ).all()
    tier_rows = db.execute(
        text(
            "SELECT delivery_tier, count(*) AS cnt FROM policy_quality_assessments "
            "WHERE rubric_version = :v GROUP BY delivery_tier"
        ),
        {"v": rubric_version},
    ).all()
    timeline_rows = db.execute(
        text(
            "SELECT timeline_state, count(*) AS cnt FROM policy_quality_assessments "
            "WHERE rubric_version = :v GROUP BY timeline_state ORDER BY cnt DESC"
        ),
        {"v": rubric_version},
    ).all()
    source_rows = db.execute(
        text(
            "SELECT source_tier, count(*) AS cnt FROM policy_quality_assessments "
            "WHERE rubric_version = :v GROUP BY source_tier ORDER BY source_tier"
        ),
        {"v": rubric_version},
    ).all()
    axis = db.execute(
        text(
            "SELECT round(avg(reliability),1) AS r, round(avg(validity),1) AS v, "
            "round(avg(utility),1) AS u, count(*) AS n, "
            "sum(CASE WHEN deliverable THEN 1 ELSE 0 END) AS deliverable "
            "FROM policy_quality_assessments WHERE rubric_version = :v"
        ),
        {"v": rubric_version},
    ).one()
    reason_rows = db.execute(
        text(
            "SELECT issue->>'code' AS code, count(*) AS cnt FROM ("
            "  SELECT jsonb_array_elements(CAST(issues AS jsonb)) AS issue "
            "  FROM policy_quality_assessments WHERE rubric_version = :v"
            ") s GROUP BY 1 ORDER BY cnt DESC LIMIT 12"
        ),
        {"v": rubric_version},
    ).all()
    return {
        "rubric_version": rubric_version,
        "assessed": int(axis.n or 0),
        "deliverable": int(axis.deliverable or 0),
        "avg_reliability": float(axis.r or 0),
        "avg_validity": float(axis.v or 0),
        "avg_utility": float(axis.u or 0),
        "by_grade": [{"grade": r.grade, "count": int(r.cnt), "avg_total": float(r.avg_total or 0)} for r in grade_rows],
        "by_delivery_tier": [{"tier": r.delivery_tier, "count": int(r.cnt)} for r in tier_rows],
        "by_timeline_state": [{"state": r.timeline_state, "count": int(r.cnt)} for r in timeline_rows],
        "by_source_tier": [{"tier": r.source_tier, "count": int(r.cnt)} for r in source_rows],
        "top_issue_codes": [{"code": r.code, "count": int(r.cnt)} for r in reason_rows],
    }


# --------------------------------------------------------------------------- #
# Customer-facing export
# --------------------------------------------------------------------------- #
_EXPORT_SQL = """
SELECT p.title, p.issuing_authority, p.level, p.province, p.city, p.district,
       v.publish_date, p.effective_at, p.expires_at, v.application_deadline, p.source_url,
       q.grade, q.total, q.reliability, q.validity, q.utility,
       q.timeline_state, q.source_tier, q.verdict, q.issues
FROM policy_quality_assessments q
JOIN policies p ON p.id = q.policy_id
JOIN policy_versions v ON v.id = q.policy_version_id
WHERE q.rubric_version = :rv
  AND q.deliverable IS TRUE
ORDER BY q.total DESC, v.publish_date DESC NULLS LAST
"""

_EXPORT_HEADER = [
    "政策标题", "发布机关", "层级", "省", "市", "区县",
    "发布日期", "生效日期", "失效日期", "申报截止", "来源链接",
    "等级", "综合分", "信度分", "效度分", "实用分",
    "时效状态", "来源层级", "评估结论", "待关注项",
]


def export_deliverable_csv(db, path: str, rubric_version: str | None = None) -> int:
    """Write the deliverable subset of the corpus to a CSV the customer can open.

    Only ``deliverable = True`` rows are exported: the whole point of the rubric is
    that the customer's spreadsheet and the API's filter agree, so the export must
    never contain a document the API would withhold.  Returns the row count.
    """
    import csv
    import os

    version = rubric_version or RUBRIC_VERSION
    rows = db.execute(text(_EXPORT_SQL), {"rv": version}).all()
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.writer(fh)
        writer.writerow(_EXPORT_HEADER)
        for r in rows:
            issue_codes = [str(item.get("code", "")) for item in (r.issues or [])]
            writer.writerow([
                r.title, r.issuing_authority, r.level, r.province or "", r.city or "",
                r.district or "", r.publish_date, r.effective_at, r.expires_at,
                r.application_deadline, r.source_url, r.grade, float(r.total),
                float(r.reliability), float(r.validity), float(r.utility),
                r.timeline_state, r.source_tier, r.verdict or "", "；".join(issue_codes),
            ])
    return len(rows)
