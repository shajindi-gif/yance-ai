from dataclasses import dataclass
from uuid import UUID

import jwt
from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.core.security import decode_access_token
from app.models.models import Membership, Tenant, User, UserRole
from app.services.enterprise.api_keys import authenticate_api_key

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.api_v1_prefix}/auth/login", auto_error=False
)


@dataclass(frozen=True)
class Principal:
    user: User
    tenant_id: UUID
    role: UserRole
    auth_kind: str = "jwt"
    scopes: frozenset[str] = frozenset()


def get_principal(
    request: Request,
    token: str | None = Depends(oauth2_scheme),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    db: Session = Depends(get_db),
) -> Principal:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired access token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if x_api_key:
        restricted = (
            f"{settings.api_v1_prefix}/admin",
            f"{settings.api_v1_prefix}/billing",
            f"{settings.api_v1_prefix}/enterprise",
            f"{settings.api_v1_prefix}/payments",
            f"{settings.api_v1_prefix}/orders",
            f"{settings.api_v1_prefix}/invoices",
            f"{settings.api_v1_prefix}/bank",
            f"{settings.api_v1_prefix}/tenant",
            f"{settings.api_v1_prefix}/users",
        )
        if request.url.path.startswith(restricted):
            raise HTTPException(status_code=403, detail="API keys cannot access control-plane routes")
        authenticated = authenticate_api_key(db, x_api_key)
        if not authenticated:
            raise credentials_error
        key, user, membership = authenticated
        needed_scope = "read" if request.method in {"GET", "HEAD", "OPTIONS"} else "write"
        scopes = frozenset(key.scopes_json)
        if needed_scope not in scopes:
            raise HTTPException(status_code=403, detail=f"API key requires {needed_scope} scope")
        return Principal(
            user=user,
            tenant_id=key.tenant_id,
            role=membership.role,
            auth_kind="api_key",
            scopes=scopes,
        )
    if not token:
        raise credentials_error
    try:
        payload = decode_access_token(token)
        user_id = UUID(payload["sub"])
        tenant_id = UUID(payload["tenant_id"])
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        raise credentials_error from exc
    user = db.scalar(
        select(User)
        .join(Membership, (Membership.user_id == User.id) & (Membership.tenant_id == tenant_id))
        .join(Tenant, Tenant.id == User.tenant_id)
        .where(
            User.id == user_id,
            User.tenant_id == tenant_id,
            User.is_active.is_(True),
            Tenant.is_active.is_(True),
            Membership.status == "active",
        )
    )
    if not user:
        raise credentials_error
    if payload.get("auth_version", 0) != user.auth_version:
        raise credentials_error
    membership = db.scalar(
        select(Membership).where(
            Membership.tenant_id == tenant_id,
            Membership.user_id == user.id,
            Membership.status == "active",
        )
    )
    if not membership:
        raise credentials_error
    return Principal(user=user, tenant_id=tenant_id, role=membership.role)


def require_roles(*allowed: UserRole):
    def dependency(principal: Principal = Depends(get_principal)) -> Principal:
        if principal.role not in allowed:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return principal

    return dependency


def require_platform_admin(
    principal: Principal = Depends(get_principal),
) -> Principal:
    if not principal.user.is_platform_admin:
        raise HTTPException(status_code=403, detail="Platform administrator access required")
    return principal


AdminPrincipal = Depends(require_roles(UserRole.owner, UserRole.admin))
