"""Outcome-based Agent Task API — Async + Progress + DOCX + Next Best Action"""

import secrets
import uuid
from datetime import UTC, datetime
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import Principal, require_roles
from app.core.config import settings
from app.core.db import get_db
from app.models.models import (
    AgentRun,
    Company,
    Deliverable,
    Opportunity,
    Order,
    Product,
    RevisionRequest,
    Task,
    UserRole,
)
from app.services.report.snapshot import report_bytes

router = APIRouter(prefix="/tasks", tags=["tasks"])

TASK_TYPES = {
    "policy_scan": ("企业政策机会扫描", None),
    "policy_diagnosis": ("企业政策深度诊断", "POLICY_DIAGNOSIS"),
    "application_draft": ("政策申报材料初稿", "APPLICATION_PLAN"),
}


class TaskCreate(BaseModel):
    company_id: uuid.UUID
    task_type: str = Field(pattern="^(policy_scan|policy_diagnosis|application_draft)$")
    title: str | None = None
    description: str | None = None
    requirements: str | None = None


class RevisionCreate(BaseModel):
    deliverable_id: uuid.UUID
    request: str = Field(min_length=5, max_length=2000)


# ── API Endpoints ────────────────────────────────────────────
@router.post("")
async def create_task(
    req: TaskCreate,
    principal: Principal = Depends(require_roles(UserRole.owner, UserRole.admin, UserRole.member)),
    db: Session = Depends(get_db),
):
    if req.task_type == "policy_scan":
        raise HTTPException(
            status_code=409,
            detail="请通过 /policy-scans 创建可追溯的政策扫描",
        )
    raise HTTPException(
        status_code=501,
        detail="该任务类型尚未接入可验证的 Agent 工作流",
    )


@router.get("")
async def list_tasks(
    principal: Principal = Depends(require_roles(UserRole.owner, UserRole.admin, UserRole.member)),
    db: Session = Depends(get_db),
):
    tasks = db.scalars(
        select(Task).where(Task.tenant_id == principal.tenant_id).order_by(Task.created_at.desc())
    ).all()
    return [
        {
            "id": str(t.id),
            "task_type": t.task_type,
            "title": t.title,
            "status": t.status,
            "progress": t.progress,
            "current_stage": t.current_stage,
            "payment_status": t.payment_status,
            "created_at": t.created_at.isoformat(),
        }
        for t in tasks
    ]


@router.get("/{task_id}")
async def get_task(
    task_id: uuid.UUID,
    principal: Principal = Depends(require_roles(UserRole.owner, UserRole.admin, UserRole.member)),
    db: Session = Depends(get_db),
):
    task = db.scalar(select(Task).where(Task.id == task_id, Task.tenant_id == principal.tenant_id))
    if not task:
        raise HTTPException(404, "任务不存在")
    deliverables = db.scalars(
        select(Deliverable)
        .where(Deliverable.task_id == task_id, Deliverable.tenant_id == principal.tenant_id)
        .order_by(Deliverable.version.desc())
    ).all()
    revisions = db.scalars(
        select(RevisionRequest)
        .where(
            RevisionRequest.task_id == task_id,
            RevisionRequest.tenant_id == principal.tenant_id,
        )
        .order_by(RevisionRequest.created_at.desc())
    ).all()
    runs = db.scalars(
        select(AgentRun)
        .where(AgentRun.task_id == task_id, AgentRun.tenant_id == principal.tenant_id)
        .order_by(AgentRun.started_at)
    ).all()
    company = db.scalar(
        select(Company).where(
            Company.id == task.company_id,
            Company.tenant_id == principal.tenant_id,
        )
    )
    return {
        "id": str(task.id),
        "task_type": task.task_type,
        "title": task.title,
        "status": task.status,
        "progress": task.progress,
        "current_stage": task.current_stage,
        "payment_status": task.payment_status,
        "description": task.description,
        "company_name": company.name if company else "",
        "deliverables": [
            {
                "id": str(d.id),
                "type": d.deliverable_type,
                "title": d.title,
                "version": d.version,
                "status": d.status,
                "quality_score": d.quality_score,
                "pdf_url": d.pdf_url,
                "generated_at": d.generated_at.isoformat() if d.generated_at else None,
            }
            for d in deliverables
        ],
        "revisions": [
            {
                "id": str(r.id),
                "request": r.request,
                "status": r.status,
                "created_at": r.created_at.isoformat(),
            }
            for r in revisions
        ],
        "agent_runs": [
            {
                "id": str(r.id),
                "agent": r.agent_name,
                "status": r.status,
                "prompt_version": r.prompt_version,
                "total_tokens": r.total_tokens,
                "cost_usd": float(r.cost_usd or 0),
                "latency_ms": r.latency_ms,
            }
            for r in runs
        ],
        "created_at": task.created_at.isoformat(),
    }


