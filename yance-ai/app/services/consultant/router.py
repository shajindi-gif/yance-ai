"""AI Funding Consultant — deterministic intent routing over real engines.

Answers are composed ONLY from stored evidence: opportunities, eligibility
results with criteria, exact-span citations, requirement matrices and profile
facts. When data is missing the answer says INSUFFICIENT EVIDENCE instead of
guessing. No bare-LLM answers by design.
"""

import re
from datetime import UTC
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.models import (
    Application,
    ApplicationRequirement,
    Company,
    CompanyFact,
    CompanyProfile,
    CompanyProfileVersion,
    EligibilityResult,
    Opportunity,
    Policy,
)

INTENT_PATTERNS = (
    ("why_not", ("为什么不能", "为什么不符合", "不能申请", "没资格", "不符合", "不合格")),
    ("missing_materials", ("缺什么", "缺少", "需要什么材料", "材料清单", "还差", "哪些证明", "补什么")),
    ("deadlines", ("截止", "deadline", "还有多久", "时间", "日期", "逾期")),
    ("profile_gaps", ("画像", "完善", "信息不足", "资料不全", "补充信息")),
    ("opportunities", ("能申请", "能报", "有哪些政策", "哪些资金", "机会", "适合", "可以申报", "补贴", "资助")),
)


def classify_intent(question: str) -> str:
    text = question.lower().strip()
    for intent, markers in INTENT_PATTERNS:
        if any(marker in text for marker in markers):
            return intent
    return "search"


def _citation(opportunity: Opportunity, policy: Policy | None) -> dict[str, Any]:
    return {
        "opportunity_id": str(opportunity.id),
        "policy_id": str(opportunity.policy_id) if opportunity.policy_id else None,
        "title": opportunity.title,
        "source_url": policy.source_url if policy else None,
        "issuing_authority": policy.issuing_authority if policy else None,
        "deadline": policy.deadline.isoformat() if policy and policy.deadline else None,
    }


def _funding_label(policy: Policy | None) -> str | None:
    if policy is None:
        return None
    if policy.funding_amount_max is not None:
        if policy.funding_amount_min is not None and policy.funding_amount_min != policy.funding_amount_max:
            return f"{policy.funding_amount_min:g}-{policy.funding_amount_max:g} 万元"
        return f"最高 {policy.funding_amount_max:g} 万元"
    return policy.support_amount


def _opportunity_block(opportunity: Opportunity, policy: Policy | None) -> dict[str, Any]:
    result = {
        "kind": "opportunity",
        "title": opportunity.title,
        "detail": {
            "score": float(opportunity.score) if opportunity.score is not None else None,
            "eligibility": opportunity.eligibility_status,
            "funding": _funding_label(policy),
            "status": opportunity.status,
        },
        "citation": _citation(opportunity, policy),
    }
    return result


def _eligible_opportunities(db: Session, company_id: UUID):
    rows = db.execute(
        select(Opportunity, Policy)
        .outerjoin(Policy, Opportunity.policy_id == Policy.id)
        .where(
            Opportunity.company_id == company_id,
            Opportunity.eligibility_status.in_(["ELIGIBLE", "POTENTIALLY_ELIGIBLE"]),
        )
        .order_by(Opportunity.score.desc().nullslast())
    ).all()
    return rows


def _answer_opportunities(db: Session, company: Company) -> dict[str, Any]:
    rows = _eligible_opportunities(db, company.id)
    if not rows:
        return {
            "intent": "opportunities",
            "insufficient": True,
            "summary": "当前没有可引用的资格结论。可能尚未运行政策扫描，或全部机会被硬性条件排除。",
            "blocks": [],
            "next_actions": ["运行政策机会扫描", "完善企业画像以提高判定覆盖"],
        }
    blocks = [_opportunity_block(opportunity, policy) for opportunity, policy in rows[:8]]
    total_max = sum(
        float(p.funding_amount_max) for _, p in rows if p is not None and p.funding_amount_max is not None
    )
    summary = f"根据已验证的资格结论，贵司当前有 {len(rows)} 个可申请/潜在可申请机会。"
    if total_max:
        summary += f" 已结构化的资助上限合计约 {total_max:g} 万元（仅计入有官方金额条款的机会）。"
    return {
        "intent": "opportunities",
        "insufficient": False,
        "summary": summary,
        "blocks": blocks,
        "next_actions": ["打开高匹配机会查看逐条资格依据", "选择机会创建申报工作区"],
    }


