"""Verified phone identity; never infer tenant IDs or merge accounts by supplied email."""

import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import Principal, get_principal
from app.api.routes.auth import _make_slug
from app.core.config import settings
from app.core.db import get_db
from app.core.security import create_access_token, hash_password
from app.models.models import Company, Membership, SmsCode, Tenant, User, UserRole, now_utc
from app.schemas.schemas import Token
from app.services.analytics.events import record_event
from app.services.auth_rate_limit import _upsert_hit
from app.services.company_profiles import create_company_profile
from app.services.sms import (
    SmsDeliveryError,
    digest_code,
    is_sms_configured,
    normalize_phone,
    send_sms,
)

router = APIRouter(prefix="/auth/sms", tags=["auth"])


class SmsRequest(BaseModel):
    phone: str = Field(max_length=20)

    @field_validator("phone")
    @classmethod
    def phone_format(cls, value):
        return normalize_phone(value)


class SmsVerify(SmsRequest):
    code: str = Field(pattern=r"^[0-9]{6}$")
    owner_name: str | None = Field(default=None, min_length=2, max_length=160)
    company_name: str | None = Field(default=None, min_length=2, max_length=160)
    agreed_terms_version: str | None = Field(default=None, max_length=40)


def enabled():
    if not is_sms_configured():
        raise HTTPException(503, "短信登录暂未开通，请使用邮箱")


def as_utc(value):
    return value.astimezone(UTC) if value.tzinfo else value.replace(tzinfo=UTC)


def lock_phone(db, phone):
    db.execute(select(func.pg_advisory_xact_lock(func.hashtextextended("sms:" + phone, 0))))


def jwt_user(principal: Principal = Depends(get_principal)):
    if principal.auth_kind != "jwt":
        raise HTTPException(403, "请登录账号后绑定手机号")
    return principal


def issue(db, request, phone, purpose):
    enabled()
    # Persist attempted-send budgets before external I/O, including rejected/time-out sends.
    # No unbounded failure retry loophole. Keys contain HMACs, never raw phone/IP.
    ip = request.client.host if request.client else "unknown"
    budgets = [
        ("ip:" + digest_code(ip, "limit", ""), 10, 3600),
        ("phone:" + digest_code(phone, "limit", ""), 5, 3600),
        ("all:" + now_utc().strftime("%Y-%m-%d"), settings.sms_daily_limit, 86400),
    ]
    for key, limit, window in budgets:
        if _upsert_hit(db, "sms:" + key, window, limit) is None:
            raise HTTPException(
                429, "短信请求过于频繁，请稍后重试", headers={"Retry-After": "3600"}
            )
    lock_phone(db, phone)
    now = now_utc()
    latest = db.scalar(
        select(SmsCode).where(SmsCode.phone == phone).order_by(SmsCode.created_at.desc()).limit(1)
    )
    if latest and (now - as_utc(latest.created_at)).total_seconds() < 60:
        raise HTTPException(429, "请等待60秒后再获取验证码", headers={"Retry-After": "60"})
    code = f"{secrets.randbelow(1_000_000):06d}"
    row = SmsCode(
        phone=phone,
        purpose=purpose,
        code_hash=digest_code(phone, purpose, code),
        expires_at=now + timedelta(minutes=5),
        state="pending",
    )
    db.add(row)
    db.commit()  # a crash leaves a non-verifiable pending code and still consumes budget
    try:
        send_sms(phone, code)
    except SmsDeliveryError:
        row.state = "uncertain"
        db.commit()
        raise HTTPException(503, "短信发送失败或结果未确认，请稍后重试") from None
    row.state = "accepted"
    db.commit()
    return {"message": "短信服务已受理，请查收验证码，5分钟内有效", "retry_after": 60}


def validate(db, phone, purpose, code):
    enabled()
    lock_phone(db, phone)
    row = db.scalar(
        select(SmsCode)
        .where(SmsCode.phone == phone, SmsCode.purpose == purpose)
        .order_by(SmsCode.created_at.desc())
        .limit(1)
        .with_for_update()
    )
    if not row or row.used_at or row.state != "accepted":
        raise HTTPException(401, "验证码无效，请重新获取")
    if as_utc(row.expires_at) <= now_utc():
        raise HTTPException(401, "验证码已过期，请重新获取")
    if row.attempts >= 5:
        raise HTTPException(429, "验证码错误次数过多，请重新获取")
    if not secrets.compare_digest(row.code_hash, digest_code(phone, purpose, code)):
        row.attempts += 1
        db.commit()
        raise HTTPException(401, "验证码不正确")
    return row


