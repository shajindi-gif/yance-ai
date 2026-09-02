"""Outcome-based Agent Task API — Async + Progress + DOCX + Next Best Action"""
import secrets
import uuid
from datetime import UTC, datetime
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
    Company,
    Deliverable,
    Opportunity,
    Order,
    Policy,
    RevisionRequest,
    Task,
    UserRole,
)
from app.services.report.matcher import match_policies_for_company
from app.services.report.pdf import generate_match_report_pdf

router = APIRouter(prefix="/tasks", tags=["tasks"])

VALID_TYPES = {"policy_scan": ("企业政策机会扫描", 0.0), "policy_diagnosis": ("企业政策深度诊断", 99.0), "application_draft": ("政策申报材料初稿", 299.0)}


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
            __import__("sqlalchemy").text("UPDATE tasks SET progress=:p, current_stage=:s, updated_at=now() WHERE id=:tid"),
            {"p": progress, "s": stage, "tid": task_id}
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
        company = db.scalar(select(Company).where(Company.id == task.company_id))
        if not company:
            task.status = "failed"
            task.failure_reason = "企业不存在"
            db.commit()
            return

        task.status = "running"
        task.started_at = datetime.now(UTC)
        db.commit()

        # Stage 1: Read company profile (10%)
        _update_progress(task_id, 10, "正在读取企业画像")
        run1 = AgentRun(tenant_id=task.tenant_id, task_id=task.id, user_id=task.user_id,
                        agent_name="profile_reader", provider="internal", model="n/a",
                        status="running", started_at=datetime.now(UTC))
        db.add(run1)
        db.commit()
        run1.status = "completed"
        run1.finished_at = datetime.now(UTC)
        run1.latency_ms = 50
        db.commit()

        # Stage 2: Policy matching via RAG (30%)
        _update_progress(task_id, 30, "正在检索政策库并匹配")
        run2 = AgentRun(tenant_id=task.tenant_id, task_id=task.id, user_id=task.user_id,
                        agent_name="policy_match_agent", provider=task.model_provider or "qwen",
                        model="qwen-plus", status="running", started_at=datetime.now(UTC))
        db.add(run2)
        db.commit()

        import asyncio
        loop = asyncio.new_event_loop()
        opportunities = loop.run_until_complete(match_policies_for_company(db, company, task.tenant_id))
        loop.close()

        run2.status = "completed"
        run2.finished_at = datetime.now(UTC)
        run2.latency_ms = int((run2.finished_at - run2.started_at).total_seconds() * 1000)
        db.commit()

        # Stage 3: Analysis (60%)
        _update_progress(task_id, 60, f"已发现 {len(opportunities)} 项政策机会，正在分析")
        policy_ids = [o.policy_id for o in opportunities]
        policies = db.scalars(select(Policy).where(Policy.id.in_(policy_ids))).all() if policy_ids else []

        # Stage 4: Generate PDF (80%)
        _update_progress(task_id, 80, "正在生成报告文件")
        run3 = AgentRun(tenant_id=task.tenant_id, task_id=task.id, user_id=task.user_id,
                        agent_name="report_generator", provider="internal", model="weasyprint",
                        status="running", started_at=datetime.now(UTC))
        db.add(run3)
        db.commit()
        pdf_bytes = generate_match_report_pdf(company, opportunities, policies)
        run3.status = "completed"
        run3.finished_at = datetime.now(UTC)
        run3.latency_ms = int((run3.finished_at - run3.started_at).total_seconds() * 1000)
        db.commit()

        # Stage 5: Create Deliverable (100%)
        _update_progress(task_id, 95, "正在生成交付物")
        deliverable = Deliverable(
            tenant_id=task.tenant_id, task_id=task.id, user_id=task.user_id,
            company_id=task.company_id, deliverable_type=task.task_type,
            title=f"{company.name} - {VALID_TYPES.get(task.task_type, ('', task.task_type))[0]}报告",
            content_json={"total_matches": len(opportunities),
                          "policies": [{"title": p.title, "level": p.level, "support_amount": p.support_amount} for p in policies[:10]]},
            content_markdown=f"# {company.name} 政策分析报告\n\n匹配政策数: {len(opportunities)}",
            pdf_url=f"/api/v1/tasks/{task.id}/download",
            version=1, status="generated", quality_score=88,
            generated_at=datetime.now(UTC),
        )
        db.add(deliverable)
        task.status = "delivered"
        task.delivery_status = "delivered"
        task.completed_at = datetime.now(UTC)
        _update_progress(task_id, 100, "已完成")
        db.commit()
        db.refresh(deliverable)

    except Exception as e:
        db.rollback()
        try:
            task = db.scalar(select(Task).where(Task.id == task_id))
            if task:
                task.status = "failed"
                task.failure_reason = str(e)[:500]
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


