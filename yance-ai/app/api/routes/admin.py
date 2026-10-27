import re
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
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
    DocumentIngestionRun,
    EvalRun,
    FeatureFlag,
    Feedback,
    Invoice,
    Membership,
    Notification,
    Order,
    Policy,
    Tenant,
    TenantFeatureFlag,
    User,
    WorkflowRun,
    now_utc,
)
from app.schemas.schemas import FeedbackStatusUpdate, TenantAccountStageUpdate
from app.services.admin.metrics import admin_overview, investor_metrics, system_health
from app.services.enterprise.audit import record_audit

router = APIRouter(prefix="/admin", tags=["admin"])


class FeatureFlagUpsert(BaseModel):
    description: str = Field(min_length=3, max_length=500)
    enabled_by_default: bool = False
    status: Literal["active", "archived"] = "active"


class TenantFeatureFlagUpdate(BaseModel):
    enabled: bool
    reason: str = Field(min_length=3, max_length=500)


def _validate_flag_key(key: str) -> str:
    if not re.fullmatch(r"[a-z][a-z0-9_]{2,119}", key):
        raise HTTPException(
            status_code=422,
            detail="Feature flag keys must use lowercase snake_case.",
        )
    return key


def _flag_out(flag: FeatureFlag) -> dict:
    return {
        "id": str(flag.id),
        "key": flag.key,
        "description": flag.description,
        "enabled_by_default": flag.enabled_by_default,
        "status": flag.status,
        "created_at": flag.created_at,
        "updated_at": flag.updated_at,
    }

