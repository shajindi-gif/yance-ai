from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import Principal, get_principal, require_roles
from app.core.db import get_db
from app.models.models import Company, CompanyProfileVersion, UserRole
from app.schemas.schemas import (
    CompanyCreate,
    CompanyOut,
    CompanyProfileData,
    CompanyProfileOut,
    CompanyProfileVersionOut,
)
from app.services.analytics.events import record_event
from app.services.billing.usage import QuotaExceeded, ensure_capacity
from app.services.company_profiles import (
    create_company_profile,
    get_or_create_company_profile,
    profile_completeness,
    publish_company_profile,
)

router = APIRouter(prefix="/companies", tags=["company"])


@router.get("", response_model=list[CompanyOut])
def list_companies(
    principal: Principal = Depends(get_principal), db: Session = Depends(get_db)
) -> list[Company]:
    return list(db.scalars(select(Company).where(Company.tenant_id == principal.tenant_id)).all())


@router.post("", response_model=CompanyOut, status_code=201)
def create_company(
    payload: CompanyCreate,
    principal: Principal = Depends(require_roles(UserRole.owner, UserRole.admin, UserRole.member)),
    db: Session = Depends(get_db),
) -> Company:
    try:
        ensure_capacity(db, tenant_id=principal.tenant_id, meter="companies")
    except QuotaExceeded as exc:
        raise HTTPException(status_code=429, detail=exc.detail()) from exc
    company = Company(tenant_id=principal.tenant_id, **payload.model_dump())
    db.add(company)
    db.flush()
    create_company_profile(db, company)
    record_event(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user.id,
        name="company_created",
        event_key=f"company_created:{company.id}",
        properties={"company_id": str(company.id)},
    )
    db.commit()
    db.refresh(company)
    return company


def _tenant_company(db: Session, company_id: UUID, tenant_id: UUID) -> Company:
    company = db.scalar(
        select(Company).where(Company.id == company_id, Company.tenant_id == tenant_id)
    )
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company


@router.get("/{company_id}", response_model=CompanyOut)
def get_company(
    company_id: UUID,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> Company:
    return _tenant_company(db, company_id, principal.tenant_id)


@router.put("/{company_id}", response_model=CompanyOut)
def update_company(
    company_id: UUID,
    payload: CompanyCreate,
    principal: Principal = Depends(require_roles(UserRole.owner, UserRole.admin, UserRole.member)),
    db: Session = Depends(get_db),
) -> Company:
    company = _tenant_company(db, company_id, principal.tenant_id)
    for key, value in payload.model_dump().items():
        setattr(company, key, value)
    db.commit()
    db.refresh(company)
    return company


@router.get("/{company_id}/profile", response_model=CompanyProfileOut)
def get_company_profile(
    company_id: UUID,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
):
    company = _tenant_company(db, company_id, principal.tenant_id)
    profile = get_or_create_company_profile(db, company)
    db.commit()
    db.refresh(profile)
    return profile


@router.put("/{company_id}/profile", response_model=CompanyProfileOut)
def update_company_profile(
    company_id: UUID,
    payload: CompanyProfileData,
    principal: Principal = Depends(require_roles(UserRole.owner, UserRole.admin, UserRole.member)),
    db: Session = Depends(get_db),
):
    company = _tenant_company(db, company_id, principal.tenant_id)
    profile = get_or_create_company_profile(db, company)
    draft = payload.model_dump(mode="json")
    profile.draft_json = draft
    profile.completeness_score = profile_completeness(draft)
    profile.status = "draft"
    company.industry = payload.industry
    company.province = payload.province
    company.city = payload.city
    db.commit()
    db.refresh(profile)
    return profile


@router.post(
    "/{company_id}/profile/publish", response_model=CompanyProfileVersionOut, status_code=201
)
def publish_profile(
    company_id: UUID,
    principal: Principal = Depends(require_roles(UserRole.owner, UserRole.admin, UserRole.member)),
    db: Session = Depends(get_db),
):
    company = _tenant_company(db, company_id, principal.tenant_id)
    profile = get_or_create_company_profile(db, company)
    version = publish_company_profile(db, profile, created_by=principal.user.id)
    if version.completeness_score == 100:
        record_event(
            db,
            tenant_id=principal.tenant_id,
            user_id=principal.user.id,
            name="company_profile_completed",
            event_key=f"company_profile_completed:{version.id}",
            properties={
                "company_id": str(company.id),
                "profile_version_id": str(version.id),
            },
        )
    db.commit()
    db.refresh(version)
    return version


@router.get("/{company_id}/profile/versions", response_model=list[CompanyProfileVersionOut])
def list_profile_versions(
    company_id: UUID,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
):
    _tenant_company(db, company_id, principal.tenant_id)
    return list(
        db.scalars(
            select(CompanyProfileVersion)
            .where(
                CompanyProfileVersion.company_id == company_id,
                CompanyProfileVersion.tenant_id == principal.tenant_id,
            )
            .order_by(CompanyProfileVersion.version.desc())
        ).all()
    )


@router.delete("/{company_id}", status_code=204)
def delete_company(
    company_id: UUID,
    principal: Principal = Depends(require_roles(UserRole.owner, UserRole.admin)),
    db: Session = Depends(get_db),
) -> None:
    company = db.scalar(
        select(Company).where(Company.id == company_id, Company.tenant_id == principal.tenant_id)
    )
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    db.delete(company)
    db.commit()
