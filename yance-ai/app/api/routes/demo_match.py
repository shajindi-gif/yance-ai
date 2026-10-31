"""创业大赛演示：政策匹配报告 + 演示支付闭环 + 埋点 + 多模型"""

import asyncio
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import Principal, require_roles
from app.core.config import settings
from app.core.db import get_db
from app.models.models import (
    AnalyticsEvent,
    Company,
    Deliverable,
    Entitlement,
    Invoice,
    Opportunity,
    Order,
    Payment,
    Policy,
    Product,
    UserRole,
)
from app.services.commerce.availability import purchase_status
from app.services.llm.base import LLMRequest
from app.services.llm.router import LLMRouter
from app.services.report.matcher import match_policies_for_company
from app.services.report.snapshot import report_bytes

router = APIRouter(tags=["demo-match"])

_llm = LLMRouter()

# ── 可用模型列表 ─────────────────────────────────────────────
AVAILABLE_MODELS = {
    "qwen": {"name": "通义千问 Qwen", "model_id": "qwen-plus"},
    "deepseek": {"name": "DeepSeek V3", "model_id": "deepseek-chat"},
    "openai": {"name": "OpenAI GPT-4o", "model_id": "gpt-4o-mini"},
}


# ── 埋点工具 ────────────────────────────────────────────────
def track_event(
    db: Session,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID | None,
    name: str,
    properties: dict | None = None,
):
    """记录分析事件到 analytics_events 表"""
    event = AnalyticsEvent(
        tenant_id=tenant_id,
        user_id=user_id,
        name=name,
        properties=properties or {},
    )
    db.add(event)
    db.commit()


# ── 请求/响应模型 ────────────────────────────────────────────
class MatchRequest(BaseModel):
    company_id: uuid.UUID
    provider: str = "qwen"


class MatchResponse(BaseModel):
    company_name: str
    total_matches: int
    preview: list[dict]
    full: list[dict]
    ai_summary: str = ""
    provider_used: str = ""


# ── 报告生成（含多模型 AI 摘要）──────────────────────────────
@router.post("/reports/match", response_model=MatchResponse)
async def generate_match_report(
    req: MatchRequest,
    principal: Principal = Depends(require_roles(UserRole.owner, UserRole.admin, UserRole.member)),
    db: Session = Depends(get_db),
):
    company = db.scalar(
        select(Company).where(
            Company.id == req.company_id, Company.tenant_id == principal.tenant_id
        )
    )
    if not company:
        raise HTTPException(status_code=404, detail="企业不存在")

    opportunities = await match_policies_for_company(db, company, principal.tenant_id)

    policy_ids = [o.policy_id for o in opportunities]
    policies = db.scalars(select(Policy).where(Policy.id.in_(policy_ids))).all()
    policy_map = {p.id: p for p in policies}

    def opp_to_dict(opp: Opportunity) -> dict:
        policy = policy_map.get(opp.policy_id)
        evidence = opp.evidence_json or {}
        return {
            "opportunity_id": str(opp.id),
            "policy_id": str(opp.policy_id),
            "policy_title": policy.title if policy else "",
            "jurisdiction": policy.jurisdiction if policy else "",
            "level": policy.level if policy else "",
            "province": policy.province if policy else "",
            "support_amount": policy.support_amount if policy else "",
            "support_type": policy.support_type if policy else "",
            "deadline": policy.deadline.isoformat() if policy and policy.deadline else None,
            "issuing_authority": policy.issuing_authority if policy else "",
            "score": round(opp.score, 3),
            "score_pct": round(opp.score * 100),
            "missing_materials": evidence.get("missing_materials", []),
            "evidence_json": evidence,
        }

    full_list = [opp_to_dict(o) for o in opportunities]
    preview_list = full_list[:2]

    # ── 多模型 AI 摘要（15秒超时保护）──
    ai_summary = ""
    provider_used = ""
    provider_key = req.provider if req.provider in AVAILABLE_MODELS else "qwen"
    model_info = AVAILABLE_MODELS[provider_key]

    try:
        top_titles = "、".join(p.title for p in policies[:5])
        prompt = (
            f"你是衍策引擎AI政策顾问。{company.name}（{company.industry or '科技'}行业，"
            f"位于{company.province or '上海'}{company.city or ''}）"
            f"匹配到{len(opportunities)}项政策，包括：{top_titles}。"
            f"用2-3句话给出核心建议，包括优先申报顺序和最关键的准备事项。"
        )
        response = await asyncio.wait_for(
            _llm.complete(
                LLMRequest(
                    messages=[{"role": "user", "content": prompt}],
                    model=model_info["model_id"],
                    temperature=0.3,
                    max_tokens=300,
                ),
                provider=provider_key,
            ),
            timeout=15,
        )
        ai_summary = response.content
        provider_used = f"{model_info['name']} ({response.model})"
    except Exception:
        ai_summary = "建议优先关注匹配度最高的政策，提前准备缺失材料。"
        provider_used = f"{model_info['name']} (fallback)"

    # ── 埋点 ──
    track_event(
        db,
        principal.tenant_id,
        principal.user.id,
        "report_generated",
        {
            "company_id": str(company.id),
            "total_matches": len(opportunities),
            "provider": provider_key,
            "max_score": max((o.score for o in opportunities), default=0),
        },
    )

    return MatchResponse(
        company_name=company.name,
        total_matches=len(opportunities),
        preview=preview_list,
        full=full_list,
        ai_summary=ai_summary,
        provider_used=provider_used,
    )