AdminResource = Literal[
    "users",
    "organizations",
    "companies",
    "agent_runs",
    "workflow_runs",
    "llm_usage",
    "costs",
    "documents",
    "document_ingestion_runs",
    "policies",
    "evals",
    "errors",
    "billing",
    "invoices",
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
                "is_demo": item.is_demo,
                "demo_dataset_key": item.demo_dataset_key,
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
    if resource == "evals":
        page = _page(
            db,
            select(EvalRun).order_by(EvalRun.created_at.desc()),
            limit=limit,
            offset=offset,
            serializer=lambda item: {
                "id": str(item.id),
                "batch_id": str(item.batch_id),
                "eval_type": item.eval_type,
                "status": item.status,
                "target_key": item.target_key,
                "target_version": item.target_version,
                "scorer_version": item.scorer_version,
                "requested_cases": item.requested_cases,
                "passed_cases": item.passed_cases,
                "error_cases": item.error_cases,
                "release_gate_passed": item.release_gate_passed,
                "is_demo": item.is_demo,
                "created_at": item.created_at,
            },
        )
        if not page["items"]:
            page.update(available=False, message="No evaluation data yet.")
        return page
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
    if resource == "document_ingestion_runs":
        return _page(
            db,
            select(DocumentIngestionRun).order_by(DocumentIngestionRun.created_at.desc()),
            limit=limit,
            offset=offset,
            serializer=lambda item: {
                "id": str(item.id),
                "tenant_id": str(item.tenant_id),
                "document_id": str(item.document_id),
                "attempt": item.attempt,
                "status": item.status,
                "parser_version": item.parser_version,
                "error_code": item.error_code,
                "safe_message": item.safe_message,
                "metrics": item.metrics_json,
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
    if resource == "invoices":
        return _page(
            db,
            select(Invoice).order_by(Invoice.created_at.desc()),
            limit=limit,
            offset=offset,
            serializer=lambda item: {
                "id": str(item.id),
                "tenant_id": str(item.tenant_id),
                "invoice_no": item.invoice_no,
                "title": item.title,
                "tax_number": item.tax_number,
                "total_amount": float(item.total_amount),
                "invoice_type": item.invoice_type,
                "status": item.status,
                "voucher_filename": item.voucher_filename,
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
    feedback = db.scalar(select(Feedback).where(Feedback.id == feedback_id).with_for_update())
    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")
    previous = feedback.status
    feedback.status = payload.status
    if previous != payload.status:
        from app.services.enterprise.audit import record_audit
        record_audit(db, tenant_id=feedback.tenant_id, actor_user_id=_.user.id,
                     action="feedback.status_changed", resource_type="feedback", resource_id=str(feedback.id),
                     details={"previous_status": previous, "status": payload.status})
    db.commit()
    return {"id": str(feedback.id), "status": feedback.status}


@router.get("/feature-flags")
def list_feature_flags(
    _: Principal = Depends(require_platform_admin),
    db: Session = Depends(get_db),
) -> dict:
    flags = db.scalars(select(FeatureFlag).order_by(FeatureFlag.key)).all()
    overrides = db.execute(
        select(TenantFeatureFlag, FeatureFlag.key)
        .join(FeatureFlag, FeatureFlag.id == TenantFeatureFlag.feature_flag_id)
        .order_by(FeatureFlag.key, TenantFeatureFlag.tenant_id)
    ).all()
    return {
        "items": [_flag_out(flag) for flag in flags],
        "tenant_overrides": [
            {
                "id": str(override.id),
                "tenant_id": str(override.tenant_id),
                "key": key,
                "enabled": override.enabled,
                "updated_at": override.updated_at,
            }
            for override, key in overrides
        ],
    }


@router.put("/feature-flags/{key}")
def upsert_feature_flag(
    key: str,
    payload: FeatureFlagUpsert,
    principal: Principal = Depends(require_platform_admin),
    db: Session = Depends(get_db),
) -> dict:
    key = _validate_flag_key(key)
    flag = db.scalar(select(FeatureFlag).where(FeatureFlag.key == key).with_for_update())
    if flag is None:
        flag = FeatureFlag(key=key, **payload.model_dump())
        db.add(flag)
        db.flush()
    else:
        flag.description = payload.description
        flag.enabled_by_default = payload.enabled_by_default
        flag.status = payload.status
    record_audit(
        db,
        tenant_id=principal.tenant_id,
        actor_user_id=principal.user.id,
        action="feature_flag.configured",
        resource_type="feature_flag",
        resource_id=str(flag.id),
        details={
            "key": flag.key,
            "enabled_by_default": flag.enabled_by_default,
            "status": flag.status,
        },
    )
    db.commit()
    return _flag_out(flag)


@router.put("/feature-flags/{key}/tenants/{tenant_id}")
def set_tenant_feature_flag(
    key: str,
    tenant_id: UUID,
    payload: TenantFeatureFlagUpdate,
    principal: Principal = Depends(require_platform_admin),
    db: Session = Depends(get_db),
) -> dict:
    key = _validate_flag_key(key)
    tenant = db.get(Tenant, tenant_id)
    flag = db.scalar(select(FeatureFlag).where(FeatureFlag.key == key))
    if tenant is None or flag is None:
        raise HTTPException(status_code=404, detail="Organization or feature flag not found")
    override = db.scalar(
        select(TenantFeatureFlag)
        .where(
            TenantFeatureFlag.tenant_id == tenant_id,
            TenantFeatureFlag.feature_flag_id == flag.id,
        )
        .with_for_update()
    )
    if override is None:
        override = TenantFeatureFlag(
            tenant_id=tenant_id,
            feature_flag_id=flag.id,
            enabled=payload.enabled,
        )
        db.add(override)
        db.flush()
    else:
        override.enabled = payload.enabled
    record_audit(
        db,
        tenant_id=tenant_id,
        actor_user_id=principal.user.id,
        action="feature_flag.tenant_override_set",
        resource_type="tenant_feature_flag",
        resource_id=str(override.id),
        reason=payload.reason,
        details={"key": key, "enabled": override.enabled, "platform_admin": True},
    )
    db.commit()
    return {
        "id": str(override.id),
        "tenant_id": str(tenant_id),
        "key": key,
        "enabled": override.enabled,
    }


@router.delete("/feature-flags/{key}/tenants/{tenant_id}", status_code=204)
def remove_tenant_feature_flag(
    key: str,
    tenant_id: UUID,
    reason: str = Query(min_length=3, max_length=500),
    principal: Principal = Depends(require_platform_admin),
    db: Session = Depends(get_db),
) -> None:
    key = _validate_flag_key(key)
    override = db.scalar(
        select(TenantFeatureFlag)
        .join(FeatureFlag, FeatureFlag.id == TenantFeatureFlag.feature_flag_id)
        .where(TenantFeatureFlag.tenant_id == tenant_id, FeatureFlag.key == key)
        .with_for_update()
    )
    if override is None:
        raise HTTPException(status_code=404, detail="Tenant feature flag override not found")
    override_id = str(override.id)
    db.delete(override)
    record_audit(
        db,
        tenant_id=tenant_id,
        actor_user_id=principal.user.id,
        action="feature_flag.tenant_override_removed",
        resource_type="tenant_feature_flag",
        resource_id=override_id,
        reason=reason,
        details={"key": key, "platform_admin": True},
    )
    db.commit()


# ── 数电票人工闭环：后台待办 / 开具（上传发票文件）/ 驳回 ──────────────


class InvoiceRejectRequest(BaseModel):
    reason: str = Field(min_length=2, max_length=500)


def _invoice_row(invoice, owner_email: str | None) -> dict:
    return {
        "id": str(invoice.id),
        "tenant_id": str(invoice.tenant_id),
        "tenant_name": owner_email or "",
        "invoice_no": invoice.invoice_no,
        "title": invoice.title,
        "tax_number": invoice.tax_number,
        "invoice_type": invoice.invoice_type,
        "amount": float(invoice.amount or 0),
        "total_amount": float(invoice.total_amount or 0),
        "status": invoice.status,
        "review_note": invoice.review_note,
        "issued_at": invoice.issued_at.isoformat() if invoice.issued_at else None,
        "voucher_filename": invoice.voucher_filename,
        "created_at": invoice.created_at.isoformat() if invoice.created_at else None,
    }


def _notify_invoice(db: Session, invoice, *, issued: bool, reason: str | None = None) -> None:
    """Create an in-app notification for the tenant and email the owners."""
    from app.services.notifications.email import is_email_configured, send_email

    if issued:
        title = f"您的发票已开具（{invoice.invoice_no}）"
        body = (
            f"您好，订单对应发票（抬头：{invoice.title}，金额 ¥{invoice.total_amount:.2f}）"
            "已通过数电票开具，请登录工作台在「账单与发票」中下载。"
        )
        dedup_key = f"invoice_issued:{invoice.id}"
    else:
        title = f"您的开票申请未通过（{invoice.invoice_no}）"
        body = f"很抱歉，您的开票申请未通过审核。原因：{reason or '信息不全'}。请核对抬头与税号后重新申请。"
        dedup_key = f"invoice_rejected:{invoice.id}"
    db.add(
        Notification(
            tenant_id=invoice.tenant_id,
            kind="invoice",
            severity="info",
            title=title,
            body=body,
            entity_type="invoice",
            entity_id=str(invoice.id),
            dedup_key=dedup_key,
        )
    )
    if is_email_configured():
        owners = db.scalars(
            select(User.email)
            .join(Membership, Membership.user_id == User.id)
            .where(Membership.tenant_id == invoice.tenant_id)
        ).all()
        for email in set(owners):
            send_email(email, title, body)
    db.commit()


@router.get("/invoices")
def admin_list_invoices(
    status: str | None = Query(default=None),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    principal: Principal = Depends(require_platform_admin),
    db: Session = Depends(get_db),
) -> dict:
    """Backoffice invoice work queue (数电票人工待办)."""
    query = select(Invoice).order_by(Invoice.created_at.desc())
    if status:
        query = query.where(Invoice.status == status)
    invoices = db.scalars(query.limit(limit).offset(offset)).all()
    total = db.scalar(
        select(func.count()).select_from(Invoice).where(Invoice.status == status) if status
        else select(func.count()).select_from(Invoice)
    )
    rows = []
    for invoice in invoices:
        owner_email = db.scalar(
            select(User.email).where(User.tenant_id == invoice.tenant_id).order_by(User.created_at).limit(1)
        )
        rows.append(_invoice_row(invoice, owner_email))
    return {"total": total, "limit": limit, "offset": offset, "items": rows}


@router.post("/invoices/{invoice_id}/issue")
async def admin_issue_invoice(
    invoice_id: UUID,
    file: UploadFile = File(...),
    note: str | None = Form(default=None),
    principal: Principal = Depends(require_platform_admin),
    db: Session = Depends(get_db),
) -> dict:
    """Mark an invoice issued and attach the e-invoice file (数电票 PDF/OFD)."""
    invoice = db.scalar(select(Invoice).where(Invoice.id == invoice_id).with_for_update())
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if invoice.status == "issued":
        raise HTTPException(status_code=409, detail="该发票已开具，如需重开请先驳回再重新申请")
    content = await file.read(5 * 1024 * 1024 + 1)
    if not content:
        raise HTTPException(status_code=400, detail="发票文件为空")
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="发票文件超过 5MB")
    content_type = file.content_type or "application/octet-stream"
    allowed = (
        "application/pdf",
        "application/octet-stream",
        "image/jpeg",
        "image/png",
    )
    if content_type not in allowed:
        raise HTTPException(status_code=400, detail="不支持的文件类型")
    invoice.voucher_filename = file.filename or f"einvoice_{invoice.invoice_no}.pdf"
    invoice.voucher_content_type = content_type
    invoice.voucher_data = content
    invoice.status = "issued"
    invoice.issued_at = now_utc()
    if note:
        invoice.review_note = note
    record_audit(db, tenant_id=invoice.tenant_id, actor_user_id=principal.user.id, action="invoice.issue", resource_type="invoice", resource_id=str(invoice.id))
    db.commit()
    _notify_invoice(db, invoice, issued=True)
    return {"id": str(invoice.id), "status": invoice.status, "voucher_filename": invoice.voucher_filename}


@router.post("/invoices/{invoice_id}/reject")
def admin_reject_invoice(
    invoice_id: UUID,
    payload: InvoiceRejectRequest,
    principal: Principal = Depends(require_platform_admin),
    db: Session = Depends(get_db),
) -> dict:
    invoice = db.scalar(select(Invoice).where(Invoice.id == invoice_id).with_for_update())
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if invoice.status == "issued":
        raise HTTPException(status_code=409, detail="该发票已开具，无法驳回")
    invoice.status = "rejected"
    invoice.review_note = payload.reason
    record_audit(db, tenant_id=invoice.tenant_id, actor_user_id=principal.user.id, action="invoice.reject", resource_type="invoice", resource_id=str(invoice.id))
    db.commit()
    _notify_invoice(db, invoice, issued=False, reason=payload.reason)
    return {"id": str(invoice.id), "status": invoice.status}
