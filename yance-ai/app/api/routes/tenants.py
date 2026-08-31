from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import Principal, get_principal, require_roles
from app.core.db import get_db
from app.core.security import hash_password
from app.models.models import Tenant, User, UserRole
from app.schemas.schemas import TenantOut, UserCreate, UserOut

router = APIRouter(tags=["tenant", "users"])


@router.get("/tenant", response_model=TenantOut)
def current_tenant(
    principal: Principal = Depends(get_principal), db: Session = Depends(get_db)
) -> Tenant:
    tenant = db.get(Tenant, principal.tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant


@router.get("/users", response_model=list[UserOut])
def list_users(
    principal: Principal = Depends(get_principal), db: Session = Depends(get_db)
) -> list[User]:
    return list(db.scalars(select(User).where(User.tenant_id == principal.tenant_id)).all())


@router.post("/users", response_model=UserOut, status_code=201)
def create_user(
    payload: UserCreate,
    principal: Principal = Depends(require_roles(UserRole.owner, UserRole.admin)),
    db: Session = Depends(get_db),
) -> User:
    user = User(
        tenant_id=principal.tenant_id,
        email=str(payload.email).lower(),
        full_name=payload.full_name,
        password_hash=hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Email already exists in tenant") from exc
    db.refresh(user)
    return user