@router.post("/send", status_code=202)
def send(payload: SmsRequest, request: Request, db: Session = Depends(get_db)):
    return issue(db, request, payload.phone, "login")


@router.post("/verify", response_model=Token)
def verify(payload: SmsVerify, request: Request, db: Session = Depends(get_db)):
    enabled()
    ip = request.client.host if request.client else "unknown"
    if _upsert_hit(db, "sms:verify:" + digest_code(ip, "limit", ""), 900, 30) is None:
        raise HTTPException(429, "验证请求过于频繁，请稍后重试")
    row = validate(db, payload.phone, "login", payload.code)
    user = db.scalar(select(User).where(User.phone == payload.phone))
    if user is None:
        if not (
            payload.owner_name
            and payload.owner_name.strip()
            and payload.company_name
            and payload.company_name.strip()
            and payload.agreed_terms_version in {"2026-10-29", "2026-10-30"}
        ):
            # Only after proof of phone control; keep code for the profile step.
            raise HTTPException(400, "首次手机登录需填写姓名、企业名称并同意服务条款与隐私政策")
        tenant = Tenant(name=payload.company_name.strip(), slug=_make_slug(payload.company_name))
        db.add(tenant)
        db.flush()
        user = User(
            tenant_id=tenant.id,
            phone=payload.phone,
            email=None,
            full_name=payload.owner_name.strip(),
            password_hash=hash_password(secrets.token_urlsafe(32)),
            role=UserRole.owner,
        )
        db.add(user)
        db.flush()
        db.add(Membership(tenant_id=tenant.id, user_id=user.id, role=user.role, status="active"))
        company = Company(tenant_id=tenant.id, name=payload.company_name.strip())
        db.add(company)
        db.flush()
        create_company_profile(db, company)
        record_event(
            db,
            tenant_id=tenant.id,
            user_id=user.id,
            name="signup_completed",
            event_key=f"signup_completed:{tenant.id}",
            properties={"method": "sms_code"},
        )
        record_event(
            db,
            tenant_id=tenant.id,
            user_id=user.id,
            name="terms_accepted",
            event_key=f"terms_accepted:{user.id}",
            properties={
                "terms_version": payload.agreed_terms_version,
                "documents": ["terms", "privacy"],
                "accepted_at": datetime.now(UTC).isoformat(),
            },
        )
    tenant = db.get(Tenant, user.tenant_id)
    member = db.scalar(
        select(Membership).where(
            Membership.user_id == user.id,
            Membership.tenant_id == user.tenant_id,
            Membership.status == "active",
        )
    )
    if not user.is_active or not tenant or not tenant.is_active or not member:
        raise HTTPException(403, "账号或工作区不可用，请联系管理员")
    row.used_at = now_utc()
    record_event(db, tenant_id=user.tenant_id, user_id=user.id, name="login_completed")
    db.commit()  # OTP consumption and provisioning share one transaction
    return Token(
        access_token=create_access_token(
            user_id=user.id,
            tenant_id=user.tenant_id,
            role=user.role.value,
            auth_version=user.auth_version,
        )
    )


@router.post("/bind/send", status_code=202)
def bind_send(
    payload: SmsRequest,
    request: Request,
    principal: Principal = Depends(jwt_user),
    db: Session = Depends(get_db),
):
    return issue(db, request, payload.phone, f"bind:{principal.user.id}")


@router.post("/bind")
def bind(
    payload: SmsVerify, principal: Principal = Depends(jwt_user), db: Session = Depends(get_db)
):
    row = validate(db, payload.phone, f"bind:{principal.user.id}", payload.code)
    # Lock user too: simultaneous binding of different phones cannot silently replace one.
    user = db.scalar(
        select(User)
        .where(User.id == principal.user.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if user.phone and user.phone != payload.phone:
        raise HTTPException(409, "账号已绑定其他手机号，本轮不支持自助更换")
    owner = db.scalar(select(User).where(User.phone == payload.phone))
    if owner and owner.id != user.id:
        raise HTTPException(409, "该手机号已关联其他账号，不能自动合并")
    user.phone = payload.phone
    row.used_at = now_utc()
    db.commit()
    return {"message": "手机号绑定成功，可用于短信登录"}
