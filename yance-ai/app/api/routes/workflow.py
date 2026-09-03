from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import Principal, get_principal, require_roles
from app.core.db import get_db
from app.models.models import (
    AnalyticsEvent,
    Application,
    ApplicationActivity,
    ApplicationRequirement,
    Company,
    CompanyProfile,
    CompanyProfileVersion,
    Opportunity,
    Policy,
    PolicyScan,
    Task,
    UserRole,
)
from app.schemas.schemas import ApplicationCreate, ApplicationOut, OpportunityOut
from app.services.policies.visibility import visible_policy_clause

router = APIRouter(tags=["policy-scan", "opportunity", "application"])
write_principal = require_roles(UserRole.owner, UserRole.admin, UserRole.member)


class PolicyScanCreate(BaseModel):
    company_id: UUID


class PolicyScanOut(BaseModel):
    id: UUID
    company_id: UUID
    profile_version_id: UUID
    task_id: UUID | None
    status: str
    total_opportunities: int
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    error_code: str | None


class ApplicationStatusUpdate(BaseModel):
    status: Literal[
        "draft",
        "preparing",
        "review",
        "revision_requested",
        "approved",
        "submitted",
        "completed",
        "cancelled",
    ]
    reason: str | None = Field(default=None, max_length=500)


class RequirementStatusUpdate(BaseModel):
    status: Literal["missing", "collecting", "ready", "approved", "not_applicable"]


APPLICATION_TRANSITIONS = {
    "draft": {"preparing", "cancelled"},
    "preparing": {"review", "cancelled"},
    "review": {"approved", "revision_requested", "cancelled"},
    "revision_requested": {"preparing", "review", "cancelled"},
    "approved": {"submitted", "cancelled"},
    "submitted": {"completed"},
    "completed": set(),
    "cancelled": set(),
}


def require_tenant_resource(db: Session, model, resource_id: UUID, tenant_id: UUID, name: str):
    resource = db.scalar(select(model).where(model.id == resource_id, model.tenant_id == tenant_id))
    if not resource:
        raise HTTPException(status_code=404, detail=f"{name} not found")
    return resource


def _scan_out(scan: PolicyScan) -> PolicyScanOut:
    return PolicyScanOut.model_validate(scan, from_attributes=True)


@router.get("/policy-scans", response_model=list[PolicyScanOut])
def list_policy_scans(
    company_id: UUID | None = Query(default=None),
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
):
    query = select(PolicyScan).where(PolicyScan.tenant_id == principal.tenant_id)
    if company_id:
        query = query.where(PolicyScan.company_id == company_id)
    return list(db.scalars(query.order_by(PolicyScan.created_at.desc())).all())


@router.post("/policy-scans", response_model=PolicyScanOut, status_code=202)
def create_policy_scan(
    payload: PolicyScanCreate,
    background_tasks: BackgroundTasks,
    principal: Principal = Depends(write_principal),
    db: Session = Depends(get_db),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", max_length=128),
):
    company = require_tenant_resource(
        db, Company, payload.company_id, principal.tenant_id, "Company"
    )
    if idempotency_key:
        existing = db.scalar(
            select(PolicyScan).where(
                PolicyScan.tenant_id == principal.tenant_id,
                PolicyScan.idempotency_key == idempotency_key,
            )
        )
        if existing:
            return _scan_out(existing)

    profile = db.scalar(
        select(CompanyProfile).where(
            CompanyProfile.company_id == company.id,
            CompanyProfile.tenant_id == principal.tenant_id,
        )
    )
    if not profile or not profile.published_version:
        raise HTTPException(status_code=409, detail="请先发布企业画像版本再开始扫描")
    profile_version = db.scalar(
        select(CompanyProfileVersion).where(
            CompanyProfileVersion.profile_id == profile.id,
            CompanyProfileVersion.version == profile.published_version,
            CompanyProfileVersion.tenant_id == principal.tenant_id,
        )
    )
    if not profile_version:
        raise HTTPException(status_code=409, detail="已发布企业画像版本不可用")

    scan = PolicyScan(
        tenant_id=principal.tenant_id,
        company_id=company.id,
        profile_version_id=profile_version.id,
        requested_by=principal.user.id,
        idempotency_key=idempotency_key,
        status="queued",
    )
    db.add(scan)
    db.flush()
    task = Task(
        tenant_id=principal.tenant_id,
        user_id=principal.user.id,
        company_id=company.id,
        scan_id=scan.id,
        task_type="policy_scan",
        title=f"{company.name} - 企业政策机会扫描",
        status="queued",
        agent_type="policy_agent",
        workflow_version="core-scan-v1",
        estimated_price=0,
        payment_status="free",
        progress=0,
        current_stage="排队中",
    )
    db.add(task)
    db.flush()
    scan.task_id = task.id
    db.add(
        AnalyticsEvent(
            tenant_id=principal.tenant_id,
            user_id=principal.user.id,
            name="policy_scan_started",
            properties={
                "scan_id": str(scan.id),
                "company_id": str(company.id),
                "profile_version_id": str(profile_version.id),
            },
        )
    )
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        if idempotency_key:
            existing = db.scalar(
                select(PolicyScan).where(
                    PolicyScan.tenant_id == principal.tenant_id,
                    PolicyScan.idempotency_key == idempotency_key,
                )
            )
            if existing:
                return _scan_out(existing)
        raise
    db.refresh(scan)

    # Phase 4 replaces this process-local runner with the durable Agent Harness.
    from app.api.routes.tasks import _run_task_background

    background_tasks.add_task(_run_task_background, task.id)
    return _scan_out(scan)


