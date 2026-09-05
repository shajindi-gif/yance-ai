from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import Principal, require_platform_admin
from app.core.db import get_db
from app.models.models import (
    AgentRun,
    AgentRunError,
    AnalyticsEvent,
    Company,
    Document,
    Feedback,
    Order,
    Policy,
    Tenant,
    User,
    WorkflowRun,
)
from app.schemas.schemas import FeedbackStatusUpdate, TenantAccountStageUpdate
from app.services.admin.metrics import admin_overview, investor_metrics, system_health

router = APIRouter(prefix="/admin", tags=["admin"])

AdminResource = Literal[
    "users",
    "organizations",
    "companies",
    "agent_runs",
    "workflow_runs",
    "llm_usage",
    "costs",
    "documents",
    "policies",
    "evals",
    "errors",
    "billing",
    "feedback",
    "analytics",
]


def _page(db: Session, query, *, limit: int, offset: int, serializer) -> dict:
    total = int(db.scalar(select(func.count()).select_from(query.order_by(None).subquery())) or 0)
    rows = db.scalars(query.limit(limit).offset(offset)).all()
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [serializer(row) for row in rows],
    }


def _run_out(item: AgentRun) -> dict:
    return {
        "id": str(item.id),
        "tenant_id": str(item.tenant_id),
        "agent_name": item.agent_name,
        "status": item.status,
        "provider": item.provider,
        "model": item.model,
        "total_tokens": item.total_tokens,
        "cost_usd": float(item.cost_usd or 0),
        "latency_ms": item.latency_ms,
        "error_code": item.error_code,
        "created_at": item.created_at,
    }


@router.get("/overview")
def get_admin_overview(
    _: Principal = Depends(require_platform_admin),
    db: Session = Depends(get_db),
) -> dict:
    return admin_overview(db)


@router.get("/investor-metrics")
def get_investor_metrics(
    _: Principal = Depends(require_platform_admin),
    db: Session = Depends(get_db),
) -> dict:
    return investor_metrics(db)


@router.get("/system-health")
def get_system_health(
    _: Principal = Depends(require_platform_admin),
    db: Session = Depends(get_db),
) -> dict:
    return system_health(db)


