from datetime import UTC, datetime
from typing import Literal
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import Principal, get_principal, require_roles
from app.core.db import get_db
from app.models.models import (
    Application,
    ApplicationActivity,
    ApplicationArtifact,
    ApplicationComment,
    ApplicationDocumentLink,
    ApplicationRequirement,
    Company,
    CompanyProfile,
    CompanyProfileVersion,
    Document,
    EligibilityResult,
    Evidence,
    Opportunity,
    Policy,
    PolicyBenefit,
    PolicyScan,
    RequiredMaterial,
    Task,
    UserRole,
)
from app.schemas.schemas import (
    ApplicationAgentAction,
    ApplicationArtifactEdit,
    ApplicationArtifactReview,
    ApplicationCommentCreate,
    ApplicationCreate,
    ApplicationDocumentLinkCreate,
    ApplicationOut,
    OpportunityOut,
)
from app.services.agents.harness import AgentHarness
from app.services.analytics.events import record_event
from app.services.applications.artifacts import render_artifact
from app.services.applications.workspace import create_artifact, readiness, workspace_records
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
    workflow_run_id: UUID | None
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

STATUS_STAGE = {
    "draft": "草稿",
    "preparing": "材料准备",
    "review": "人工复核",
    "revision_requested": "修改中",
    "approved": "已批准",
    "submitted": "已提交",
    "completed": "已完成",
    "cancelled": "已取消",
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
        workflow_version="policy-scan-v2",
        estimated_price=0,
        payment_status="free",
        progress=0,
        current_stage="排队中",
    )
    db.add(task)
    db.flush()
    scan.task_id = task.id
    AgentHarness().enqueue_policy_scan(
        db,
        scan=scan,
        task=task,
        tenant_id=principal.tenant_id,
        user_id=principal.user.id,
    )
    record_event(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user.id,
        name="policy_scan_started",
        event_key=f"policy_scan_started:{scan.id}",
        properties={
            "scan_id": str(scan.id),
            "company_id": str(company.id),
            "profile_version_id": str(profile_version.id),
        },
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
    eligibility = db.scalar(
        select(EligibilityResult).where(
            EligibilityResult.opportunity_id == opportunity.id,
            EligibilityResult.tenant_id == principal.tenant_id,
        )
    )
    evidence = (
        list(
            db.scalars(
                select(Evidence)
                .where(
                    Evidence.eligibility_result_id == eligibility.id,
                    Evidence.tenant_id == principal.tenant_id,
                )
                .order_by(Evidence.created_at)
            ).all()
        )
        if eligibility
        else []
    )
    materials = (
        list(
            db.scalars(
                select(RequiredMaterial).where(
                    RequiredMaterial.policy_version_id == eligibility.policy_version_id,
                    (RequiredMaterial.tenant_id.is_(None))
                    | (RequiredMaterial.tenant_id == principal.tenant_id),
                )
            ).all()
        )
        if eligibility and eligibility.policy_version_id
        else []
    )
    benefits = (
        list(
            db.scalars(
                select(PolicyBenefit).where(
                    PolicyBenefit.policy_version_id == eligibility.policy_version_id,
                    (PolicyBenefit.tenant_id.is_(None))
                    | (PolicyBenefit.tenant_id == principal.tenant_id),
                )
            ).all()
        )
        if eligibility and eligibility.policy_version_id
        else []
    )
    return {
        **OpportunityOut.model_validate(opportunity).model_dump(mode="json"),
        "policy_content_available": bool(policy and policy.content),
        "eligibility_result": (
            {
                "id": str(eligibility.id),
                "policy_version_id": str(eligibility.policy_version_id)
                if eligibility.policy_version_id
                else None,
                "status": eligibility.status,
                "confidence": float(eligibility.confidence),
                "summary": eligibility.summary,
                "criteria": eligibility.criteria_json,
                "missing_information": eligibility.missing_information_json,
                "engine_version": eligibility.engine_version,
                "review_status": eligibility.review_status,
                "verified_at": eligibility.verified_at,
            }
            if eligibility
            else None
        ),
        "evidence": [
            {
                "id": str(item.id),
                "source_title": item.source_title,
                "source_url": item.source_url,
                "issuer": item.issuer,
                "article": item.article,
                "quote": item.quote,
                "confidence": float(item.confidence),
                "verifier": item.verifier,
                "verified": item.verified,
            }
            for item in evidence
        ],
        "required_materials": [
            {
                "id": str(item.id),
                "name": item.name,
                "description": item.description,
                "is_hard_gate": item.is_hard_gate,
                "article": item.article,
            }
            for item in materials
        ],
        "benefits": [
            {
                "id": str(item.id),
                "benefit_type": item.benefit_type,
                "description": item.description,
                "amount_text": item.amount_text,
                "article": item.article,
            }
            for item in benefits
        ],
    }


@router.post("/opportunities/{opportunity_id}/opened", status_code=204)
def record_opportunity_opened(
    opportunity_id: UUID,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> None:
    opportunity = require_tenant_resource(
        db, Opportunity, opportunity_id, principal.tenant_id, "Opportunity"
    )
    day = datetime.now(UTC).date().isoformat()
    record_event(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user.id,
        name="opportunity_opened",
        event_key=f"opportunity_opened:{principal.user.id}:{opportunity.id}:{day}",
        properties={
            "opportunity_id": str(opportunity.id),
            "company_id": str(opportunity.company_id),
        },
    )
    try:
        db.commit()
    except IntegrityError:
        # Two tabs can record the same daily open at the same time. The event's
        # tenant-scoped key is the source of truth, so a duplicate is success.
        db.rollback()


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
    db.add(
        Task(
            tenant_id=principal.tenant_id,
            user_id=principal.user.id,
            company_id=company.id,
            application_id=application.id,
            task_type="application_workspace",
            title=f"{payload.title} — 材料准备与复核",
            status="draft",
            agent_type="application_agent",
            workflow_version="app-workspace-v1",
            estimated_price=0,
            payment_status="free",
            progress=0,
            current_stage="材料准备",
        )
    )
    if opportunity:
        eligibility = db.scalar(
            select(EligibilityResult).where(
                EligibilityResult.opportunity_id == opportunity.id,
                EligibilityResult.tenant_id == principal.tenant_id,
            )
        )
        structured_materials = (
            list(
                db.scalars(
                    select(RequiredMaterial).where(
                        RequiredMaterial.policy_version_id == eligibility.policy_version_id,
                        (RequiredMaterial.tenant_id.is_(None))
                        | (RequiredMaterial.tenant_id == principal.tenant_id),
                    )
                ).all()
            )
            if eligibility and eligibility.policy_version_id
            else []
        )
        material_rows = [
            {
                "title": item.name,
                "description": item.description or "政策原文列明的申报材料。",
                "is_hard_gate": item.is_hard_gate,
                "source_json": {
                    "opportunity_id": str(opportunity.id),
                    "policy_version_id": str(item.policy_version_id),
                    "article": item.article,
                    "source_quote": item.source_quote,
                },
            }
            for item in structured_materials
        ]
        if not material_rows:
            material_rows = [
                {
                    "title": str(item),
                    "description": "扫描阶段识别的候选材料；尚未与已导入资料完成核验。",
                    "is_hard_gate": False,
                    "source_json": {"opportunity_id": str(opportunity.id)},
                }
                for item in (opportunity.evidence_json or {}).get("missing_materials", [])
            ]
        for position, material in enumerate(material_rows):
            db.add(
                ApplicationRequirement(
                    tenant_id=principal.tenant_id,
                    application_id=application.id,
                    title=material["title"][:300],
                    description=material["description"],
                    category="material",
                    status="missing",
                    is_hard_gate=material["is_hard_gate"],
                    source_json=material["source_json"],
                    sort_order=position,
                )
            )
    db.add(
        ApplicationActivity(
            tenant_id=principal.tenant_id,
            application_id=application.id,
            actor_user_id=principal.user.id,
            action="application_created",
            summary="申报工作区已创建",
            metadata_json={"opportunity_id": str(opportunity.id) if opportunity else None},
        )
    )
    record_event(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user.id,
        name="application_created",
        event_key=f"application_created:{application.id}",
        properties={
            "application_id": str(application.id),
            "company_id": str(company.id),
            "opportunity_id": str(opportunity.id) if opportunity else None,
        },
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
    records = workspace_records(db, application)
    requirements = records["requirements"]
    activities = db.scalars(
        select(ApplicationActivity)
        .where(
            ApplicationActivity.application_id == application.id,
            ApplicationActivity.tenant_id == principal.tenant_id,
        )
        .order_by(ApplicationActivity.occurred_at.desc())
    ).all()
    artifacts = db.scalars(
        select(ApplicationArtifact)
        .where(
            ApplicationArtifact.application_id == application.id,
            ApplicationArtifact.tenant_id == principal.tenant_id,
        )
        .order_by(ApplicationArtifact.version.desc())
    ).all()
    linked_documents = db.execute(
        select(ApplicationDocumentLink, Document)
        .join(Document, Document.id == ApplicationDocumentLink.document_id)
        .where(
            ApplicationDocumentLink.application_id == application.id,
            ApplicationDocumentLink.tenant_id == principal.tenant_id,
            Document.tenant_id == principal.tenant_id,
        )
        .order_by(ApplicationDocumentLink.created_at.desc())
    ).all()
    tasks = db.scalars(
        select(Task)
        .where(
            Task.application_id == application.id,
            Task.tenant_id == principal.tenant_id,
        )
        .order_by(Task.created_at)
    ).all()
    comments = db.scalars(
        select(ApplicationComment)
        .where(
            ApplicationComment.application_id == application.id,
            ApplicationComment.tenant_id == principal.tenant_id,
        )
        .order_by(ApplicationComment.created_at.desc())
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
                "source": item.source_json,
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
        "readiness": readiness(records),
        "evidence": [
            {
                "id": str(item.id),
                "source_title": item.source_title,
                "source_url": item.source_url,
                "issuer": item.issuer,
                "article": item.article,
                "quote": item.quote,
                "confidence": float(item.confidence),
                "verified": item.verified,
            }
            for item in records["evidence"]
        ],
        "documents": [
            {
                "link_id": str(link.id),
                "document_id": str(document.id),
                "requirement_id": str(link.requirement_id) if link.requirement_id else None,
                "filename": document.filename,
                "content_type": document.content_type,
                "status": document.status,
                "ingestion_status": document.ingestion_status,
                "created_at": link.created_at.isoformat(),
            }
            for link, document in linked_documents
        ],
        "generated": [
            {
                "id": str(item.id),
                "artifact_type": item.artifact_type,
                "title": item.title,
                "version": item.version,
                "status": item.status,
                "generation_method": item.generation_method,
                "checksum_sha256": item.checksum_sha256,
                "source_snapshot": item.source_snapshot_json,
                "content": item.content_json,
                "review_note": item.review_note,
                "reviewed_at": item.reviewed_at.isoformat() if item.reviewed_at else None,
                "created_at": item.created_at.isoformat(),
            }
            for item in artifacts
        ],
        "tasks": [
            {
                "id": str(item.id),
                "title": item.title,
                "status": item.status,
                "progress": item.progress,
                "current_stage": item.current_stage,
            }
            for item in tasks
        ],
        "comments": [
            {
                "id": str(item.id),
                "user_id": str(item.user_id) if item.user_id else None,
                "body": item.body,
                "created_at": item.created_at.isoformat(),
            }
            for item in comments
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
    if payload.status == "review":
        records = workspace_records(db, application)
        state = readiness(records)
        latest_artifact = db.scalar(
            select(ApplicationArtifact)
            .where(
                ApplicationArtifact.application_id == application.id,
                ApplicationArtifact.tenant_id == principal.tenant_id,
            )
            .order_by(ApplicationArtifact.version.desc())
        )
        if not latest_artifact:
            raise HTTPException(status_code=409, detail="请先生成申报工作稿再提交复核")
        if latest_artifact.status == "rejected":
            raise HTTPException(status_code=409, detail="最新申报工作稿已退回，请先修复或编辑")
        if not state["can_submit_for_review"]:
            raise HTTPException(status_code=409, detail={"message": "申报尚未就绪", **state})
    if payload.status == "approved":
        if principal.role not in {UserRole.owner, UserRole.admin}:
            raise HTTPException(status_code=403, detail="Only owners and admins can approve")
        latest_artifact = db.scalar(
            select(ApplicationArtifact)
            .where(
                ApplicationArtifact.application_id == application.id,
                ApplicationArtifact.tenant_id == principal.tenant_id,
            )
            .order_by(ApplicationArtifact.version.desc())
        )
        if not latest_artifact or latest_artifact.status != "approved":
            raise HTTPException(status_code=409, detail="最新申报工作稿尚未通过人工复核")
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
    application.review_status = {
        "review": "pending",
        "revision_requested": "changes_requested",
        "approved": "approved",
    }.get(payload.status, application.review_status)
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
    for task in db.scalars(
        select(Task).where(
            Task.application_id == application.id,
            Task.tenant_id == principal.tenant_id,
        )
    ).all():
        task.status = payload.status
        task.progress = application.progress
        task.current_stage = STATUS_STAGE[payload.status]
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
    require_tenant_resource(db, Application, application_id, principal.tenant_id, "Application")
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


@router.post("/applications/{application_id}/documents", status_code=201)
def link_application_document(
    application_id: UUID,
    payload: ApplicationDocumentLinkCreate,
    principal: Principal = Depends(write_principal),
    db: Session = Depends(get_db),
):
    application = require_tenant_resource(
        db, Application, application_id, principal.tenant_id, "Application"
    )
    document = require_tenant_resource(
        db, Document, payload.document_id, principal.tenant_id, "Document"
    )
    if document.company_id and document.company_id != application.company_id:
        raise HTTPException(status_code=409, detail="Document belongs to another company")
    if payload.requirement_id:
        requirement = db.scalar(
            select(ApplicationRequirement).where(
                ApplicationRequirement.id == payload.requirement_id,
                ApplicationRequirement.application_id == application.id,
                ApplicationRequirement.tenant_id == principal.tenant_id,
            )
        )
        if not requirement:
            raise HTTPException(status_code=404, detail="Requirement not found")
    existing = db.scalar(
        select(ApplicationDocumentLink).where(
            ApplicationDocumentLink.application_id == application.id,
            ApplicationDocumentLink.document_id == document.id,
            ApplicationDocumentLink.requirement_id == payload.requirement_id,
            ApplicationDocumentLink.tenant_id == principal.tenant_id,
        )
    )
    if existing:
        return {"id": str(existing.id), "status": existing.status}
    link = ApplicationDocumentLink(
        tenant_id=principal.tenant_id,
        application_id=application.id,
        document_id=document.id,
        requirement_id=payload.requirement_id,
        added_by=principal.user.id,
        status="linked",
    )
    db.add(link)
    db.add(
        ApplicationActivity(
            tenant_id=principal.tenant_id,
            application_id=application.id,
            actor_user_id=principal.user.id,
            action="document_linked",
            summary=f"已关联企业资料“{document.filename}”",
            metadata_json={"document_id": str(document.id)},
        )
    )
    db.commit()
    db.refresh(link)
    return {"id": str(link.id), "status": link.status}


@router.post("/applications/{application_id}/comments", status_code=201)
def create_application_comment(
    application_id: UUID,
    payload: ApplicationCommentCreate,
    principal: Principal = Depends(write_principal),
    db: Session = Depends(get_db),
):
    application = require_tenant_resource(
        db, Application, application_id, principal.tenant_id, "Application"
    )
    body = payload.body.strip()
    if not body:
        raise HTTPException(status_code=422, detail="Comment cannot be blank")
    comment = ApplicationComment(
        tenant_id=principal.tenant_id,
        application_id=application.id,
        user_id=principal.user.id,
        body=body,
    )
    db.add(comment)
    db.add(
        ApplicationActivity(
            tenant_id=principal.tenant_id,
            application_id=application.id,
            actor_user_id=principal.user.id,
            action="comment_added",
            summary="新增申报协作评论",
            metadata_json={"comment_id": str(comment.id)},
        )
    )
    db.commit()
    db.refresh(comment)
    return {"id": str(comment.id), "body": comment.body, "created_at": comment.created_at}


def _artifact_out(item: ApplicationArtifact) -> dict:
    return {
        "id": str(item.id),
        "title": item.title,
        "version": item.version,
        "status": item.status,
        "generation_method": item.generation_method,
        "checksum_sha256": item.checksum_sha256,
        "source_snapshot": item.source_snapshot_json,
        "content": item.content_json,
        "review_note": item.review_note,
        "created_at": item.created_at,
    }


@router.post("/applications/{application_id}/agent-actions")
def application_agent_action(
    application_id: UUID,
    payload: ApplicationAgentAction,
    principal: Principal = Depends(write_principal),
    db: Session = Depends(get_db),
):
    application = require_tenant_resource(
        db, Application, application_id, principal.tenant_id, "Application"
    )
    artifact_write_states = {"draft", "preparing", "revision_requested"}
    if payload.action in {"generate", "fix"} and application.status not in artifact_write_states:
        raise HTTPException(
            status_code=409,
            detail=f"Artifacts cannot be generated while application is {application.status}",
        )
    records = workspace_records(db, application)
    state = readiness(records)
    response: dict = {
        "action": payload.action,
        "engine": "deterministic-evidence-v1",
        "artifact": None,
    }
    if payload.action == "check":
        response.update(
            {"message": "已按材料硬门槛、资格状态与证据完整性完成检查。", "readiness": state}
        )
    elif payload.action in {"ask", "explain"}:
        if payload.action == "ask" and not (payload.question or "").strip():
            raise HTTPException(status_code=422, detail="Question is required for ask")
        eligibility = records["eligibility"]
        response.update(
            {
                "message": eligibility.summary if eligibility else "当前没有可引用的资格判断。",
                "readiness": state,
                "citations": [
                    {
                        "source_title": item.source_title,
                        "article": item.article,
                        "quote": item.quote,
                        "verified": item.verified,
                    }
                    for item in records["evidence"]
                ],
            }
        )
    else:
        latest = db.scalar(
            select(ApplicationArtifact)
            .where(
                ApplicationArtifact.application_id == application.id,
                ApplicationArtifact.tenant_id == principal.tenant_id,
            )
            .order_by(ApplicationArtifact.version.desc())
        )
        if payload.action == "fix" and not latest:
            raise HTTPException(status_code=409, detail="No generated artifact to fix")
        if payload.action == "fix" and (
            application.status != "revision_requested" or latest.status != "rejected"
        ):
            raise HTTPException(
                status_code=409,
                detail="Fix requires a rejected latest artifact and revision_requested status",
            )
        fix_note = (payload.instruction or (latest.review_note if latest else None) or "").strip()
        if payload.action == "fix" and not fix_note:
            raise HTTPException(
                status_code=422, detail="Fix instruction or review note is required"
            )
        try:
            artifact = create_artifact(
                db,
                application,
                user_id=principal.user.id,
                revision_note=fix_note if payload.action == "fix" else None,
            )
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        db.add(
            ApplicationActivity(
                tenant_id=principal.tenant_id,
                application_id=application.id,
                actor_user_id=principal.user.id,
                action="artifact_generated"
                if payload.action == "generate"
                else "artifact_regenerated",
                summary=f"生成申报工作稿 v{artifact.version}",
                metadata_json={
                    "artifact_id": str(artifact.id),
                    "method": artifact.generation_method,
                },
            )
        )
        record_event(
            db,
            tenant_id=principal.tenant_id,
            user_id=principal.user.id,
            name="document_generated",
            event_key=f"document_generated:{artifact.id}",
            properties={
                "application_id": str(application.id),
                "artifact_id": str(artifact.id),
            },
        )
        db.commit()
        db.refresh(artifact)
        response.update(
            {
                "message": f"已生成版本 v{artifact.version}，等待人工复核。",
                "artifact": _artifact_out(artifact),
                "readiness": state,
            }
        )
        return response
    db.add(
        ApplicationActivity(
            tenant_id=principal.tenant_id,
            application_id=application.id,
            actor_user_id=principal.user.id,
            action=f"workspace_{payload.action}",
            summary=f"执行工作区动作：{payload.action}",
            metadata_json={"engine": "deterministic-evidence-v1"},
        )
    )
    db.commit()
    return response


@router.post("/applications/{application_id}/artifacts/{artifact_id}/review")
def review_application_artifact(
    application_id: UUID,
    artifact_id: UUID,
    payload: ApplicationArtifactReview,
    principal: Principal = Depends(require_roles(UserRole.owner, UserRole.admin)),
    db: Session = Depends(get_db),
):
    application = require_tenant_resource(
        db, Application, application_id, principal.tenant_id, "Application"
    )
    artifact = db.scalar(
        select(ApplicationArtifact).where(
            ApplicationArtifact.id == artifact_id,
            ApplicationArtifact.application_id == application.id,
            ApplicationArtifact.tenant_id == principal.tenant_id,
        )
    )
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    if application.status != "review":
        raise HTTPException(status_code=409, detail="Application must be in review")
    if payload.decision == "reject" and not (payload.note or "").strip():
        raise HTTPException(status_code=422, detail="Review note is required when rejecting")
    latest_version = db.scalar(
        select(func.max(ApplicationArtifact.version)).where(
            ApplicationArtifact.application_id == application.id,
            ApplicationArtifact.artifact_type == artifact.artifact_type,
        )
    )
    if artifact.version != latest_version:
        raise HTTPException(
            status_code=409, detail="Only the latest artifact version can be reviewed"
        )
    artifact.status = "approved" if payload.decision == "approve" else "rejected"
    artifact.reviewed_by = principal.user.id
    artifact.reviewed_at = datetime.now(UTC)
    artifact.review_note = payload.note
    application.review_status = (
        "artifact_approved" if payload.decision == "approve" else "changes_requested"
    )
    if payload.decision == "reject":
        application.status = "revision_requested"
        application.progress = 60
        for task in db.scalars(
            select(Task).where(
                Task.application_id == application.id,
                Task.tenant_id == principal.tenant_id,
            )
        ).all():
            task.status = "revision_requested"
            task.progress = 60
            task.current_stage = "修改中"
    db.add(
        ApplicationActivity(
            tenant_id=principal.tenant_id,
            application_id=application.id,
            actor_user_id=principal.user.id,
            action=f"artifact_{artifact.status}",
            summary=f"申报工作稿 v{artifact.version} 已{'批准' if payload.decision == 'approve' else '退回'}",
            metadata_json={"artifact_id": str(artifact.id)},
        )
    )
    db.commit()
    db.refresh(artifact)
    return _artifact_out(artifact)


@router.post("/applications/{application_id}/artifacts/{artifact_id}/edit", status_code=201)
def edit_application_artifact(
    application_id: UUID,
    artifact_id: UUID,
    payload: ApplicationArtifactEdit,
    principal: Principal = Depends(write_principal),
    db: Session = Depends(get_db),
):
    application = require_tenant_resource(
        db, Application, application_id, principal.tenant_id, "Application"
    )
    source = db.scalar(
        select(ApplicationArtifact).where(
            ApplicationArtifact.id == artifact_id,
            ApplicationArtifact.application_id == application.id,
            ApplicationArtifact.tenant_id == principal.tenant_id,
        )
    )
    if not source:
        raise HTTPException(status_code=404, detail="Artifact not found")
    if application.status not in {"draft", "preparing", "revision_requested"}:
        raise HTTPException(
            status_code=409,
            detail=f"Artifacts cannot be edited while application is {application.status}",
        )
    latest_version = db.scalar(
        select(func.max(ApplicationArtifact.version)).where(
            ApplicationArtifact.application_id == application.id,
            ApplicationArtifact.artifact_type == source.artifact_type,
        )
    )
    if source.version != latest_version:
        raise HTTPException(
            status_code=409, detail="Only the latest artifact version can be edited"
        )
    artifact = create_artifact(
        db,
        application,
        user_id=principal.user.id,
        title=payload.title or source.title,
        executive_summary=payload.executive_summary or source.content_json.get("executive_summary"),
        revision_note=f"基于 v{source.version} 人工编辑",
    )
    db.add(
        ApplicationActivity(
            tenant_id=principal.tenant_id,
            application_id=application.id,
            actor_user_id=principal.user.id,
            action="artifact_edited",
            summary=f"人工编辑生成申报工作稿 v{artifact.version}",
            metadata_json={"artifact_id": str(artifact.id), "source_artifact_id": str(source.id)},
        )
    )
    db.commit()
    db.refresh(artifact)
    return _artifact_out(artifact)


@router.get("/applications/{application_id}/artifacts/{artifact_id}/download")
def download_application_artifact(
    application_id: UUID,
    artifact_id: UUID,
    export_format: Literal["docx", "pdf", "xlsx", "json"] = Query(default="docx", alias="format"),
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
):
    application = require_tenant_resource(
        db, Application, application_id, principal.tenant_id, "Application"
    )
    artifact = db.scalar(
        select(ApplicationArtifact).where(
            ApplicationArtifact.id == artifact_id,
            ApplicationArtifact.application_id == application.id,
            ApplicationArtifact.tenant_id == principal.tenant_id,
        )
    )
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    body, media_type, extension = render_artifact(artifact.content_json, export_format)
    filename = quote(f"{artifact.title}_v{artifact.version}.{extension}")
    return Response(
        content=body,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"},
    )
