import hashlib
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.models import AuditLog


def record_audit(db: Session, *, tenant_id, actor_user_id, action: str, resource_type: str, resource_id: str | None = None, request_id: str | None = None, result: str = "success", reason: str | None = None, details: dict | None = None) -> AuditLog:
    previous = db.scalar(
        select(AuditLog)
        .where(AuditLog.tenant_id == tenant_id)
        .order_by(AuditLog.occurred_at.desc(), AuditLog.id.desc())
        .limit(1)
        .with_for_update()
    )
    safe_details = details or {}
    canonical = json.dumps(
        {
            "tenant_id": str(tenant_id),
            "actor_user_id": str(actor_user_id) if actor_user_id else None,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "request_id": request_id,
            "result": result,
            "reason": reason,
            "details": safe_details,
            "previous_hash": previous.entry_hash if previous else None,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    entry = AuditLog(
        tenant_id=tenant_id,
        actor_user_id=actor_user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        request_id=request_id,
        result=result,
        reason=reason,
        details=safe_details,
        previous_hash=previous.entry_hash if previous else None,
        entry_hash=hashlib.sha256(canonical.encode()).hexdigest(),
    )
    db.add(entry)
    return entry
