from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.models import (
    Company,
    Document,
    Subscription,
    UsageBudget,
    UsageRecord,
    User,
)
from app.services.billing.catalog import ensure_current_subscription

RESOURCE_METERS = {"companies", "documents", "storage_bytes", "users"}


@dataclass(frozen=True)
class QuotaExceeded(Exception):
    meter: str
    used: int
    requested: int
    limit: int
    reset_at: datetime
    scope: str = "plan"

    def detail(self) -> dict:
        return {
            "code": "quota_exceeded",
            "meter": self.meter,
            "used": self.used,
            "requested": self.requested,
            "limit": self.limit,
            "reset_at": self.reset_at.isoformat(),
            "scope": self.scope,
        }


def _resource_usage(db: Session, tenant_id: UUID, meter: str) -> int:
    if meter == "companies":
        return int(db.scalar(select(func.count()).select_from(Company).where(Company.tenant_id == tenant_id)) or 0)
    if meter == "users":
        return int(db.scalar(select(func.count()).select_from(User).where(User.tenant_id == tenant_id, User.is_active.is_(True))) or 0)
    if meter == "documents":
        return int(db.scalar(select(func.count()).select_from(Document).where(Document.tenant_id == tenant_id, Document.status != "rejected")) or 0)
    if meter == "storage_bytes":
        return int(db.scalar(select(func.coalesce(func.sum(Document.size_bytes), 0)).where(Document.tenant_id == tenant_id, Document.status != "rejected")) or 0)
    raise ValueError(f"unsupported resource meter: {meter}")


def _event_usage(db: Session, subscription: Subscription, meter: str, *, user_id: UUID | None = None, workflow_run_id: UUID | None = None) -> int:
    query = select(func.coalesce(func.sum(UsageRecord.quantity), 0)).where(
        UsageRecord.tenant_id == subscription.tenant_id,
        UsageRecord.meter_key == meter,
        UsageRecord.occurred_at >= subscription.current_period_start,
        UsageRecord.occurred_at < subscription.current_period_end,
    )
    if user_id:
        query = query.where(UsageRecord.user_id == user_id)
    if workflow_run_id:
        query = query.where(UsageRecord.workflow_run_id == workflow_run_id)
    return int(db.scalar(query) or 0)


def _plan_limit(plan_limits: dict, meter: str) -> int | None:
    if meter not in plan_limits:
        raise RuntimeError(f"plan_meter_not_configured:{meter}")
    value = plan_limits[meter]
    return None if value is None else int(value)


def _enforce_budgets(db: Session, subscription: Subscription, meter: str, requested: int, *, user_id: UUID | None, workflow_run_id: UUID | None) -> None:
    scope_ids = {"organization": subscription.tenant_id}
    if user_id:
        scope_ids["user"] = user_id
    if workflow_run_id:
        scope_ids["workflow"] = workflow_run_id
    budgets = db.scalars(
        select(UsageBudget).where(
            UsageBudget.tenant_id == subscription.tenant_id,
            UsageBudget.meter_key == meter,
            UsageBudget.active.is_(True),
        )
    ).all()
    for budget in budgets:
        if scope_ids.get(budget.scope_type) != budget.scope_id:
            continue
        used = _event_usage(
            db,
            subscription,
            meter,
            user_id=budget.scope_id if budget.scope_type == "user" else None,
            workflow_run_id=budget.scope_id if budget.scope_type == "workflow" else None,
        )
        if used + requested > budget.hard_limit:
            raise QuotaExceeded(meter, used, requested, budget.hard_limit, subscription.current_period_end, budget.scope_type)


def ensure_capacity(db: Session, *, tenant_id: UUID, meter: str, requested: int = 1) -> dict:
    if meter not in RESOURCE_METERS:
        raise ValueError("ensure_capacity only supports resource meters")
    subscription, plan = ensure_current_subscription(db, tenant_id)
    used = _resource_usage(db, tenant_id, meter)
    limit = _plan_limit(plan.limits_json, meter)
    if limit is not None and used + requested > limit:
        raise QuotaExceeded(meter, used, requested, limit, subscription.current_period_end)
    return {"meter": meter, "used": used, "requested": requested, "limit": limit}


def _consume_usage(
    db: Session,
    *,
    tenant_id: UUID,
    meter: str,
    quantity: int,
    idempotency_key: str,
    user_id: UUID | None = None,
    workflow_run_id: UUID | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
) -> tuple[UsageRecord, bool]:
    if quantity <= 0:
        raise ValueError("usage quantity must be positive")
    subscription, plan = ensure_current_subscription(db, tenant_id)
    existing = db.scalar(
        select(UsageRecord).where(
            UsageRecord.tenant_id == tenant_id,
            UsageRecord.idempotency_key == idempotency_key,
        )
    )
    if existing:
        return existing, False
    used = _event_usage(db, subscription, meter)
    limit = _plan_limit(plan.limits_json, meter)
    if limit is not None and used + quantity > limit:
        raise QuotaExceeded(meter, used, quantity, limit, subscription.current_period_end)
    _enforce_budgets(db, subscription, meter, quantity, user_id=user_id, workflow_run_id=workflow_run_id)
    record = UsageRecord(
        tenant_id=tenant_id,
        subscription_id=subscription.id,
        user_id=user_id,
        workflow_run_id=workflow_run_id,
        meter_key=meter,
        quantity=quantity,
        idempotency_key=idempotency_key,
        resource_type=resource_type,
        resource_id=resource_id,
        source="server",
        occurred_at=datetime.now(UTC),
    )
    db.add(record)
    db.flush()
    return record, True


def consume_usage(
    db: Session,
    *,
    tenant_id: UUID,
    meter: str,
    quantity: int,
    idempotency_key: str,
    user_id: UUID | None = None,
    workflow_run_id: UUID | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
) -> UsageRecord:
    record, _ = _consume_usage(
        db,
        tenant_id=tenant_id,
        meter=meter,
        quantity=quantity,
        idempotency_key=idempotency_key,
        user_id=user_id,
        workflow_run_id=workflow_run_id,
        resource_type=resource_type,
        resource_id=resource_id,
    )
    return record


def consume_usage_once(
    db: Session,
    *,
    tenant_id: UUID,
    meter: str,
    quantity: int,
    idempotency_key: str,
    user_id: UUID | None = None,
    workflow_run_id: UUID | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
) -> tuple[UsageRecord, bool]:
    """Consume once and tell callers whether this request created the ledger entry."""
    return _consume_usage(
        db,
        tenant_id=tenant_id,
        meter=meter,
        quantity=quantity,
        idempotency_key=idempotency_key,
        user_id=user_id,
        workflow_run_id=workflow_run_id,
        resource_type=resource_type,
        resource_id=resource_id,
    )


def usage_snapshot(db: Session, tenant_id: UUID) -> dict:
    subscription, plan = ensure_current_subscription(db, tenant_id)
    usage = []
    for meter, configured_limit in plan.limits_json.items():
        used = _resource_usage(db, tenant_id, meter) if meter in RESOURCE_METERS else _event_usage(db, subscription, meter)
        limit = None if configured_limit is None else int(configured_limit)
        usage.append({"meter": meter, "used": used, "limit": limit, "remaining": None if limit is None else max(0, limit - used)})
    return {"subscription": subscription, "plan": plan, "usage": usage}
