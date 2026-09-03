"""Outcome-based Agent Task API — Async + Progress + DOCX + Next Best Action"""

import secrets
import uuid
from datetime import UTC, datetime
from time import perf_counter
from urllib.parse import quote

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import Principal, require_roles
from app.core.config import settings
from app.core.db import SessionLocal, get_db
from app.models.models import (
    AgentRun,
    AnalyticsEvent,
    Company,
    Deliverable,
    Opportunity,
    Order,
    Policy,
    PolicyScan,
    Product,
    RevisionRequest,
    Task,
    UserRole,
)
from app.services.policies.visibility import visible_policy_clause
from app.services.report.matcher import match_policies_for_company
from app.services.report.pdf import generate_match_report_pdf

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


# ── Async Worker ─────────────────────────────────────────────
def _update_progress(task_id, progress, stage):
    db = SessionLocal()
    try:
        db.execute(
            __import__("sqlalchemy").text(
                "UPDATE tasks SET progress=:p, current_stage=:s, updated_at=now() WHERE id=:tid"
            ),
            {"p": progress, "s": stage, "tid": task_id},
        )
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


def _run_task_background(task_id: uuid.UUID):
    """Background worker: runs the full Agent pipeline with progress updates."""
    db = SessionLocal()
    try:
        task = db.scalar(select(Task).where(Task.id == task_id))
        if not task:
            return
        company = db.scalar(
            select(Company).where(
                Company.id == task.company_id,
                Company.tenant_id == task.tenant_id,
            )
        )
        if not company:
            task.status = "failed"
            task.failure_reason = "企业不存在"
            db.commit()
            return

        task.status = "running"
        task.started_at = datetime.now(UTC)
        scan = None
        if task.scan_id:
            scan = db.scalar(
                select(PolicyScan).where(
                    PolicyScan.id == task.scan_id,
                    PolicyScan.tenant_id == task.tenant_id,
                )
            )
            if scan:
                scan.status = "running"
                scan.started_at = task.started_at
        db.commit()

        # Stage 1: Read company profile (10%). This is a workflow step, not an Agent run.
        _update_progress(task_id, 10, "正在读取企业画像")

        # Stage 2: Policy matching via RAG (30%)
        _update_progress(task_id, 30, "正在检索政策库并匹配")
        matching_started = perf_counter()
        run2 = AgentRun(
            tenant_id=task.tenant_id,
            task_id=task.id,
            user_id=task.user_id,
            agent_name="policy_match_pipeline",
            provider="embedding_registry",
            model=settings.embedding_model,
            status="running",
            started_at=datetime.now(UTC),
        )
        db.add(run2)
        db.commit()

        import asyncio

        loop = asyncio.new_event_loop()
        opportunities = loop.run_until_complete(
            match_policies_for_company(
                db,
                company,
                task.tenant_id,
                scan_id=scan.id if scan else None,
                profile_version_id=scan.profile_version_id if scan else None,
            )
        )
        loop.close()

        run2.status = "completed"
        run2.finished_at = datetime.now(UTC)
        run2.latency_ms = round((perf_counter() - matching_started) * 1000)
        db.commit()

        # Stage 3: Analysis (60%)
        _update_progress(task_id, 60, f"已发现 {len(opportunities)} 项政策机会，正在分析")
        policy_ids = [o.policy_id for o in opportunities]
        policies = (
            db.scalars(
                select(Policy).where(
                    Policy.id.in_(policy_ids),
                    visible_policy_clause(task.tenant_id),
                )
            ).all()
            if policy_ids
            else []
        )

        # Stage 4: Generate PDF (80%)
        _update_progress(task_id, 80, "正在生成报告文件")
        rendering_started = perf_counter()
        run3 = AgentRun(
            tenant_id=task.tenant_id,
            task_id=task.id,
            user_id=task.user_id,
            agent_name="report_generator",
            provider="internal",
            model="weasyprint",
            status="running",
            started_at=datetime.now(UTC),
        )
        db.add(run3)
        db.commit()
        generate_match_report_pdf(company, opportunities, policies)
        run3.status = "completed"
        run3.finished_at = datetime.now(UTC)
        run3.latency_ms = round((perf_counter() - rendering_started) * 1000)
        db.commit()

        # Stage 5: Create Deliverable (100%)
        _update_progress(task_id, 95, "正在生成交付物")
        deliverable = Deliverable(
            tenant_id=task.tenant_id,
            task_id=task.id,
            user_id=task.user_id,
            company_id=task.company_id,
            deliverable_type=task.task_type,
            title=f"{company.name} - {TASK_TYPES.get(task.task_type, ('', None))[0]}报告",
            content_json={
                "total_matches": len(opportunities),
                "policies": [
                    {"title": p.title, "level": p.level, "support_amount": p.support_amount}
                    for p in policies[:10]
                ],
            },
            content_markdown=f"# {company.name} 政策分析报告\n\n匹配政策数: {len(opportunities)}",
            pdf_url=f"/api/v1/tasks/{task.id}/download",
            version=1,
            status="generated",
            quality_score=None,
            generated_at=datetime.now(UTC),
        )
        db.add(deliverable)
        task.status = "delivered"
        task.delivery_status = "delivered"
        task.completed_at = datetime.now(UTC)
        if scan:
            scan.status = "completed"
            scan.total_opportunities = len(opportunities)
            scan.completed_at = task.completed_at
            db.add(
                AnalyticsEvent(
                    tenant_id=task.tenant_id,
                    user_id=task.user_id,
                    name="policy_scan_completed",
                    properties={
                        "scan_id": str(scan.id),
                        "company_id": str(task.company_id),
                        "total_opportunities": len(opportunities),
                    },
                )
            )
        _update_progress(task_id, 100, "已完成")
        db.commit()
        db.refresh(deliverable)

    except Exception:
        db.rollback()
        try:
            task = db.scalar(select(Task).where(Task.id == task_id))
            if task:
                task.status = "failed"
                task.failure_reason = "task_execution_failed"
                if task.scan_id:
                    scan = db.scalar(
                        select(PolicyScan).where(
                            PolicyScan.id == task.scan_id,
                            PolicyScan.tenant_id == task.tenant_id,
                        )
                    )
                    if scan:
                        scan.status = "failed"
                        scan.error_code = "scan_execution_failed"
                        scan.completed_at = datetime.now(UTC)
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


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
            {"agent": r.agent_name, "status": r.status, "latency_ms": r.latency_ms} for r in runs
        ],
        "created_at": task.created_at.isoformat(),
    }