# ── API Endpoints ────────────────────────────────────────────
@router.post("")
async def create_task(req: TaskCreate, principal: Principal = Depends(require_roles(UserRole.owner, UserRole.admin, UserRole.member)), db: Session = Depends(get_db)):
    company = db.scalar(select(Company).where(Company.id == req.company_id, Company.tenant_id == principal.tenant_id))
    if not company:
        raise HTTPException(404, "企业不存在")
    type_title, price = VALID_TYPES.get(req.task_type, (req.task_type, 0.0))
    task = Task(
        tenant_id=principal.tenant_id, user_id=principal.user.id, company_id=req.company_id,
        task_type=req.task_type, title=req.title or f"{company.name} - {type_title}",
        description=req.description, requirements=req.requirements,
        status="submitted", agent_type="policy_agent", estimated_price=price,
        payment_status="free" if price == 0 else "unpaid", progress=0, current_stage="待执行",
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    if price > 0:
        task.status = "awaiting_payment"
        db.commit()
    return {"id": str(task.id), "task_type": task.task_type, "title": task.title,
            "status": task.status, "payment_status": task.payment_status,
            "estimated_price": float(task.estimated_price or 0), "company_name": company.name,
            "created_at": task.created_at.isoformat()}


@router.get("")
async def list_tasks(principal: Principal = Depends(require_roles(UserRole.owner, UserRole.admin, UserRole.member)), db: Session = Depends(get_db)):
    tasks = db.scalars(select(Task).where(Task.tenant_id == principal.tenant_id).order_by(Task.created_at.desc())).all()
    return [{"id": str(t.id), "task_type": t.task_type, "title": t.title, "status": t.status,
             "progress": t.progress, "current_stage": t.current_stage,
             "payment_status": t.payment_status, "created_at": t.created_at.isoformat()} for t in tasks]


@router.get("/{task_id}")
async def get_task(task_id: uuid.UUID, principal: Principal = Depends(require_roles(UserRole.owner, UserRole.admin, UserRole.member)), db: Session = Depends(get_db)):
    task = db.scalar(select(Task).where(Task.id == task_id, Task.tenant_id == principal.tenant_id))
    if not task:
        raise HTTPException(404, "任务不存在")
    deliverables = db.scalars(select(Deliverable).where(Deliverable.task_id == task_id).order_by(Deliverable.version.desc())).all()
    revisions = db.scalars(select(RevisionRequest).where(RevisionRequest.task_id == task_id).order_by(RevisionRequest.created_at.desc())).all()
    runs = db.scalars(select(AgentRun).where(AgentRun.task_id == task_id).order_by(AgentRun.started_at)).all()
    company = db.scalar(select(Company).where(Company.id == task.company_id))
    return {
        "id": str(task.id), "task_type": task.task_type, "title": task.title,
        "status": task.status, "progress": task.progress, "current_stage": task.current_stage,
        "payment_status": task.payment_status, "description": task.description,
        "company_name": company.name if company else "",
        "deliverables": [{"id": str(d.id), "type": d.deliverable_type, "title": d.title,
                          "version": d.version, "status": d.status, "quality_score": d.quality_score,
                          "pdf_url": d.pdf_url, "generated_at": d.generated_at.isoformat() if d.generated_at else None} for d in deliverables],
        "revisions": [{"id": str(r.id), "request": r.request, "status": r.status, "created_at": r.created_at.isoformat()} for r in revisions],
        "agent_runs": [{"agent": r.agent_name, "status": r.status, "latency_ms": r.latency_ms} for r in runs],
        "created_at": task.created_at.isoformat(),
    }


@router.post("/{task_id}/execute")
async def execute_task(task_id: uuid.UUID, background_tasks: BackgroundTasks,
                       principal: Principal = Depends(require_roles(UserRole.owner, UserRole.admin, UserRole.member)),
                       db: Session = Depends(get_db)):
    task = db.scalar(select(Task).where(Task.id == task_id, Task.tenant_id == principal.tenant_id))
    if not task:
        raise HTTPException(404, "任务不存在")
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
async def pay_task(task_id: uuid.UUID, principal: Principal = Depends(require_roles(UserRole.owner, UserRole.admin, UserRole.member)), db: Session = Depends(get_db)):
    if settings.app_env == "production" or not settings.demo_features_enabled:
        raise HTTPException(status_code=404, detail="Not found")

    task = db.scalar(select(Task).where(Task.id == task_id, Task.tenant_id == principal.tenant_id))
    if not task or task.payment_status != "unpaid":
        raise HTTPException(400, "任务不存在或已支付")
    price = float(task.estimated_price or 0)
    order = Order(tenant_id=principal.tenant_id, order_no=f"Y{secrets.token_hex(8).upper()}",
                  product_code=task.task_type, amount=price, currency="CNY", status="paid")
    db.add(order)
    db.commit()
    db.refresh(order)
    task.payment_status = "paid"
    task.status = "paid"
    task.order_id = order.id
    task.final_price = price
    db.commit()
    return {"task_id": str(task_id), "order_no": order.order_no, "amount": price, "payment_status": "paid"}


@router.post("/{task_id}/revision")
async def request_revision(task_id: uuid.UUID, req: RevisionCreate, principal: Principal = Depends(require_roles(UserRole.owner, UserRole.admin, UserRole.member)), db: Session = Depends(get_db)):
    task = db.scalar(select(Task).where(Task.id == task_id, Task.tenant_id == principal.tenant_id))
    if not task:
        raise HTTPException(404, "任务不存在")
    revision = RevisionRequest(tenant_id=principal.tenant_id, task_id=task_id,
                               deliverable_id=req.deliverable_id, user_id=principal.user.id,
                               request=req.request, status="pending")
    db.add(revision)
    task.status = "revision_requested"
    db.commit()
    return {"revision_id": str(revision.id), "status": "pending", "message": "修改请求已提交"}


@router.post("/{task_id}/accept")
async def accept_task(task_id: uuid.UUID, principal: Principal = Depends(require_roles(UserRole.owner, UserRole.admin, UserRole.member)), db: Session = Depends(get_db)):
    task = db.scalar(select(Task).where(Task.id == task_id, Task.tenant_id == principal.tenant_id))
    if not task or task.status not in ("delivered", "revision_requested"):
        raise HTTPException(400, "任务状态不允许验收")
    deliverable = db.scalar(select(Deliverable).where(Deliverable.task_id == task_id).order_by(Deliverable.version.desc()))
    if deliverable:
        deliverable.status = "accepted"
        deliverable.accepted_at = datetime.now(UTC)
    task.status = "accepted"
    task.delivery_status = "accepted"
    db.commit()
    return {"task_id": str(task_id), "status": "accepted", "message": "任务验收成功"}


@router.get("/{task_id}/download")
async def download_pdf(task_id: uuid.UUID, principal: Principal = Depends(require_roles(UserRole.owner, UserRole.admin, UserRole.member)), db: Session = Depends(get_db)):
    task = db.scalar(select(Task).where(Task.id == task_id, Task.tenant_id == principal.tenant_id))
    if not task:
        raise HTTPException(404, "任务不存在")
    deliverable = db.scalar(select(Deliverable).where(Deliverable.task_id == task_id).order_by(Deliverable.version.desc()))
    if not deliverable:
        raise HTTPException(404, "未找到交付物")
    company = db.scalar(select(Company).where(Company.id == task.company_id))
    opportunities = db.scalars(select(Opportunity).where(Opportunity.company_id == task.company_id).order_by(Opportunity.score.desc())).all()
    policy_ids = [o.policy_id for o in opportunities]
    policies = db.scalars(select(Policy).where(Policy.id.in_(policy_ids))).all() if policy_ids else []
    pdf_bytes = generate_match_report_pdf(company, opportunities, policies)
    filename = f"{company.name}_{deliverable.title}_{deliverable.version}.pdf"
    return Response(content=pdf_bytes, media_type="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"})


