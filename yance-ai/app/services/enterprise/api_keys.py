import hashlib
import hmac
import secrets
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import ApiKey, Membership, Tenant, User


def _hash_secret(raw_key: str) -> str:
    return hmac.new(settings.api_key_pepper.encode(), raw_key.encode(), hashlib.sha256).hexdigest()


def create_api_key(db: Session, *, tenant_id, user_id, name: str, scopes: list[str], expires_at=None) -> tuple[ApiKey, str]:
    prefix = secrets.token_hex(6)
    raw_key = f"yance_live_{prefix}_{secrets.token_urlsafe(32)}"
    key = ApiKey(
        tenant_id=tenant_id,
        created_by=user_id,
        name=name,
        prefix=prefix,
        secret_hash=_hash_secret(raw_key),
        scopes_json=sorted(set(scopes)),
        expires_at=expires_at,
    )
    db.add(key)
    db.flush()
    return key, raw_key


def authenticate_api_key(db: Session, raw_key: str) -> tuple[ApiKey, User, Membership] | None:
    parts = raw_key.split("_", 3)
    if len(parts) != 4 or parts[:2] != ["yance", "live"]:
        return None
    prefix = parts[2]
    row = db.execute(
        select(ApiKey, User, Membership)
        .join(User, User.id == ApiKey.created_by)
        .join(Membership, (Membership.user_id == User.id) & (Membership.tenant_id == ApiKey.tenant_id))
        .join(Tenant, Tenant.id == ApiKey.tenant_id)
        .where(
            ApiKey.prefix == prefix,
            ApiKey.revoked_at.is_(None),
            User.is_active.is_(True),
            Membership.status == "active",
            Tenant.is_active.is_(True),
        )
    ).one_or_none()
    if not row:
        return None
    key, user, membership = row
    now = datetime.now(UTC)
    if key.expires_at and key.expires_at <= now:
        return None
    if not hmac.compare_digest(key.secret_hash, _hash_secret(raw_key)):
        return None
    key.last_used_at = now
    db.commit()
    return key, user, membership
