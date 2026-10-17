import re
import secrets
import time
from datetime import UTC, datetime

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import Principal, get_principal
from app.core.config import settings
from app.core.db import get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.models.models import Company, Membership, Tenant, User, UserRole
from app.schemas.schemas import (
    BootstrapRequest,
    EmailCodeSendRequest,
    EmailCodeVerifyRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    RegisterRequest,
    Token,
    UserOut,
)
from app.services.analytics.events import record_event
from app.services.auth_rate_limit import (
    login_failure,
    login_is_limited,
    login_success,
    register_attempt,
)
from app.services.company_profiles import create_company_profile
from app.services.email_code import (
    EmailSendError,
    RateLimited,
    check_send_limits,
    consume_code,
    consume_login_code,
    send_login_code,
    send_reset_code,
)
from app.services.notifications.email import is_email_configured

router = APIRouter(prefix="/auth", tags=["auth"])
logger = structlog.get_logger()


# ── 限流：DB 计数（跨 4 个 uvicorn worker 共享，重启不清零）────────
# 见 app/services/auth_rate_limit.py（S1 修复：原内存计数在多 worker 下失效）


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
    client_ip = _client_ip(request)
    if not register_attempt(db, client_ip):
        raise HTTPException(status_code=429, detail="注册过于频繁，请稍后再试")

    # Require explicit consent to the current terms/privacy policy version.
    if not payload.agreed_terms_version:
        raise HTTPException(
            status_code=400,
            detail="请先阅读并同意《服务条款》与《隐私政策》后再注册",
        )

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
    record_event(
        db,
        tenant_id=tenant.id,
        user_id=owner.id,
        name="signup_completed",
        event_key=f"signup_completed:{tenant.id}",
    )
    record_event(
        db,
        tenant_id=tenant.id,
        user_id=owner.id,
        name="terms_accepted",
        event_key=f"terms_accepted:{owner.id}",
        properties={
            "terms_version": payload.agreed_terms_version,
            "documents": ["terms", "privacy"],
            "accepted_at": datetime.now(UTC).isoformat(),
        },
    )
    record_event(
        db,
        tenant_id=tenant.id,
        user_id=owner.id,
        name="company_created",
        event_key=f"company_created:{company.id}",
        properties={"company_id": str(company.id)},
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
    request: Request,
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
    x_tenant_slug: str | None = Header(default=None, alias="X-Tenant-Slug"),
) -> Token:
    client_ip = _client_ip(request)
    if login_is_limited(db, client_ip):
        raise HTTPException(
            status_code=429, detail="登录失败次数过多，请 15 分钟后再试"
        )
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
        login_failure(db, client_ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    login_success(db, client_ip)
    record_event(
        db,
        tenant_id=user.tenant_id,
        user_id=user.id,
        name="login_completed",
    )
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        logger.warning("analytics_event_write_failed", event_name="login_completed")
    return Token(
        access_token=create_access_token(
            user_id=user.id, tenant_id=user.tenant_id, role=user.role.value
        )
    )


# ── 邮箱验证码登录（无需密码，自动建号）────────────────────────


def _client_ip(request: Request) -> str:
    """Best-effort client IP; Cloudflare Tunnel forwards the real IP via XFF."""
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.get("/config")
def auth_config() -> dict:
    """Public capability flags so the login page can hide unavailable tabs."""
    return {"email_login_enabled": is_email_configured()}


@router.post("/email/send", status_code=202)
def email_code_send(
    request: Request,
    payload: EmailCodeSendRequest,
    db: Session = Depends(get_db),
) -> dict:
    """Send a 6-digit login code. Unknown emails are provisioned at verify time.

    Deliberately anti-enumeration: the response never reveals whether the
    address already has an account.
    """
    if not is_email_configured():
        raise HTTPException(
            status_code=503,
            detail="邮箱验证码通道尚未开通，请使用密码登录或注册",
        )
    email = str(payload.email).lower()
    client_ip = _client_ip(request)
    try:
        check_send_limits(db, email, client_ip)
    except RateLimited as rl:
        raise HTTPException(
            status_code=429,
            detail=f"验证码发送过于频繁，请 {rl.retry_after} 秒后重试",
        ) from rl
    try:
        send_login_code(db, email, client_ip)
    except EmailSendError as exc:
        raise HTTPException(
            status_code=502, detail="验证码邮件发送失败，请稍后重试"
        ) from exc
    return {"message": "验证码已发送，请查收邮箱（10 分钟内有效）"}


@router.post("/email/verify", response_model=Token)
def email_code_verify(
    payload: EmailCodeVerifyRequest,
    db: Session = Depends(get_db),
) -> Token:
    """Verify a login code; existing users log in, new emails auto-register."""
    if not is_email_configured():
        raise HTTPException(
            status_code=503, detail="邮箱验证码通道尚未开通，请使用密码登录"
        )
    email = str(payload.email).lower()

    # Resolve the account BEFORE consuming the code so a missing-field 400
    # does not burn a valid verification code. Counts every user (active or
    # not): email is treated as globally unique for self-service registration.
    users = db.scalars(select(User).where(User.email == email)).all()
    provisioning = len(users) == 0
    if len(users) > 1:
        # Same email across multiple workspaces (admin-provisioned): password
        # login with X-Tenant-Slug is the only unambiguous path.
        raise HTTPException(
            status_code=400,
            detail="该邮箱关联多个工作区，请使用密码登录",
        )
    if provisioning and not (
        payload.owner_name and payload.company_name and payload.agreed_terms_version
    ):
        raise HTTPException(
            status_code=400,
            detail="首次登录需填写姓名、企业名称并同意《服务条款》与《隐私政策》",
        )

    result = consume_login_code(db, email, payload.code)
    if result == "expired":
        raise HTTPException(status_code=401, detail="验证码已过期，请重新获取")
    if result == "too_many":
        raise HTTPException(status_code=429, detail="验证码错误次数过多，请重新获取")
    if result != "ok":
        raise HTTPException(status_code=401, detail="验证码不正确")

    if not provisioning:
        user = users[0]
        if not user.is_active:
            raise HTTPException(status_code=403, detail="该账号已被停用，请联系管理员")
        tenant = db.get(Tenant, user.tenant_id)
        if not tenant or not tenant.is_active:
            raise HTTPException(status_code=403, detail="该工作区已被停用，请联系管理员")
        record_event(
            db, tenant_id=user.tenant_id, user_id=user.id, name="login_completed"
        )
        try:
            db.commit()
        except SQLAlchemyError:
            db.rollback()
            logger.warning("analytics_event_write_failed", event_name="login_completed")
        return Token(
            access_token=create_access_token(
                user_id=user.id, tenant_id=user.tenant_id, role=user.role.value
            )
        )

    # ── Auto-provision: tenant + owner + default company (mirrors /register) ──
    slug = _make_slug(payload.company_name or "")
    tenant = Tenant(name=payload.company_name, slug=slug)
    db.add(tenant)
    db.flush()
    owner = User(
        tenant_id=tenant.id,
        email=email,
        full_name=payload.owner_name,
        # Passwordless account: store a random unusable hash (column is NOT NULL).
        password_hash=hash_password(secrets.token_urlsafe(24)),
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
    company = Company(tenant_id=tenant.id, name=payload.company_name)
    db.add(company)
    db.flush()
    create_company_profile(db, company)
    record_event(
        db,
        tenant_id=tenant.id,
        user_id=owner.id,
        name="signup_completed",
        event_key=f"signup_completed:{tenant.id}",
        properties={"method": "email_code"},
    )
    record_event(
        db,
        tenant_id=tenant.id,
        user_id=owner.id,
        name="terms_accepted",
        event_key=f"terms_accepted:{owner.id}",
        properties={
            "terms_version": payload.agreed_terms_version,
            "documents": ["terms", "privacy"],
            "accepted_at": datetime.now(UTC).isoformat(),
        },
    )
    record_event(
        db,
        tenant_id=tenant.id,
        user_id=owner.id,
        name="company_created",
        event_key=f"company_created:{company.id}",
        properties={"company_id": str(company.id)},
    )
    record_event(
        db, tenant_id=tenant.id, user_id=owner.id, name="login_completed"
    )
    try:
        db.commit()
    except IntegrityError as exc:
        # Lost a race against a concurrent verify for the same email.
        db.rollback()
        existing = db.scalars(
            select(User).where(User.email == email, User.is_active.is_(True))
        ).all()
        if len(existing) == 1:
            user = existing[0]
            return Token(
                access_token=create_access_token(
                    user_id=user.id, tenant_id=user.tenant_id, role=user.role.value
                )
            )
        raise HTTPException(status_code=409, detail="注册失败，请重试") from exc

    return Token(
        access_token=create_access_token(
            user_id=owner.id, tenant_id=tenant.id, role=owner.role.value
        )
    )


# ── 找回密码（邮箱验证码重置密码）───────────────────────────────────


@router.post("/password/reset/request", status_code=202)
def password_reset_request(
    request: Request,
    payload: PasswordResetRequest,
    db: Session = Depends(get_db),
) -> dict:
    """Send a reset code if the email has an account; identical reply either way.

    Anti-enumeration: unknown emails get the same 202 but no email is sent.
    """
    if not is_email_configured():
        raise HTTPException(
            status_code=503,
            detail="邮箱验证码通道尚未开通，请联系管理员协助重置密码",
        )
    email = str(payload.email).lower()
    client_ip = _client_ip(request)
    has_account = db.scalar(select(func.count()).select_from(User).where(User.email == email))
    if has_account:
        try:
            check_send_limits(db, email, client_ip)
        except RateLimited as rl:
            raise HTTPException(
                status_code=429,
                detail=f"验证码发送过于频繁，请 {rl.retry_after} 秒后重试",
            ) from rl
        try:
            send_reset_code(db, email, client_ip)
        except EmailSendError as exc:
            raise HTTPException(
                status_code=502, detail="重置邮件发送失败，请稍后重试"
            ) from exc
    return {"message": "如果该邮箱已注册，重置验证码已发送（10 分钟内有效）"}


@router.post("/password/reset/confirm", response_model=Token)
def password_reset_confirm(
    payload: PasswordResetConfirm,
    db: Session = Depends(get_db),
) -> Token:
    """Consume a reset code, set the new password, and log the user in."""
    if not is_email_configured():
        raise HTTPException(
            status_code=503, detail="邮箱验证码通道尚未开通，请联系管理员协助重置密码"
        )
    email = str(payload.email).lower()
    users = db.scalars(select(User).where(User.email == email)).all()
    if len(users) > 1:
        raise HTTPException(
            status_code=400,
            detail="该邮箱关联多个工作区，请联系管理员协助重置密码",
        )
    if not users:
        raise HTTPException(status_code=400, detail="该邮箱未注册，请先注册账号")

    result = consume_code(db, email, payload.code, purpose="reset")
    if result == "expired":
        raise HTTPException(status_code=401, detail="验证码已过期，请重新获取")
    if result == "too_many":
        raise HTTPException(status_code=429, detail="验证码错误次数过多，请重新获取")
    if result != "ok":
        raise HTTPException(status_code=401, detail="验证码不正确")

    user = users[0]
    if not user.is_active:
        raise HTTPException(status_code=403, detail="该账号已被停用，请联系管理员")
    user.password_hash = hash_password(payload.new_password)
    record_event(
        db,
        tenant_id=user.tenant_id,
        user_id=user.id,
        name="password_reset",
        event_key=f"password_reset:{user.id}:{int(time.time())}",
    )
    try:
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="密码重置失败，请重试") from exc
    return Token(
        access_token=create_access_token(
            user_id=user.id, tenant_id=user.tenant_id, role=user.role.value
        )
    )


@router.get("/me", response_model=UserOut)
def me(principal: Principal = Depends(get_principal)) -> User:
    return principal.user