def _answer_why_not(db: Session, company: Company, question: str) -> dict[str, Any]:
    stmt = (
        select(Opportunity, Policy)
        .outerjoin(Policy, Opportunity.policy_id == Policy.id)
        .where(Opportunity.company_id == company.id)
    )
    rows = db.execute(stmt).all()
    named = [(o, p) for o, p in rows if any(tok and tok in o.title for tok in re.split(r"[「\"“”']", question) if len(tok) >= 4)]
    target = named[0] if named else next(((o, p) for o, p in rows if o.eligibility_status == "NOT_ELIGIBLE"), None)
    if target is None:
        return {
            "intent": "why_not",
            "insufficient": True,
            "summary": "没有找到可引用的资格判定记录，无法解释原因。请先运行政策扫描。",
            "blocks": [],
            "next_actions": ["运行政策机会扫描后重试"],
        }
    opportunity, policy = target
    result = db.scalar(select(EligibilityResult).where(EligibilityResult.opportunity_id == opportunity.id))
    blocks: list[dict[str, Any]] = []
    if result is None or not result.criteria_json:
        return {
            "intent": "why_not",
            "insufficient": True,
            "summary": f"「{opportunity.title}」尚无逐条资格判定明细（仅有汇总状态 {opportunity.eligibility_status}）。",
            "blocks": [_opportunity_block(opportunity, policy)],
            "next_actions": ["重新运行该机会的资格评估"],
        }
    for criterion in result.criteria_json:
        if str(criterion.get("result", "")).upper() in {"FAIL", "NOT_MET", "HARD_FAIL"}:
            blocks.append(
                {
                    "kind": "criterion",
                    "title": f"未通过：{criterion.get('requirement') or criterion.get('name')}",
                    "detail": {
                        "company_value": criterion.get("company_value") or criterion.get("actual"),
                        "required": criterion.get("required_value") or criterion.get("expected"),
                        "hard_gate": criterion.get("hard_gate", criterion.get("is_hard_gate")),
                    },
                    "citation": {
                        "quote": criterion.get("source_quote") or criterion.get("evidence"),
                        "article": criterion.get("article"),
                        **(_citation(opportunity, policy)),
                    },
                }
            )
    insufficient = [
        c for c in result.criteria_json if str(c.get("result", "")).upper() in {"INSUFFICIENT", "UNKNOWN", "MISSING_DATA"}
    ]
    summary = f"「{opportunity.title}」资格结论：{result.status}。未通过硬性条件 {len(blocks)} 项，证据不足 {len(insufficient)} 项。"
    return {
        "intent": "why_not",
        "insufficient": not blocks and not insufficient,
        "summary": summary,
        "blocks": blocks[:10],
        "missing_evidence": [c.get("requirement") or c.get("name") for c in insufficient][:10],
        "next_actions": ["补充证据不足项对应的企业事实", "如条件可整改，查看 How to Fix"],
    }


def _answer_missing_materials(db: Session, company: Company) -> dict[str, Any]:
    application = db.scalar(
        select(Application)
        .where(Application.company_id == company.id, Application.status.notin_(["cancelled"]))
        .order_by(Application.created_at.desc())
    )
    if application is None:
        return {
            "intent": "missing_materials",
            "insufficient": True,
            "summary": "贵司还没有创建申报工作区，无法生成材料缺口清单。请先从机会详情创建申报。",
            "blocks": [],
            "next_actions": ["打开我的机会 → 选择目标政策 → 创建申报"],
        }
    requirements = list(
        db.scalars(
            select(ApplicationRequirement)
            .where(
                ApplicationRequirement.application_id == application.id,
                ApplicationRequirement.status.in_(["missing", "collecting"]),
            )
            .order_by(ApplicationRequirement.is_hard_gate.desc())
        ).all()
    )
    blocks = [
        {
            "kind": "requirement",
            "title": r.title,
            "detail": {
                "status": r.status,
                "hard_gate": r.is_hard_gate,
                "category": r.category,
                "application": application.title,
            },
            "citation": {"source": (r.source_json or {}).get("source") if hasattr(r, "source_json") else None},
        }
        for r in requirements
    ]
    if not blocks:
        return {
            "intent": "missing_materials",
            "insufficient": False,
            "summary": f"「{application.title}」的材料矩阵当前没有缺失/收集中的要求项。",
            "blocks": [],
            "next_actions": ["进入申请工作区做一致性检查与评审"],
        }
    return {
        "intent": "missing_materials",
        "insufficient": False,
        "summary": f"「{application.title}」还有 {len(blocks)} 项材料未就绪（硬性 {sum(1 for r in requirements if r.is_hard_gate)} 项）。",
        "blocks": blocks[:12],
        "next_actions": ["上传缺失材料到企业资料库并关联申请", "优先处理硬性门槛项"],
    }


