"""Funding OS APIs: notifications, AI consultant, funding command center, milestones."""

from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import Principal, get_principal, require_roles
from app.core.db import get_db
from app.models.models import (
    Application,
    Company,
    CompanyFact,
    CompanyProfile,
    CompanyProfileVersion,
    Milestone,
    Notification,
    Opportunity,
    Policy,
    UserRole,
)
from app.schemas.schemas import ORMModel
from app.services.consultant.router import answer as consultant_answer
from app.services.notifications.deadlines import scan_deadlines

write_principal = require_roles(UserRole.owner, UserRole.admin, UserRole.member)

router = APIRouter(tags=["funding-os"])


# ── schemas ────────────────────────────────────────────────────────────
class NotificationOut(ORMModel):
    id: UUID
    kind: str
    severity: str
    title: str
    body: str | None
    entity_type: str | None
    entity_id: str | None
    read_at: datetime | None
    created_at: datetime


class MilestoneCreate(BaseModel):
    title: str = Field(min_length=2, max_length=300)
    description: str | None = Field(default=None, max_length=4000)
    kind: Literal["preparation", "acceptance"] = "preparation"
    due_at: datetime | None = None
    owner_user_id: UUID | None = None


class MilestoneUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=300)
    description: str | None = Field(default=None, max_length=4000)
    due_at: datetime | None = None
    status: Literal["todo", "doing", "done", "blocked"] | None = None
    completion_note: str | None = Field(default=None, max_length=2000)
    owner_user_id: UUID | None = None


class MilestoneOut(ORMModel):
    id: UUID
    application_id: UUID
    kind: str
    title: str
    description: str | None
    owner_user_id: UUID | None
    due_at: datetime | None
    status: str
    completion_note: str | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ConsultantAsk(BaseModel):
    company_id: UUID
    question: str = Field(min_length=2, max_length=1000)


# ── helpers ────────────────────────────────────────────────────────────
def _get_company(db: Session, principal: Principal, company_id: UUID) -> Company:
    company = db.scalar(
        select(Company).where(Company.id == company_id, Company.tenant_id == principal.tenant_id)
    )
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company