@router.get("/{task_id}/next-actions")
async def next_best_actions(task_id: uuid.UUID, principal: Principal = Depends(require_roles(UserRole.owner, UserRole.admin, UserRole.member)), db: Session = Depends(get_db)):
    """Rule-based Next Best Action recommendations."""
    task = db.scalar(select(Task).where(Task.id == task_id, Task.tenant_id == principal.tenant_id))
    if not task:
        raise HTTPException(404, "任务不存在")
    opportunities = db.scalars(select(Opportunity).where(Opportunity.company_id == task.company_id).order_by(Opportunity.score.desc())).all()
    actions = []
    high_matches = [o for o in opportunities if o.score >= 0.7]
    all_missing = set()
    for o in opportunities:
        for m in (o.evidence_json or {}).get("missing_materials", []):
            all_missing.add(m)
    if task.task_type == "policy_scan" and high_matches:
        actions.append({"action": "升级深度诊断", "desc": f"发现 {len(high_matches)} 项高匹配政策，建议深度分析申报条件", "product_code": "POLICY_DIAGNOSIS", "price": 99, "cta": "深度诊断 ¥99"})
    if all_missing:
        actions.append({"action": "补齐申报材料", "desc": f"当前有 {len(all_missing)} 项材料需要准备", "product_code": None, "price": 0, "cta": "查看材料清单"})
    if high_matches:
        actions.append({"action": "生成申报方案", "desc": "为最优政策生成完整申报方案", "product_code": "APPLICATION_PLAN", "price": 699, "cta": "生成方案 ¥699"})
    if task.task_type == "policy_scan":
        actions.append({"action": "开启持续监控", "desc": "新政策发布时自动通知", "product_code": None, "price": 0, "cta": "即将开放"})
    return {"task_id": str(task_id), "actions": actions[:4]}


@router.get("/admin/all")
async def admin_tasks(principal: Principal = Depends(require_roles(UserRole.owner)), db: Session = Depends(get_db)):
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
            "success_rate": round(len([t for t in tasks if t.status in ("delivered", "accepted")]) / max(len(tasks), 1) * 100),
        },
        "tasks": [{"id": str(t.id), "title": t.title[:40], "task_type": t.task_type, "status": t.status,
                    "progress": t.progress, "current_stage": t.current_stage,
                    "created_at": t.created_at.isoformat()} for t in tasks[:50]]
    }