def _answer_deadlines(db: Session, company: Company) -> dict[str, Any]:
    from datetime import datetime

    from app.models.models import Milestone

    now = datetime.now(UTC)
    blocks = []
    applications = list(
        db.scalars(
            select(Application).where(
                Application.company_id == company.id,
                Application.due_at.is_not(None),
                Application.status.notin_(["submitted", "completed", "cancelled"]),
            )
        ).all()
    )
    for application in applications:
        due = application.due_at
        if due.tzinfo is None:
            due = due.replace(tzinfo=UTC)
        days = (due - now).days
        blocks.append(
            {
                "kind": "deadline",
                "title": f"申报「{application.title}」",
                "detail": {"due": due.strftime("%Y-%m-%d"), "days_left": days, "status": application.status},
            }
        )
    milestones = list(
        db.scalars(
            select(Milestone).where(
                Milestone.tenant_id == company.tenant_id,
                Milestone.due_at.is_not(None),
                Milestone.status.notin_(["done"]),
            )
        ).all()
    )
    for milestone in milestones:
        due = milestone.due_at
        if due.tzinfo is None:
            due = due.replace(tzinfo=UTC)
        blocks.append(
            {
                "kind": "deadline",
                "title": f"里程碑「{milestone.title}」",
                "detail": {"due": due.strftime("%Y-%m-%d"), "days_left": (due - now).days, "status": milestone.status},
            }
        )
    blocks.sort(key=lambda b: b["detail"]["days_left"])
    if not blocks:
        return {
            "intent": "deadlines",
            "insufficient": True,
            "summary": "没有设置截止日期的申报或里程碑。机会的政策截止日期可在机会详情查看。",
            "blocks": [],
            "next_actions": ["从机会创建申报时带入官方截止日期", "为申报添加准备里程碑"],
        }
    return {
        "intent": "deadlines",
        "insufficient": False,
        "summary": f"共 {len(blocks)} 个进行中的时间项，最近一个剩 {blocks[0]['detail']['days_left']} 天。",
        "blocks": blocks[:10],
        "next_actions": ["逾期项优先处理", "为 T-7 内的申报生成材料清单"],
    }


def _answer_profile_gaps(db: Session, company: Company) -> dict[str, Any]:
    profile = db.scalar(select(CompanyProfile).where(CompanyProfile.company_id == company.id))
    completeness = profile.completeness_score if profile else 0
    fact_keys: set[str] = set()
    if profile is not None and profile.published_version:
        version = db.scalar(
            select(CompanyProfileVersion).where(
                CompanyProfileVersion.profile_id == profile.id,
                CompanyProfileVersion.version == profile.published_version,
            )
        )
        if version is not None:
            fact_keys = set(
                db.scalars(
                    select(CompanyFact.fact_key).where(CompanyFact.profile_version_id == version.id)
                ).all()
            )
    high_value = ["revenue", "rd_expense", "rd_ratio", "employee_count", "patents", "software_copyrights", "qualifications", "tax_status"]
    missing = [key for key in high_value if key not in fact_keys]
    summary = f"企业画像完成度 {completeness}%。"
    if missing:
        summary += f" 影响资格判定的关键事实仍缺失：{', '.join(missing)}（INSUFFICIENT EVIDENCE，不做猜测）。"
    else:
        summary += " 关键资格事实均已登记。"
    return {
        "intent": "profile_gaps",
        "insufficient": completeness < 40,
        "summary": summary,
        "blocks": [{"kind": "missing_fact", "title": key, "detail": {"why": "资格规则高频引用"}} for key in missing],
        "next_actions": ["上传审计报告/社保人数证明自动抽取", "在企业主页补充研发费用与营收"],
    }


def _answer_search(db: Session, company: Company, question: str) -> dict[str, Any]:
    tokens = [t for t in re.split(r"[\s,，。？?、]+", question) if len(t) >= 2][:5]
    stmt = (
        select(Opportunity, Policy)
        .outerjoin(Policy, Opportunity.policy_id == Policy.id)
        .where(Opportunity.company_id == company.id)
    )
    rows = db.execute(stmt).all()
    matched = [
        (o, p)
        for o, p in rows
        if any(tok in o.title or (p is not None and tok in (p.content or "")) for tok in tokens)
    ]
    if not matched:
        return {
            "intent": "search",
            "insufficient": True,
            "summary": "在贵司已扫描的机会与已收录政策证据内没有命中该问题。为避免无依据回答，不生成结论。",
            "blocks": [],
            "next_actions": ["换个说法或运行新的政策扫描", "询问：能申请哪些资金 / 缺什么材料 / 截止日期"],
        }
    return {
        "intent": "search",
        "insufficient": False,
        "summary": f"命中 {len(matched)} 个相关机会，全部结论可回溯到官方条款。",
        "blocks": [_opportunity_block(o, p) for o, p in matched[:6]],
        "next_actions": ["打开机会查看逐条资格与证据"],
    }


def answer(db: Session, *, company: Company, question: str) -> dict[str, Any]:
    intent = classify_intent(question)
    if intent == "opportunities":
        return _answer_opportunities(db, company)
    if intent == "why_not":
        return _answer_why_not(db, company, question)
    if intent == "missing_materials":
        return _answer_missing_materials(db, company)
    if intent == "deadlines":
        return _answer_deadlines(db, company)
    if intent == "profile_gaps":
        return _answer_profile_gaps(db, company)
    return _answer_search(db, company, question)
