from dataclasses import dataclass
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.core.security import decode_access_token
from app.models.models import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.api_v1_prefix}/auth/login")


@dataclass(frozen=True)
class Principal:
    user: User
    tenant_id: UUID
    role: UserRole


def get_principal(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> Principal:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired access token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        user_id = UUID(payload["sub"])
        tenant_id = UUID(payload["tenant_id"])
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        raise credentials_error from exc
    user = db.scalar(
        select(User).where(
            User.id == user_id, User.tenant_id == tenant_id, User.is_active.is_(True)
        )
    )
    if not user:
        raise credentials_error
    return Principal(user=user, tenant_id=tenant_id, role=user.role)


def require_roles(*allowed: UserRole):
    def dependency(principal: Principal = Depends(get_principal)) -> Principal:
        if principal.role not in allowed:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return principal

    return dependency


AdminPrincipal = Depends(require_roles(UserRole.owner, UserRole.admin))