@router.post("/{task_id}/execute")
async def execute_task(
    task_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    principal: Principal = Depends(require_roles(UserRole.owner, UserRole.admin, UserRole.member)),
    db: Session = Depends(get_db),
):
    task = db.scalar(select(Task).where(Task.id == task_id, Task.tenant_id == principal.tenant_id))
    if not task:
        raise HTTPException(404, "任务不存在")
    if task.task_type != "policy_scan" or not task.scan_id:
        raise HTTPException(
            status_code=501,
            detail="该历史任务尚未迁移到可验证的 Agent 工作流",
        )
    if task.status not in ("submitted", "awaiting_payment", "paid", "revision_requested"):
        raise HTTPException(400, f"状态 {task.status} 不允许执行")
    if task.payment_status == "unpaid":
        raise HTTPException(402, "请先完成支付")
    task.status = "queued"
    task.progress = 0
    task.current_stage = "排队中"
    db.commit()
    background_tasks.add_task(_run_task_background, task_id)
    return {"task_id": str(task_id), "status": "queued", "message": "任务已提交，后台执行中"}


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
    principal: Principal = Depends(require_roles(UserRole.owner, UserRole.admin, UserRole.member)),
    db: Session = Depends(get_db),
):
    task = db.scalar(select(Task).where(Task.id == task_id, Task.tenant_id == principal.tenant_id))
    if not task:
        raise HTTPException(404, "任务不存在")
    deliverable = db.scalar(
        select(Deliverable)
        .where(Deliverable.task_id == task_id, Deliverable.tenant_id == principal.tenant_id)
        .order_by(Deliverable.version.desc())
    )
    if not deliverable:
        raise HTTPException(404, "未找到交付物")
    company = db.scalar(
        select(Company).where(
            Company.id == task.company_id,
            Company.tenant_id == principal.tenant_id,
        )
    )
    opportunities = db.scalars(
        select(Opportunity)
        .where(
            Opportunity.company_id == task.company_id,
            Opportunity.tenant_id == principal.tenant_id,
        )
        .order_by(Opportunity.score.desc())
    ).all()
    policy_ids = [o.policy_id for o in opportunities]
    policies = (
        db.scalars(
            select(Policy).where(
                Policy.id.in_(policy_ids),
                visible_policy_clause(principal.tenant_id),
            )
        ).all()
        if policy_ids
        else []
    )
    pdf_bytes = generate_match_report_pdf(company, opportunities, policies)
    filename = f"{company.name}_{deliverable.title}_{deliverable.version}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
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
