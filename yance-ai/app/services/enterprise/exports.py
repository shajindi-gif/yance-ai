import hashlib
import json
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.models import Company, ExportJob, Subscription, Tenant, UsageRecord, User


def create_safe_workspace_export(db: Session, *, tenant_id, user_id) -> ExportJob:
    tenant = db.get(Tenant, tenant_id)
    users = db.scalars(select(User).where(User.tenant_id == tenant_id)).all()
    companies = db.scalars(select(Company).where(Company.tenant_id == tenant_id)).all()
    subscriptions = db.scalars(select(Subscription).where(Subscription.tenant_id == tenant_id)).all()
    usage = db.scalars(select(UsageRecord).where(UsageRecord.tenant_id == tenant_id)).all()
    payload = {
        "schema_version": "workspace-export-v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "organization": {"id": str(tenant.id), "name": tenant.name, "slug": tenant.slug},
        "users": [{"id": str(item.id), "email": item.email, "full_name": item.full_name, "role": item.role.value, "active": item.is_active} for item in users],
        "companies": [{"id": str(item.id), "name": item.name, "province": item.province, "city": item.city, "industry": item.industry} for item in companies],
        "subscriptions": [{"id": str(item.id), "plan_id": str(item.plan_id), "status": item.status, "period_start": item.current_period_start.isoformat(), "period_end": item.current_period_end.isoformat()} for item in subscriptions],
        "usage": [{"meter": item.meter_key, "quantity": item.quantity, "occurred_at": item.occurred_at.isoformat(), "resource_type": item.resource_type, "resource_id": item.resource_id} for item in usage],
        "excluded_sensitive_fields": ["password_hash", "api_key_hash", "payment_raw_response", "document_object_key"],
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    job = ExportJob(
        tenant_id=tenant_id,
        requested_by=user_id,
        status="completed",
        format="json",
        scope="workspace",
        payload_json=payload,
        checksum_sha256=hashlib.sha256(encoded).hexdigest(),
        record_counts_json={"users": len(users), "companies": len(companies), "subscriptions": len(subscriptions), "usage_records": len(usage)},
        completed_at=datetime.now(UTC),
    )
    db.add(job)
    db.flush()
    return job
