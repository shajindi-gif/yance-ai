import re
import secrets
import time
from collections import defaultdict

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import Principal, get_principal
from app.core.config import settings
from app.core.db import get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.models.models import AnalyticsEvent, Company, Membership, Tenant, User, UserRole
from app.schemas.schemas import BootstrapRequest, RegisterRequest, Token, UserOut
from app.services.company_profiles import create_company_profile

router = APIRouter(prefix="/auth", tags=["auth"])


# ── 简单 IP 限流（内存，重启重置；商业上线前换 Redis）────────
_register_rate: dict[str, list[float]] = defaultdict(list)
_RATE_LIMIT_PER_HOUR = 5


def _check_rate_limit(client_ip: str) -> None:
    now = time.time()
    window = 3600
    _register_rate[client_ip] = [t for t in _register_rate[client_ip] if now - t < window]
    if len(_register_rate[client_ip]) >= _RATE_LIMIT_PER_HOUR:
        raise HTTPException(status_code=429, detail="注册过于频繁，请稍后再试")
    _register_rate[client_ip].append(now)


def _make_slug(company_name: str) -> str:
    """从公司名生成 slug：保留字母数字，中文用 pinyin 占位，长度不足则补随机码"""
    # 只保留 a-z0-9 与 -，其余字符丢弃；中文保留为占位符后丢弃
    ascii_part = re.sub(r"[^a-z0-9]", "", company_name.lower())
    if len(ascii_part) < 3:
        ascii_part = "org"
    return f"{ascii_part[:30]}-{secrets.token_hex(3)}"


def create_tenant_and_owner(payload: BootstrapRequest, db: Session) -> Token:
    tenant = Tenant(name=payload.tenant_name, slug=payload.tenant_slug)
    db.add(tenant)
    db.flush()
    owner = User(
        tenant_id=tenant.id,
        email=str(payload.owner_email).lower(),
        full_name=payload.owner_name,
        password_hash=hash_password(payload.owner_password),
        role=UserRole.owner,
    )
    db.add(owner)
    db.flush()
    db.add(
        Membership(
            tenant_id=tenant.id,
            user_id=owner.id,
            role=UserRole.owner,
            status="active",
        )
    )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="Tenant slug or owner email already exists"
        ) from exc
    return Token(
        access_token=create_access_token(
            user_id=owner.id, tenant_id=tenant.id, role=owner.role.value
        )
    )


@router.post("/bootstrap", response_model=Token, status_code=201)
def bootstrap(
    payload: BootstrapRequest,
    db: Session = Depends(get_db),
    x_bootstrap_token: str = Header(alias="X-Bootstrap-Token"),
) -> Token:
    if not secrets.compare_digest(x_bootstrap_token, settings.bootstrap_token):
        raise HTTPException(status_code=403, detail="Invalid bootstrap token")
    if db.scalar(select(func.count()).select_from(Tenant)):
        raise HTTPException(status_code=409, detail="System has already been bootstrapped")
    return create_tenant_and_owner(payload, db)


@router.post("/provision-tenant", response_model=Token, status_code=201)
def provision_tenant(
    payload: BootstrapRequest,
    db: Session = Depends(get_db),
    x_tenant_provisioning_token: str = Header(alias="X-Tenant-Provisioning-Token"),
) -> Token:
    """Controlled customer onboarding; call only from a trusted admin workflow."""
    if not secrets.compare_digest(x_tenant_provisioning_token, settings.tenant_provisioning_token):
        raise HTTPException(status_code=403, detail="Invalid tenant provisioning token")
    return create_tenant_and_owner(payload, db)


@router.post("/register", response_model=Token, status_code=201)
def register(
    request: Request,
    payload: RegisterRequest,
    db: Session = Depends(get_db),
) -> Token:
    """Public self-service registration: creates tenant + owner + default company."""
    client_ip = request.client.host if request.client else "unknown"
    _check_rate_limit(client_ip)

    # Check email uniqueness across all users
    existing_user = db.scalar(select(User).where(User.email == str(payload.owner_email).lower()))
    if existing_user:
        raise HTTPException(status_code=409, detail="该邮箱已注册，请直接登录")

    # Create tenant with auto-generated slug
    slug = _make_slug(payload.company_name)
    tenant = Tenant(name=payload.company_name, slug=slug)
    db.add(tenant)
    db.flush()

    # Create owner user
    owner = User(
        tenant_id=tenant.id,
        email=str(payload.owner_email).lower(),
        full_name=payload.owner_name,
        password_hash=hash_password(payload.owner_password),
        role=UserRole.owner,
    )
    db.add(owner)
    db.flush()
    db.add(
        Membership(
            tenant_id=tenant.id,
            user_id=owner.id,
            role=UserRole.owner,
            status="active",
        )
    )

    # Create default company so the user can immediately generate a match report
    company = Company(
        tenant_id=tenant.id,
        name=payload.company_name,
        industry=payload.industry,
        province=payload.province,
        city=payload.city,
    )
    db.add(company)
    db.flush()
    create_company_profile(db, company)
    db.add_all(
        [
            AnalyticsEvent(
                tenant_id=tenant.id,
                user_id=owner.id,
                name="signup_completed",
                properties={},
            ),
            AnalyticsEvent(
                tenant_id=tenant.id,
                user_id=owner.id,
                name="company_created",
                properties={"company_id": str(company.id)},
            ),
        ]
    )

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="注册失败，请重试") from exc

    return Token(
        access_token=create_access_token(
            user_id=owner.id, tenant_id=tenant.id, role=owner.role.value
        )
    )


@router.post("/login", response_model=Token)
def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
    x_tenant_slug: str | None = Header(default=None, alias="X-Tenant-Slug"),
) -> Token:
    query = (
        select(User)
        .join(Tenant, Tenant.id == User.tenant_id)
        .where(
            User.email == form.username.lower(),
            User.is_active.is_(True),
            Tenant.is_active.is_(True),
        )
    )
    if x_tenant_slug:
        query = query.where(Tenant.slug == x_tenant_slug)
    users = db.scalars(query).all()
    if len(users) > 1 and not x_tenant_slug:
        raise HTTPException(status_code=400, detail="X-Tenant-Slug is required for this email")
    user = next(
        (
            candidate
            for candidate in users
            if verify_password(form.password, candidate.password_hash)
        ),
        None,
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Token(
        access_token=create_access_token(
            user_id=user.id, tenant_id=user.tenant_id, role=user.role.value
        )
    )


@router.get("/me", response_model=UserOut)
def me(principal: Principal = Depends(get_principal)) -> User:
    return principal.user
