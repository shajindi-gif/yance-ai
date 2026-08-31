from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import Principal, get_principal, require_roles
from app.core.db import get_db
from app.models.models import Application, Company, Opportunity, Policy, UserRole
from app.schemas.schemas import (
    ApplicationCreate,
    ApplicationOut,
    OpportunityCreate,
    OpportunityOut,
)

router = APIRouter(tags=["opportunity", "application"])
write_principal = require_roles(UserRole.owner, UserRole.admin, UserRole.member)


def require_tenant_resource(db: Session, model, resource_id: UUID, tenant_id: UUID, name: str):
    resource = db.scalar(select(model).where(model.id == resource_id, model.tenant_id == tenant_id))
    if not resource:
        raise HTTPException(status_code=404, detail=f"{name} not found")
    return resource


@router.get("/opportunities", response_model=list[OpportunityOut])
def list_opportunities(
    principal: Principal = Depends(get_principal), db: Session = Depends(get_db)
) -> list[Opportunity]:
    return list(
        db.scalars(select(Opportunity).where(Opportunity.tenant_id == principal.tenant_id)).all()
    )


@router.post("/opportunities", response_model=OpportunityOut, status_code=201)
def create_opportunity(
    payload: OpportunityCreate,
    principal: Principal = Depends(write_principal),
    db: Session = Depends(get_db),
) -> Opportunity:
    require_tenant_resource(db, Company, payload.company_id, principal.tenant_id, "Company")
    if payload.policy_id:
        require_tenant_resource(db, Policy, payload.policy_id, principal.tenant_id, "Policy")
    opportunity = Opportunity(tenant_id=principal.tenant_id, **payload.model_dump())
    db.add(opportunity)
    db.commit()
    db.refresh(opportunity)
    return opportunity


@router.get("/applications", response_model=list[ApplicationOut])
def list_applications(
    principal: Principal = Depends(get_principal), db: Session = Depends(get_db)
) -> list[Application]:
    return list(
        db.scalars(select(Application).where(Application.tenant_id == principal.tenant_id)).all()
    )


@router.post("/applications", response_model=ApplicationOut, status_code=201)
def create_application(
    payload: ApplicationCreate,
    principal: Principal = Depends(write_principal),
    db: Session = Depends(get_db),
) -> Application:
    require_tenant_resource(db, Company, payload.company_id, principal.tenant_id, "Company")
    if payload.opportunity_id:
        require_tenant_resource(
            db, Opportunity, payload.opportunity_id, principal.tenant_id, "Opportunity"
        )
    application = Application(tenant_id=principal.tenant_id, **payload.model_dump())
    db.add(application)
    db.commit()
    db.refresh(application)
    return application