@router.post("/{task_id}/execute")
async def execute_task(
    task_id: uuid.UUID,
    principal: Principal = Depends(require_roles(UserRole.owner, UserRole.admin, UserRole.member)),
    db: Session = Depends(get_db),
):
    task = db.scalar(select(Task).where(Task.id == task_id, Task.tenant_id == principal.tenant_id))
    if not task:
        raise HTTPException(404, "任务不存在")
    run = db.scalar(
        select(AgentRun)
        .where(AgentRun.task_id == task.id, AgentRun.tenant_id == principal.tenant_id)
        .order_by(AgentRun.created_at.desc())
    )
    if task.task_type != "policy_scan" or not task.scan_id or not run or not run.workflow_run_id:
        raise HTTPException(
            status_code=501,
            detail="该历史任务尚未迁移到可验证的 Agent 工作流",
        )
    if run.status in {"queued", "planning", "running"}:
        return {
            "task_id": str(task_id),
            "run_id": str(run.id),
            "status": run.status,
            "message": "任务已由独立 Agent Worker 接管",
        }
    raise HTTPException(status_code=409, detail=f"Agent Run 状态 {run.status} 不允许重新排队")


@router.post("/{task_id}/pay")
async def pay_task(
    task_id: uuid.UUID,
    principal: Principal = Depends(require_roles(UserRole.owner, UserRole.admin, UserRole.member)),
    db: Session = Depends(get_db),
):
    if settings.app_env == "production" or not settings.demo_features_enabled:
        raise HTTPException(status_code=404, detail="Not found")

    task = db.scalar(select(Task).where(Task.id == task_id, Task.tenant_id == principal.tenant_id))
    if not task or task.payment_status != "unpaid":
        raise HTTPException(400, "任务不存在或已支付")
    price = float(task.estimated_price or 0)
    product_code = TASK_TYPES[task.task_type][1]
    if not product_code:
        raise HTTPException(status_code=400, detail="Free tasks do not require payment")
    product = db.scalar(
        select(Product).where(Product.code == product_code, Product.active.is_(True))
    )
    if not product or float(product.promotional_price or product.price) != price:
        raise HTTPException(status_code=409, detail="Product price changed; recreate the task")
    order = Order(
        tenant_id=principal.tenant_id,
        order_no=f"Y{secrets.token_hex(8).upper()}",
        product_code=product_code,
        amount=price,
        currency="CNY",
        resource_type=product.entitlement_type,
        resource_id=task.company_id,
        status="paid",
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    task.payment_status = "paid"
    task.status = "paid"
    task.order_id = order.id
    task.final_price = price
    db.commit()
    return {
        "task_id": str(task_id),
        "order_no": order.order_no,
        "amount": price,
        "payment_status": "paid",
    }


@router.post("/{task_id}/revision")
async def request_revision(
    task_id: uuid.UUID,
    req: RevisionCreate,
    principal: Principal = Depends(require_roles(UserRole.owner, UserRole.admin, UserRole.member)),
    db: Session = Depends(get_db),
):
    task = db.scalar(select(Task).where(Task.id == task_id, Task.tenant_id == principal.tenant_id))
    if not task:
        raise HTTPException(404, "任务不存在")
    deliverable = db.scalar(
        select(Deliverable).where(
            Deliverable.id == req.deliverable_id,
            Deliverable.task_id == task_id,
            Deliverable.tenant_id == principal.tenant_id,
        )
    )
    if not deliverable:
        raise HTTPException(status_code=404, detail="交付物不存在")
    revision = RevisionRequest(
        tenant_id=principal.tenant_id,
        task_id=task_id,
        deliverable_id=req.deliverable_id,
        user_id=principal.user.id,
        request=req.request,
        status="pending",
    )
    db.add(revision)
    task.status = "revision_requested"
    db.commit()
    return {"revision_id": str(revision.id), "status": "pending", "message": "修改请求已提交"}


@router.post("/{task_id}/accept")
async def accept_task(
    task_id: uuid.UUID,
    principal: Principal = Depends(require_roles(UserRole.owner, UserRole.admin, UserRole.member)),
    db: Session = Depends(get_db),
):
    task = db.scalar(select(Task).where(Task.id == task_id, Task.tenant_id == principal.tenant_id))
    if not task or task.status not in ("delivered", "revision_requested"):
        raise HTTPException(400, "任务状态不允许验收")
    deliverable = db.scalar(
        select(Deliverable)
        .where(Deliverable.task_id == task_id, Deliverable.tenant_id == principal.tenant_id)
        .order_by(Deliverable.version.desc())
    )
    if deliverable:
        deliverable.status = "accepted"
        deliverable.accepted_at = datetime.now(UTC)
    task.status = "accepted"
    task.delivery_status = "accepted"
    db.commit()
    return {"task_id": str(task_id), "status": "accepted", "message": "任务验收成功"}


@router.get("/{task_id}/download")
async def download_pdf(
    task_id: uuid.UUID,
    deliverable_id: uuid.UUID | None = None,
    principal: Principal = Depends(require_roles(UserRole.owner, UserRole.admin, UserRole.member)),
    db: Session = Depends(get_db),
):
    task = db.scalar(select(Task).where(Task.id == task_id, Task.tenant_id == principal.tenant_id))
    if not task:
        raise HTTPException(404, "任务不存在")
    if task.status not in {"delivered", "accepted", "revision_requested"}:
        raise HTTPException(409, "任务尚未形成可交付报告，请检查执行状态后重试")
    deliverable = db.scalar(
        select(Deliverable)
        .where(Deliverable.task_id == task_id, Deliverable.tenant_id == principal.tenant_id,
               Deliverable.id == deliverable_id if deliverable_id else Deliverable.id.is_not(None))
        .order_by(Deliverable.version.desc())
    )
    if not deliverable:
        raise HTTPException(404, "未找到交付物")
    pdf_bytes = report_bytes(deliverable)
    filename = f"{deliverable.title}_v{deliverable.version}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}",
                 "Cache-Control": "private, no-store"},
    )