# ── notifications ──────────────────────────────────────────────────────
@router.get("/notifications", response_model=list[NotificationOut])
def list_notifications(
    unread_only: bool = Query(default=False),
    limit: int = Query(default=50, le=200),
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> list[Notification]:
    query = select(Notification).where(Notification.tenant_id == principal.tenant_id)
    if unread_only:
        query = query.where(Notification.read_at.is_(None))
    return list(db.scalars(query.order_by(Notification.created_at.desc()).limit(limit)).all())


@router.get("/notifications/unread-count")
def unread_count(
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> dict:
    count = db.scalar(
        select(func.count())
        .select_from(Notification)
        .where(
            Notification.tenant_id == principal.tenant_id,
            Notification.read_at.is_(None),
        )
    )
    return {"unread": int(count or 0)}


@router.post("/notifications/scan")
def trigger_deadline_scan(
    principal: Principal = Depends(require_roles(UserRole.owner, UserRole.admin)),
    db: Session = Depends(get_db),
) -> dict:
    created = scan_deadlines(db, tenant_id=principal.tenant_id)
    return {"created": created}


@router.post("/notifications/{notification_id}/read", response_model=NotificationOut)
def mark_read(
    notification_id: UUID,
    principal: Principal = Depends(write_principal),
    db: Session = Depends(get_db),
) -> Notification:
    notification = db.scalar(
        select(Notification).where(
            Notification.id == notification_id, Notification.tenant_id == principal.tenant_id
        )
    )
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    if notification.read_at is None:
        notification.read_at = datetime.now(UTC)
        db.commit()
        db.refresh(notification)
    return notification


@router.post("/notifications/read-all")
def mark_all_read(
    principal: Principal = Depends(write_principal),
    db: Session = Depends(get_db),
) -> dict:
    rows = db.scalars(
        select(Notification).where(
            Notification.tenant_id == principal.tenant_id, Notification.read_at.is_(None)
        )
    ).all()
    now = datetime.now(UTC)
    for row in rows:
        row.read_at = now
    db.commit()
    return {"updated": len(rows)}


# ── AI consultant ──────────────────────────────────────────────────────
@router.post("/consultant/ask")
def ask_consultant(
    payload: ConsultantAsk,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    company = _get_company(db, principal, payload.company_id)
    result = consultant_answer(db, company=company, question=payload.question)
    result["company_id"] = str(company.id)
    result["asked_at"] = datetime.now(UTC).isoformat()
    return result


# ── funding command center ─────────────────────────────────────────────
@router.get("/funding/summary")
def funding_summary(
    company_id: UUID | None = Query(default=None),
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Aggregated Funding Command Center facts computed from real records only."""
    company_stmt = select(Company).where(Company.tenant_id == principal.tenant_id)
    if company_id:
        company_stmt = company_stmt.where(Company.id == company_id)
    company = db.scalar(company_stmt.order_by(Company.created_at.asc()))
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")

    now = datetime.now(UTC)
    horizon = datetime.fromtimestamp(now.timestamp() + 30 * 86400, tz=UTC)

    opportunities = list(
        db.scalars(
            select(Opportunity).where(Opportunity.company_id == company.id)
        ).all()
    )
    eligible = [o for o in opportunities if o.eligibility_status in {"ELIGIBLE", "POTENTIALLY_ELIGIBLE"}]
    high_match = [o for o in eligible if o.score is not None and float(o.score) >= 70]

    policy_ids = [o.policy_id for o in eligible if o.policy_id]
    funding_max_total = 0.0
    amount_backed = 0
    if policy_ids:
        policies = list(db.scalars(select(Policy).where(Policy.id.in_(policy_ids))).all())
        for policy in policies:
            if policy.funding_amount_max is not None:
                funding_max_total += float(policy.funding_amount_max)
                amount_backed += 1

    applications = list(
        db.scalars(
            select(Application).where(Application.tenant_id == principal.tenant_id)
        ).all()
    )
    active_apps = [a for a in applications if a.status not in {"submitted", "completed", "cancelled"}]
    deadlines_30d = [
        a for a in active_apps if a.due_at and a.due_at.replace(tzinfo=UTC) <= horizon
    ]

    profile = db.scalar(select(CompanyProfile).where(CompanyProfile.company_id == company.id))
    fact_count = 0
    if profile is not None and profile.published_version:
        version = db.scalar(
            select(CompanyProfileVersion).where(
                CompanyProfileVersion.profile_id == profile.id,
                CompanyProfileVersion.version == profile.published_version,
            )
        )
        if version is not None:
            fact_count = int(
                db.scalar(
                    select(func.count())
                    .select_from(CompanyFact)
                    .where(CompanyFact.profile_version_id == version.id)
                )
                or 0
            )
    missing_evidence = max(0, 8 - min(8, fact_count))  # 8 high-value fact slots tracked by consultant

    pipeline: dict[str, int] = {}
    for app_row in applications:
        pipeline[app_row.status] = pipeline.get(app_row.status, 0) + 1

    upcoming_milestones = list(
        db.scalars(
            select(Milestone)
            .where(
                Milestone.tenant_id == principal.tenant_id,
                Milestone.status.notin_(["done"]),
                Milestone.due_at.is_not(None),
            )
            .order_by(Milestone.due_at.asc())
            .limit(8)
        ).all()
    )

    unread = int(
        db.scalar(
            select(func.count())
            .select_from(Notification)
            .where(
                Notification.tenant_id == principal.tenant_id,
                Notification.read_at.is_(None),
            )
        )
        or 0
    )

    recommended = sorted(
        eligible, key=lambda o: (float(o.score) if o.score is not None else 0), reverse=True
    )[:5]

    return {
        "company_id": str(company.id),
        "company_name": company.name,
        "estimated_funding_available_wan": round(funding_max_total, 2),
        "funding_amount_coverage": {
            "eligible": len(eligible),
            "with_official_amount": amount_backed,
        },
        "eligible_count": len(eligible),
        "high_match_count": len(high_match),
        "deadlines_in_30_days": len(deadlines_30d),
        "applications_in_progress": len(active_apps),
        "missing_evidence_count": missing_evidence,
        "profile_completeness": profile.completeness_score if profile else 0,
        "pipeline": pipeline,
        "upcoming_tasks": [
            {
                "id": str(m.id),
                "title": m.title,
                "due_at": m.due_at.isoformat() if m.due_at else None,
                "status": m.status,
                "application_id": str(m.application_id),
            }
            for m in upcoming_milestones
        ],
        "recommended_opportunities": [
            {
                "id": str(o.id),
                "title": o.title,
                "score": float(o.score) if o.score is not None else None,
                "eligibility": o.eligibility_status,
            }
            for o in recommended
        ],
        "unread_notifications": unread,
    }


# ── milestones ─────────────────────────────────────────────────────────
@router.get("/applications/{application_id}/milestones", response_model=list[MilestoneOut])
def list_milestones(
    application_id: UUID,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> list[Milestone]:
    application = db.scalar(
        select(Application).where(
            Application.id == application_id, Application.tenant_id == principal.tenant_id
        )
    )
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    return list(
        db.scalars(
            select(Milestone)
            .where(Milestone.application_id == application_id)
            .order_by(Milestone.due_at.asc().nullslast(), Milestone.created_at.asc())
        ).all()
    )


@router.post(
    "/applications/{application_id}/milestones",
    response_model=MilestoneOut,
    status_code=201,
)
def create_milestone(
    application_id: UUID,
    payload: MilestoneCreate,
    principal: Principal = Depends(write_principal),
    db: Session = Depends(get_db),
) -> Milestone:
    application = db.scalar(
        select(Application).where(
            Application.id == application_id, Application.tenant_id == principal.tenant_id
        )
    )
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    milestone = Milestone(
        tenant_id=principal.tenant_id,
        application_id=application.id,
        title=payload.title.strip(),
        description=payload.description,
        kind=payload.kind,
        due_at=payload.due_at,
        owner_user_id=payload.owner_user_id or principal.user.id,
    )
    db.add(milestone)
    db.commit()
    db.refresh(milestone)
    return milestone


@router.patch("/milestones/{milestone_id}", response_model=MilestoneOut)
def update_milestone(
    milestone_id: UUID,
    payload: MilestoneUpdate,
    principal: Principal = Depends(write_principal),
    db: Session = Depends(get_db),
) -> Milestone:
    milestone = db.scalar(
        select(Milestone).where(
            Milestone.id == milestone_id, Milestone.tenant_id == principal.tenant_id
        )
    )
    if not milestone:
        raise HTTPException(status_code=404, detail="Milestone not found")
    data = payload.model_dump(exclude_unset=True)
    if "status" in data and data["status"] is not None:
        milestone.status = data["status"]
        if data["status"] == "done":
            milestone.completed_at = datetime.now(UTC)
        else:
            milestone.completed_at = None
    for field in ("title", "description", "due_at", "completion_note", "owner_user_id"):
        if field in data:
            setattr(milestone, field, data[field])
    db.commit()
    db.refresh(milestone)
    return milestone


@router.delete("/milestones/{milestone_id}", status_code=204)
def delete_milestone(
    milestone_id: UUID,
    principal: Principal = Depends(require_roles(UserRole.owner, UserRole.admin)),
    db: Session = Depends(get_db),
) -> None:
    milestone = db.scalar(
        select(Milestone).where(
            Milestone.id == milestone_id, Milestone.tenant_id == principal.tenant_id
        )
    )
    if not milestone:
        raise HTTPException(status_code=404, detail="Milestone not found")
    db.delete(milestone)
    db.commit()