# ── PDF 下载 ──────────────────────────────────────────────────
@router.get("/reports/{company_id}/download")
async def download_match_report_pdf(
    company_id: uuid.UUID,
    order_id: uuid.UUID | None = None,
    principal: Principal = Depends(require_roles(UserRole.owner, UserRole.admin, UserRole.member)),
    db: Session = Depends(get_db),
):
    company = db.scalar(
        select(Company).where(Company.id == company_id, Company.tenant_id == principal.tenant_id)
    )
    if not company:
        raise HTTPException(status_code=404, detail="企业不存在")

    # 检查 Entitlement（已购买的报告可以无限次下载）
    entitlement = db.scalar(
        select(Entitlement).where(
            Entitlement.tenant_id == principal.tenant_id,
            Entitlement.resource_type == "report",
            Entitlement.resource_id == company_id,
            Entitlement.status == "active",
        )
    )
    if not entitlement:
        raise HTTPException(status_code=403, detail="请先购买该企业的报告")

    # Bind download to the purchased version, including tenant/resource checks on every join.
    deliverable = db.scalar(
        select(Deliverable).join(Order, Order.report_deliverable_id == Deliverable.id)
        .join(Entitlement, Entitlement.order_id == Order.id)
        .where(
            Entitlement.tenant_id == principal.tenant_id,
            Entitlement.resource_type == "report", Entitlement.resource_id == company_id,
            Entitlement.status == "active", Order.tenant_id == principal.tenant_id,
            Order.resource_type == "report", Order.resource_id == company_id,
            Order.id == order_id if order_id else Order.id.is_not(None),
            Order.status == "paid", Deliverable.tenant_id == principal.tenant_id,
            Deliverable.company_id == company_id,
        ).order_by(Order.created_at.desc())
    )
    if deliverable is None:
        raise HTTPException(409, "原订单未绑定固定报告版本，请联系支持核对原交付；权益保留，请勿重复付款")
    pdf_bytes = report_bytes(deliverable)

    track_event(
        db,
        principal.tenant_id,
        principal.user.id,
        "report_downloaded",
        {
            "company_id": str(company.id),
        },
    )

    from urllib.parse import quote

    filename = f"{deliverable.title}_v{deliverable.version}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}",
                 "Cache-Control": "private, no-store"},
    )


# ── 产品目录（统一定价）────────────────────────────────────────
@router.get("/products")
async def get_products(db: Session = Depends(get_db)):
    """获取所有活跃产品 SKU（前端定价页从此获取价格）"""
    products = db.scalars(
        select(Product).where(Product.active.is_(True)).order_by(Product.sort_order)
    ).all()
    return [
        {
            "id": str(p.id),
            "code": p.code,
            "name": p.name,
            "description": p.description,
            "product_type": p.product_type,
            "price": float(p.price),
            "original_price": float(p.original_price) if p.original_price else None,
            "promotional_price": float(p.promotional_price) if p.promotional_price is not None else None,
            "entitlement_type": p.entitlement_type,
            **purchase_status(p),
        }
        for p in products
    ]


# ── 演示支付（使用 Product 价格 + 创建 Entitlement）────────────
class DemoPayRequest(BaseModel):
    product_code: str  # POLICY_REPORT, POLICY_DIAGNOSIS, APPLICATION_PLAN
    company_id: uuid.UUID | None = None  # for report: which company
    opportunity_id: uuid.UUID | None = None  # for diagnosis: which opportunity