@router.get("/resources/{resource}")
def list_admin_resources(
    resource: AdminResource,
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _: Principal = Depends(require_platform_admin),
    db: Session = Depends(get_db),
) -> dict:
    if resource == "evals":
        return {
            "total": 0,
            "limit": limit,
            "offset": offset,
            "items": [],
            "available": False,
            "message": "No evaluation data yet.",
        }
    if resource == "users":
        return _page(
            db,
            select(User).order_by(User.created_at.desc()),
            limit=limit,
            offset=offset,
            serializer=lambda item: {
                "id": str(item.id),
                "tenant_id": str(item.tenant_id),
                "email": item.email,
                "full_name": item.full_name,
                "role": item.role.value,
                "is_active": item.is_active,
                "is_platform_admin": item.is_platform_admin,
                "created_at": item.created_at,
            },
        )
    if resource == "organizations":
        return _page(
            db,
            select(Tenant).order_by(Tenant.created_at.desc()),
            limit=limit,
            offset=offset,
            serializer=lambda item: {
                "id": str(item.id),
                "name": item.name,
                "slug": item.slug,
                "account_stage": item.account_stage,
                "is_active": item.is_active,
                "created_at": item.created_at,
            },
        )
    if resource == "companies":
        return _page(
            db,
            select(Company).order_by(Company.created_at.desc()),
            limit=limit,
            offset=offset,
            serializer=lambda item: {
                "id": str(item.id),
                "tenant_id": str(item.tenant_id),
                "name": item.name,
                "industry": item.industry,
                "province": item.province,
                "created_at": item.created_at,
            },
        )
    if resource in {"agent_runs", "llm_usage", "costs"}:
        query = select(AgentRun)
        if resource in {"llm_usage", "costs"}:
            query = query.where(or_(AgentRun.total_tokens > 0, AgentRun.cost_usd > 0))
        return _page(
            db,
            query.order_by(AgentRun.created_at.desc()),
            limit=limit,
            offset=offset,
            serializer=_run_out,
        )
    if resource == "workflow_runs":
        return _page(
            db,
            select(WorkflowRun).order_by(WorkflowRun.created_at.desc()),
            limit=limit,
            offset=offset,
            serializer=lambda item: {
                "id": str(item.id),
                "tenant_id": str(item.tenant_id),
                "status": item.status,
                "current_step": item.current_step,
                "cost_usd": float(item.cost_usd or 0),
                "latency_ms": item.latency_ms,
                "error_code": item.error_code,
                "created_at": item.created_at,
            },
        )
    if resource == "documents":
        return _page(
            db,
            select(Document).order_by(Document.created_at.desc()),
            limit=limit,
            offset=offset,
            serializer=lambda item: {
                "id": str(item.id),
                "tenant_id": str(item.tenant_id),
                "company_id": str(item.company_id) if item.company_id else None,
                "filename": item.filename,
                "content_type": item.content_type,
                "size_bytes": item.size_bytes,
                "status": item.status,
                "ingestion_status": item.ingestion_status,
                "created_at": item.created_at,
            },
        )
    if resource == "policies":
        return _page(
            db,
            select(Policy).order_by(Policy.created_at.desc()),
            limit=limit,
            offset=offset,
            serializer=lambda item: {
                "id": str(item.id),
                "tenant_id": str(item.tenant_id) if item.tenant_id else None,
                "title": item.title,
                "issuing_authority": item.issuing_authority,
                "jurisdiction": item.jurisdiction,
                "status": item.status,
                "created_at": item.created_at,
            },
        )
    if resource == "errors":
        return _page(
            db,
            select(AgentRunError).order_by(AgentRunError.occurred_at.desc()),
            limit=limit,
            offset=offset,
            serializer=lambda item: {
                "id": str(item.id),
                "tenant_id": str(item.tenant_id),
                "agent_run_id": str(item.agent_run_id),
                "code": item.code,
                "category": item.category,
                "safe_message": item.safe_message,
                "retryable": item.retryable,
                "occurred_at": item.occurred_at,
            },
        )
    if resource == "billing":
        return _page(
            db,
            select(Order).order_by(Order.created_at.desc()),
            limit=limit,
            offset=offset,
            serializer=lambda item: {
                "id": str(item.id),
                "tenant_id": str(item.tenant_id),
                "order_no": item.order_no,
                "product_code": item.product_code,
                "amount": float(item.amount),
                "currency": item.currency,
                "status": item.status,
                "created_at": item.created_at,
            },
        )
    if resource == "feedback":
        return _page(
            db,
            select(Feedback).order_by(Feedback.created_at.desc()),
            limit=limit,
            offset=offset,
            serializer=lambda item: {
                "id": str(item.id),
                "tenant_id": str(item.tenant_id),
                "user_id": str(item.user_id) if item.user_id else None,
                "category": item.category,
                "message": item.message,
                "route": item.route,
                "status": item.status,
                "created_at": item.created_at,
            },
        )
    if resource == "analytics":
        return _page(
            db,
            select(AnalyticsEvent).order_by(AnalyticsEvent.occurred_at.desc()),
            limit=limit,
            offset=offset,
            serializer=lambda item: {
                "id": str(item.id),
                "tenant_id": str(item.tenant_id),
                "user_id": str(item.user_id) if item.user_id else None,
                "name": item.name,
                "source": item.source,
                "event_key": item.event_key,
                "request_id": item.request_id,
                "occurred_at": item.occurred_at,
            },
        )
    raise HTTPException(status_code=404, detail="Admin resource not found")


@router.patch("/organizations/{tenant_id}")
def update_tenant_account_stage(
    tenant_id: UUID,
    payload: TenantAccountStageUpdate,
    _: Principal = Depends(require_platform_admin),
    db: Session = Depends(get_db),
) -> dict:
    tenant = db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Organization not found")
    tenant.account_stage = payload.account_stage
    db.commit()
    return {"id": str(tenant.id), "account_stage": tenant.account_stage}


@router.patch("/feedback/{feedback_id}")
def update_feedback_status(
    feedback_id: UUID,
    payload: FeedbackStatusUpdate,
    _: Principal = Depends(require_platform_admin),
    db: Session = Depends(get_db),
) -> dict:
    feedback = db.get(Feedback, feedback_id)
    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")
    feedback.status = payload.status
    db.commit()
    return {"id": str(feedback.id), "status": feedback.status}
