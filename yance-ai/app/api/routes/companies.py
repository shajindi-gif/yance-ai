from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import Principal, get_principal, require_roles
from app.core.db import get_db
from app.models.models import Company, UserRole
from app.schemas.schemas import CompanyCreate, CompanyOut

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
    company = Company(tenant_id=principal.tenant_id, **payload.model_dump())
    db.add(company)
    db.commit()
    db.refresh(company)
    return company


@router.get("/{company_id}", response_model=CompanyOut)
def get_company(
    company_id: UUID,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> Company:
    company = db.scalar(
        select(Company).where(Company.id == company_id, Company.tenant_id == principal.tenant_id)
    )
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company


@router.put("/{company_id}", response_model=CompanyOut)
def update_company(
    company_id: UUID,
    payload: CompanyCreate,
    principal: Principal = Depends(require_roles(UserRole.owner, UserRole.admin, UserRole.member)),
    db: Session = Depends(get_db),
) -> Company:
    company = db.scalar(
        select(Company).where(Company.id == company_id, Company.tenant_id == principal.tenant_id)
    )
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    for key, value in payload.model_dump().items():
        setattr(company, key, value)
    db.commit()
    db.refresh(company)
    return company


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