@router.post("/payments/demo-pay")
async def demo_payment(
    req: DemoPayRequest,
    principal: Principal = Depends(require_roles(UserRole.owner, UserRole.admin, UserRole.member)),
    db: Session = Depends(get_db),
):
    if settings.app_env == "production" or not settings.demo_features_enabled:
        raise HTTPException(status_code=404, detail="Not found")

    # 从 Product 表获取真实价格
    product = db.scalar(
        select(Product).where(Product.code == req.product_code, Product.active.is_(True))
    )
    if not product:
        raise HTTPException(status_code=404, detail=f"产品不存在: {req.product_code}")

    resource_id = req.company_id if product.entitlement_type == "report" else req.opportunity_id
    resource_model = Company if product.entitlement_type == "report" else Opportunity
    if not resource_id or not db.scalar(
        select(resource_model.id).where(
            resource_model.id == resource_id,
            resource_model.tenant_id == principal.tenant_id,
        )
    ):
        raise HTTPException(status_code=404, detail="产品关联资源不存在")

    # 使用 Product 价格
    amount = float(product.promotional_price or product.price)

    order = Order(
        tenant_id=principal.tenant_id,
        order_no=f"Y{secrets.token_hex(8).upper()}",
        product_code=req.product_code,
        amount=amount,
        currency="CNY",
        resource_type=product.entitlement_type,
        resource_id=resource_id,
        status="created",
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    order.status = "paid"

    payment = Payment(
        tenant_id=principal.tenant_id,
        order_id=order.id,
        provider="demo",
        provider_trade_no=f"DEMO_{order.order_no}",
        amount=amount,
        currency="CNY",
        status="completed",
    )
    db.add(payment)

    # 创建 Entitlement（解锁交付物）
    entitlement = Entitlement(
        tenant_id=principal.tenant_id,
        user_id=principal.user.id,
        product_id=product.id,
        order_id=order.id,
        resource_type=product.entitlement_type,
        resource_id=resource_id,
        status="active",
    )
    db.add(entitlement)

    invoice = Invoice(
        tenant_id=principal.tenant_id,
        order_id=order.id,
        invoice_no=f"INV_{order.order_no}",
        title="个人",
        tax_number="",
        invoice_type="vat_normal",
        amount=amount,
        tax_amount=0,
        total_amount=amount,
        status="generated",
    )
    db.add(invoice)
    db.commit()
    db.refresh(invoice)

    track_event(
        db,
        principal.tenant_id,
        principal.user.id,
        "demo_payment_completed",
        {
            "order_no": order.order_no,
            "amount": amount,
            "product_code": req.product_code,
            "product_name": product.name,
        },
    )

    return {
        "order_id": str(order.id),
        "order_no": order.order_no,
        "payment_status": "paid",
        "invoice_id": str(invoice.id),
        "invoice_no": invoice.invoice_no,
        "product_name": product.name,
        "amount": amount,
        "message": f"演示支付成功，{product.name}已解锁",
    }


# ── 查询当前租户的 Entitlement ────────────────────────────────
@router.get("/entitlements")
async def get_entitlements(
    principal: Principal = Depends(require_roles(UserRole.owner, UserRole.admin, UserRole.member)),
    db: Session = Depends(get_db),
):
    """获取当前租户已购买的所有产品授权"""
    entitlements = db.scalars(
        select(Entitlement)
        .join(Product)
        .where(Entitlement.tenant_id == principal.tenant_id, Entitlement.status == "active")
        .order_by(Entitlement.created_at.desc())
    ).all()
    result = []
    for e in entitlements:
        product = db.scalar(select(Product).where(Product.id == e.product_id))
        result.append(
            {
                "id": str(e.id),
                "order_id": str(e.order_id),
                "product_code": product.code if product else "",
                "product_name": product.name if product else "",
                "resource_type": e.resource_type,
                "resource_id": str(e.resource_id) if e.resource_id else None,
                "status": e.status,
                "created_at": e.created_at.isoformat(),
            }
        )
    return result


# ── 分析统计（数据飞轮可视化）────────────────────────────────
@router.get("/analytics/stats")
async def get_analytics_stats(
    principal: Principal = Depends(require_roles(UserRole.owner, UserRole.admin)),
    db: Session = Depends(get_db),
):
    seven_days_ago = datetime.now(UTC) - timedelta(days=7)
    events = db.scalars(
        select(AnalyticsEvent).where(
            AnalyticsEvent.tenant_id == principal.tenant_id,
            AnalyticsEvent.occurred_at >= seven_days_ago,
        )
    ).all()

    counts: dict[str, int] = {}
    provider_counts: dict[str, int] = {}
    for e in events:
        counts[e.name] = counts.get(e.name, 0) + 1
        if e.name == "report_generated" and e.properties.get("provider"):
            p = e.properties["provider"]
            provider_counts[p] = provider_counts.get(p, 0) + 1

    return {
        "period": "7d",
        "total_events": len(events),
        "searches": counts.get("policy_search", 0),
        "reports_generated": counts.get("report_generated", 0),
        "payments": counts.get("payment_completed", 0),
        "downloads": counts.get("report_downloaded", 0),
        "provider_usage": provider_counts,
        "available_models": {k: v["name"] for k, v in AVAILABLE_MODELS.items()},
    }