@router.get("/{task_id}/next-actions")
async def next_best_actions(
    task_id: uuid.UUID,
    principal: Principal = Depends(require_roles(UserRole.owner, UserRole.admin, UserRole.member)),
    db: Session = Depends(get_db),
):
    """Rule-based Next Best Action recommendations."""
    task = db.scalar(select(Task).where(Task.id == task_id, Task.tenant_id == principal.tenant_id))
    if not task:
        raise HTTPException(404, "任务不存在")
    opportunities = db.scalars(
        select(Opportunity)
        .where(
            Opportunity.company_id == task.company_id,
            Opportunity.tenant_id == principal.tenant_id,
        )
        .order_by(Opportunity.score.desc())
    ).all()
    actions = []
    high_matches = [o for o in opportunities if o.score is not None and o.score >= 0.7]
    all_missing = set()
    for o in opportunities:
        for m in (o.evidence_json or {}).get("missing_materials", []):
            all_missing.add(m)
    if task.task_type == "policy_scan" and high_matches:
        actions.append(
            {
                "action": "复核高相关性机会",
                "desc": f"发现 {len(high_matches)} 项高相关性政策，下一步应核验资格与原文依据",
                "product_code": None,
                "price": 0,
                "cta": "查看政策机会",
                "href": "/opportunities",
            }
        )
    if all_missing:
        actions.append(
            {
                "action": "补齐申报材料",
                "desc": f"当前有 {len(all_missing)} 项材料需要准备",
                "product_code": None,
                "price": 0,
                "cta": "查看材料清单",
                "href": "/applications",
            }
        )
    return {"task_id": str(task_id), "actions": actions[:4]}


@router.get("/admin/all")
async def admin_tasks(
    principal: Principal = Depends(require_roles(UserRole.owner)), db: Session = Depends(get_db)
):
    tasks = db.scalars(
        select(Task)
        .where(Task.tenant_id == principal.tenant_id)
        .order_by(Task.created_at.desc())
        .limit(100)
    ).all()
    today = datetime.now(UTC).replace(hour=0, minute=0, second=0)
    today_tasks = [t for t in tasks if t.created_at >= today]
    return {
        "metrics": {
            "today_total": len(today_tasks),
            "running": len([t for t in tasks if t.status == "running"]),
            "completed": len([t for t in tasks if t.status in ("delivered", "accepted")]),
            "failed": len([t for t in tasks if t.status == "failed"]),
            "success_rate": round(
                len([t for t in tasks if t.status in ("delivered", "accepted")])
                / max(len(tasks), 1)
                * 100
            ),
        },
        "tasks": [
            {
                "id": str(t.id),
                "title": t.title[:40],
                "task_type": t.task_type,
                "status": t.status,
                "progress": t.progress,
                "current_stage": t.current_stage,
                "created_at": t.created_at.isoformat(),
            }
            for t in tasks[:50]
        ],
    }
