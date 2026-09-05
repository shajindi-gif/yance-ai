import json
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import Principal, get_principal, require_roles
from app.core.db import get_db
from app.models.models import (
    ApiKey,
    AuditLog,
    DeletionRequest,
    ExportJob,
    RetentionPolicy,
    UserRole,
)
from app.services.enterprise.api_keys import create_api_key
from app.services.enterprise.audit import record_audit
from app.services.enterprise.exports import create_safe_workspace_export
from app.services.enterprise.flags import effective_flags

router = APIRouter(prefix="/enterprise", tags=["enterprise"])

ALLOWED_API_SCOPES = {"read", "write"}


class ApiKeyCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    scopes: list[str] = Field(min_length=1, max_length=2)
    expires_at: datetime | None = None

    @model_validator(mode="after")
    def validate_key(self):
        if not set(self.scopes) <= ALLOWED_API_SCOPES:
            raise ValueError("unsupported API key scope")
        if self.expires_at and self.expires_at <= datetime.now(UTC):
            raise ValueError("expires_at must be in the future")
        return self


class RetentionUpdate(BaseModel):
    document_days: int = Field(ge=30, le=3650)
    agent_trace_days: int = Field(ge=30, le=3650)
    analytics_days: int = Field(ge=30, le=3650)
    audit_days: int = Field(ge=365, le=3650)
    legal_hold: bool = False
    legal_hold_reason: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def validate_hold(self):
        if self.legal_hold and not self.legal_hold_reason:
            raise ValueError("legal_hold_reason is required")
        return self