@router.get("/policy-scans/{scan_id}", response_model=PolicyScanOut)
def get_policy_scan(
    scan_id: UUID,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
):
    return require_tenant_resource(db, PolicyScan, scan_id, principal.tenant_id, "Policy scan")


@router.get("/opportunities", response_model=list[OpportunityOut])
def list_opportunities(
    company_id: UUID | None = Query(default=None),
    scan_id: UUID | None = Query(default=None),
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> list[Opportunity]:
    query = select(Opportunity).where(Opportunity.tenant_id == principal.tenant_id)
    if company_id:
        query = query.where(Opportunity.company_id == company_id)
    if scan_id:
        query = query.where(Opportunity.scan_id == scan_id)
    return list(
        db.scalars(query.order_by(Opportunity.created_at.desc(), Opportunity.score.desc())).all()
    )


@router.post("/opportunities", status_code=501)
def create_opportunity_disabled(
    principal: Principal = Depends(write_principal),
):
    raise HTTPException(
        status_code=501,
        detail="机会只能由可追溯的政策扫描生成，手工创建尚未开放",
    )


@router.get("/opportunities/{opportunity_id}")
def get_opportunity(
    opportunity_id: UUID,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
):
    opportunity = require_tenant_resource(
        db, Opportunity, opportunity_id, principal.tenant_id, "Opportunity"
    )
    policy = None
    if opportunity.policy_id:
        policy = db.scalar(
            select(Policy).where(
                Policy.id == opportunity.policy_id,
                visible_policy_clause(principal.tenant_id),
            )
        )
    return {
        **OpportunityOut.model_validate(opportunity).model_dump(mode="json"),
        "policy_content_available": bool(policy and policy.content),
    }


@router.get("/applications", response_model=list[ApplicationOut])
def list_applications(
    principal: Principal = Depends(get_principal), db: Session = Depends(get_db)
) -> list[Application]:
    return list(
        db.scalars(
            select(Application)
            .where(Application.tenant_id == principal.tenant_id)
            .order_by(Application.updated_at.desc())
        ).all()
    )


@router.post("/applications", response_model=ApplicationOut, status_code=201)
def create_application(
    payload: ApplicationCreate,
    principal: Principal = Depends(write_principal),
    db: Session = Depends(get_db),
) -> Application:
    company = require_tenant_resource(
        db, Company, payload.company_id, principal.tenant_id, "Company"
    )
    opportunity = None
    if payload.opportunity_id:
        opportunity = require_tenant_resource(
            db, Opportunity, payload.opportunity_id, principal.tenant_id, "Opportunity"
        )
        if opportunity.company_id != company.id:
            raise HTTPException(
                status_code=409,
                detail="Opportunity does not belong to the selected company",
            )
        existing = db.scalar(
            select(Application).where(
                Application.tenant_id == principal.tenant_id,
                Application.opportunity_id == opportunity.id,
                Application.status != "cancelled",
            )
        )
        if existing:
            return existing

    application = Application(
        tenant_id=principal.tenant_id,
        company_id=company.id,
        opportunity_id=opportunity.id if opportunity else None,
        title=payload.title,
        status="draft",
        form_data=payload.form_data,
        owner_user_id=principal.user.id,
        progress=0,
        review_status="not_requested",
    )
    db.add(application)
    db.flush()
    if opportunity:
        materials = (opportunity.evidence_json or {}).get("missing_materials", [])
        for position, material in enumerate(materials):
            db.add(
                ApplicationRequirement(
                    tenant_id=principal.tenant_id,
                    application_id=application.id,
                    title=str(material)[:300],
                    description="扫描阶段识别的候选材料；尚未与已导入资料完成核验。",
                    category="material",
                    status="missing",
                    is_hard_gate=False,
                    source_json={"opportunity_id": str(opportunity.id)},
                    sort_order=position,
                )
            )
    db.add_all(
        [
            ApplicationActivity(
                tenant_id=principal.tenant_id,
                application_id=application.id,
                actor_user_id=principal.user.id,
                action="application_created",
                summary="申报工作区已创建",
                metadata_json={"opportunity_id": str(opportunity.id) if opportunity else None},
            ),
            AnalyticsEvent(
                tenant_id=principal.tenant_id,
                user_id=principal.user.id,
                name="application_created",
                properties={
                    "application_id": str(application.id),
                    "company_id": str(company.id),
                    "opportunity_id": str(opportunity.id) if opportunity else None,
                },
            ),
        ]
    )
    db.commit()
    db.refresh(application)
    return application


@router.get("/applications/{application_id}")
def get_application(
    application_id: UUID,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
):
    application = require_tenant_resource(
        db, Application, application_id, principal.tenant_id, "Application"
    )
    company = require_tenant_resource(
        db, Company, application.company_id, principal.tenant_id, "Company"
    )
    opportunity = (
        require_tenant_resource(
            db, Opportunity, application.opportunity_id, principal.tenant_id, "Opportunity"
        )
        if application.opportunity_id
        else None
    )
    requirements = db.scalars(
        select(ApplicationRequirement)
        .where(
            ApplicationRequirement.application_id == application.id,
            ApplicationRequirement.tenant_id == principal.tenant_id,
        )
        .order_by(ApplicationRequirement.sort_order)
    ).all()
    activities = db.scalars(
        select(ApplicationActivity)
        .where(
            ApplicationActivity.application_id == application.id,
            ApplicationActivity.tenant_id == principal.tenant_id,
        )
        .order_by(ApplicationActivity.occurred_at.desc())
    ).all()
    return {
        **ApplicationOut.model_validate(application).model_dump(mode="json"),
        "company_name": company.name,
        "opportunity": (
            OpportunityOut.model_validate(opportunity).model_dump(mode="json")
            if opportunity
            else None
        ),
        "requirements": [
            {
                "id": str(item.id),
                "title": item.title,
                "description": item.description,
                "category": item.category,
                "status": item.status,
                "is_hard_gate": item.is_hard_gate,
                "sort_order": item.sort_order,
            }
            for item in requirements
        ],
        "activities": [
            {
                "id": str(item.id),
                "action": item.action,
                "summary": item.summary,
                "occurred_at": item.occurred_at.isoformat(),
            }
            for item in activities
        ],
    }


@router.patch("/applications/{application_id}/status", response_model=ApplicationOut)
def update_application_status(
    application_id: UUID,
    payload: ApplicationStatusUpdate,
    principal: Principal = Depends(write_principal),
    db: Session = Depends(get_db),
):
    application = require_tenant_resource(
        db, Application, application_id, principal.tenant_id, "Application"
    )
    allowed = APPLICATION_TRANSITIONS.get(application.status, set())
    if payload.status not in allowed:
        raise HTTPException(
            status_code=409,
            detail=f"Application cannot transition from {application.status} to {payload.status}",
        )
    previous = application.status
    application.status = payload.status
    progress_by_status = {
        "draft": 0,
        "preparing": 20,
        "review": 70,
        "revision_requested": 60,
        "approved": 90,
        "submitted": 95,
        "completed": 100,
        "cancelled": application.progress,
    }
    application.progress = progress_by_status[payload.status]
    db.add(
        ApplicationActivity(
            tenant_id=principal.tenant_id,
            application_id=application.id,
            actor_user_id=principal.user.id,
            action="status_changed",
            summary=f"状态由 {previous} 更新为 {payload.status}",
            metadata_json={"reason": payload.reason} if payload.reason else {},
        )
    )
    db.commit()
    db.refresh(application)
    return application


@router.patch(
    "/applications/{application_id}/requirements/{requirement_id}",
    status_code=204,
)
def update_requirement_status(
    application_id: UUID,
    requirement_id: UUID,
    payload: RequirementStatusUpdate,
    principal: Principal = Depends(write_principal),
    db: Session = Depends(get_db),
) -> None:
    require_tenant_resource(
        db, Application, application_id, principal.tenant_id, "Application"
    )
    requirement = db.scalar(
        select(ApplicationRequirement).where(
            ApplicationRequirement.id == requirement_id,
            ApplicationRequirement.application_id == application_id,
            ApplicationRequirement.tenant_id == principal.tenant_id,
        )
    )
    if not requirement:
        raise HTTPException(status_code=404, detail="Requirement not found")
    requirement.status = payload.status
    db.add(
        ApplicationActivity(
            tenant_id=principal.tenant_id,
            application_id=application_id,
            actor_user_id=principal.user.id,
            action="requirement_updated",
            summary=f"材料“{requirement.title}”更新为 {payload.status}",
            metadata_json={"requirement_id": str(requirement.id)},
        )
    )
    db.commit()