class DeletionCreate(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


def _key_out(item: ApiKey) -> dict:
    return {"id": str(item.id), "name": item.name, "prefix": item.prefix, "scopes": item.scopes_json, "expires_at": item.expires_at, "last_used_at": item.last_used_at, "revoked_at": item.revoked_at, "created_at": item.created_at}


def _retention(db: Session, principal: Principal) -> RetentionPolicy:
    policy = db.scalar(select(RetentionPolicy).where(RetentionPolicy.tenant_id == principal.tenant_id))
    if not policy:
        policy = RetentionPolicy(tenant_id=principal.tenant_id, configured_by=principal.user.id)
        db.add(policy)
        db.flush()
    return policy


@router.get("/api-keys")
def list_api_keys(principal: Principal = Depends(require_roles(UserRole.owner, UserRole.admin)), db: Session = Depends(get_db)) -> dict:
    items = db.scalars(select(ApiKey).where(ApiKey.tenant_id == principal.tenant_id).order_by(ApiKey.created_at.desc())).all()
    return {"items": [_key_out(item) for item in items]}


@router.post("/api-keys", status_code=201)
def issue_api_key(payload: ApiKeyCreate, principal: Principal = Depends(require_roles(UserRole.owner, UserRole.admin)), db: Session = Depends(get_db)) -> dict:
    key, secret = create_api_key(db, tenant_id=principal.tenant_id, user_id=principal.user.id, name=payload.name, scopes=payload.scopes, expires_at=payload.expires_at)
    record_audit(db, tenant_id=principal.tenant_id, actor_user_id=principal.user.id, action="api_key.created", resource_type="api_key", resource_id=str(key.id), details={"prefix": key.prefix, "scopes": key.scopes_json})
    db.commit()
    return {**_key_out(key), "secret": secret, "secret_display": "returned_once"}


@router.post("/api-keys/{key_id}/revoke")
def revoke_api_key(key_id: UUID, principal: Principal = Depends(require_roles(UserRole.owner, UserRole.admin)), db: Session = Depends(get_db)) -> dict:
    key = db.scalar(select(ApiKey).where(ApiKey.id == key_id, ApiKey.tenant_id == principal.tenant_id))
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")
    if key.revoked_at is None:
        key.revoked_at = datetime.now(UTC)
        record_audit(db, tenant_id=principal.tenant_id, actor_user_id=principal.user.id, action="api_key.revoked", resource_type="api_key", resource_id=str(key.id), details={"prefix": key.prefix})
        db.commit()
    return _key_out(key)


@router.get("/retention")
def get_retention(principal: Principal = Depends(require_roles(UserRole.owner, UserRole.admin)), db: Session = Depends(get_db)) -> dict:
    policy = _retention(db, principal)
    db.commit()
    return {"document_days": policy.document_days, "agent_trace_days": policy.agent_trace_days, "analytics_days": policy.analytics_days, "audit_days": policy.audit_days, "legal_hold": policy.legal_hold, "legal_hold_reason": policy.legal_hold_reason, "enforcement_worker_available": False}


@router.put("/retention")
def update_retention(payload: RetentionUpdate, principal: Principal = Depends(require_roles(UserRole.owner)), db: Session = Depends(get_db)) -> dict:
    policy = _retention(db, principal)
    for field, value in payload.model_dump().items():
        setattr(policy, field, value)
    policy.configured_by = principal.user.id
    record_audit(db, tenant_id=principal.tenant_id, actor_user_id=principal.user.id, action="retention.updated", resource_type="retention_policy", resource_id=str(policy.id), details={"legal_hold": policy.legal_hold, "document_days": policy.document_days})
    db.commit()
    return get_retention(principal=principal, db=db)


@router.get("/exports")
def list_exports(principal: Principal = Depends(require_roles(UserRole.owner, UserRole.admin)), db: Session = Depends(get_db)) -> dict:
    items = db.scalars(select(ExportJob).where(ExportJob.tenant_id == principal.tenant_id).order_by(ExportJob.created_at.desc())).all()
    return {"items": [{"id": str(item.id), "status": item.status, "format": item.format, "scope": item.scope, "checksum_sha256": item.checksum_sha256, "record_counts": item.record_counts_json, "created_at": item.created_at, "completed_at": item.completed_at} for item in items]}


@router.post("/exports", status_code=202)
def create_export(principal: Principal = Depends(require_roles(UserRole.owner, UserRole.admin)), db: Session = Depends(get_db)) -> dict:
    job = create_safe_workspace_export(db, tenant_id=principal.tenant_id, user_id=principal.user.id)
    record_audit(db, tenant_id=principal.tenant_id, actor_user_id=principal.user.id, action="workspace.exported", resource_type="export_job", resource_id=str(job.id), details={"checksum_sha256": job.checksum_sha256, "record_counts": job.record_counts_json})
    db.commit()
    return {"id": str(job.id), "status": job.status, "checksum_sha256": job.checksum_sha256, "record_counts": job.record_counts_json}


@router.get("/exports/{job_id}/download")
def download_export(job_id: UUID, principal: Principal = Depends(require_roles(UserRole.owner, UserRole.admin)), db: Session = Depends(get_db)) -> Response:
    job = db.scalar(select(ExportJob).where(ExportJob.id == job_id, ExportJob.tenant_id == principal.tenant_id, ExportJob.status == "completed"))
    if not job:
        raise HTTPException(status_code=404, detail="Export not found")
    return Response(content=json.dumps(job.payload_json, ensure_ascii=False, sort_keys=True), media_type="application/json", headers={"Content-Disposition": f'attachment; filename="yance-workspace-{job.id}.json"', "X-Content-SHA256": job.checksum_sha256 or ""})


@router.get("/deletion-request")
def get_deletion_request(principal: Principal = Depends(require_roles(UserRole.owner, UserRole.admin)), db: Session = Depends(get_db)) -> dict:
    item = db.scalar(select(DeletionRequest).where(DeletionRequest.tenant_id == principal.tenant_id, DeletionRequest.status == "scheduled").order_by(DeletionRequest.created_at.desc()))
    return {"request": None if not item else {"id": str(item.id), "status": item.status, "scheduled_for": item.scheduled_for, "reason": item.reason, "blockers": item.blocker_json}, "execution_worker_available": False}


@router.post("/deletion-request", status_code=202)
def schedule_deletion(payload: DeletionCreate, principal: Principal = Depends(require_roles(UserRole.owner)), db: Session = Depends(get_db)) -> dict:
    policy = _retention(db, principal)
    if policy.legal_hold:
        raise HTTPException(status_code=409, detail={"code": "legal_hold", "message": "Workspace deletion is blocked by legal hold."})
    existing = db.scalar(select(DeletionRequest).where(DeletionRequest.tenant_id == principal.tenant_id, DeletionRequest.status == "scheduled"))
    if existing:
        return {"id": str(existing.id), "status": existing.status, "scheduled_for": existing.scheduled_for, "execution_worker_available": False}
    item = DeletionRequest(tenant_id=principal.tenant_id, requested_by=principal.user.id, reason=payload.reason, status="scheduled", scheduled_for=datetime.now(UTC) + timedelta(days=7), blocker_json=["deployment-specific storage, log, backup and provider propagation worker is not configured"])
    db.add(item)
    db.flush()
    record_audit(db, tenant_id=principal.tenant_id, actor_user_id=principal.user.id, action="workspace.deletion_scheduled", resource_type="deletion_request", resource_id=str(item.id), reason=payload.reason)
    db.commit()
    return {"id": str(item.id), "status": item.status, "scheduled_for": item.scheduled_for, "blockers": item.blocker_json, "execution_worker_available": False}


@router.post("/deletion-request/{request_id}/cancel")
def cancel_deletion(request_id: UUID, principal: Principal = Depends(require_roles(UserRole.owner)), db: Session = Depends(get_db)) -> dict:
    item = db.scalar(select(DeletionRequest).where(DeletionRequest.id == request_id, DeletionRequest.tenant_id == principal.tenant_id, DeletionRequest.status == "scheduled"))
    if not item:
        raise HTTPException(status_code=404, detail="Deletion request not found")
    item.status = "canceled"
    item.canceled_at = datetime.now(UTC)
    record_audit(db, tenant_id=principal.tenant_id, actor_user_id=principal.user.id, action="workspace.deletion_canceled", resource_type="deletion_request", resource_id=str(item.id))
    db.commit()
    return {"id": str(item.id), "status": item.status, "canceled_at": item.canceled_at}


@router.get("/feature-flags")
def get_feature_flags(principal: Principal = Depends(get_principal), db: Session = Depends(get_db)) -> dict:
    return {"flags": effective_flags(db, principal.tenant_id)}


@router.get("/audit-logs")
def list_audit_logs(limit: int = 100, principal: Principal = Depends(require_roles(UserRole.owner, UserRole.admin)), db: Session = Depends(get_db)) -> dict:
    items = db.scalars(select(AuditLog).where(AuditLog.tenant_id == principal.tenant_id).order_by(AuditLog.occurred_at.desc()).limit(min(max(limit, 1), 200))).all()
    return {"items": [{"id": str(item.id), "action": item.action, "resource_type": item.resource_type, "resource_id": item.resource_id, "result": item.result, "reason": item.reason, "details": item.details, "entry_hash": item.entry_hash, "previous_hash": item.previous_hash, "occurred_at": item.occurred_at} for item in items]}
