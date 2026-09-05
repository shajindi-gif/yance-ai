from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import Principal, get_principal, require_roles
from app.core.db import get_db
from app.models.models import Invoice, Order, UsageBudget, UserRole
from app.services.billing.catalog import list_plan_catalog
from app.services.billing.usage import usage_snapshot
from app.services.enterprise.audit import record_audit

router = APIRouter(prefix="/billing", tags=["billing"])


class BudgetUpsert(BaseModel):
    scope_type: str = Field(pattern="^(organization|user|workflow)$")
    scope_id: UUID | None = None
    meter_key: str = Field(min_length=2, max_length=80)
    hard_limit: int = Field(ge=0)
    warning_threshold: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_threshold(self):
        if self.warning_threshold is not None and self.warning_threshold > self.hard_limit:
            raise ValueError("warning_threshold cannot exceed hard_limit")
        if self.scope_type != "organization" and self.scope_id is None:
            raise ValueError("user and workflow budgets require scope_id")
        return self


@router.get("/plans")
def get_plans(db: Session = Depends(get_db)) -> dict:
    return {"items": list_plan_catalog(db), "pricing_source": "database_price_versions"}


@router.get("/overview")
def get_billing_overview(
    principal: Principal = Depends(get_principal), db: Session = Depends(get_db)
) -> dict:
    snapshot = usage_snapshot(db, principal.tenant_id)
    subscription = snapshot["subscription"]
    plan = snapshot["plan"]
    budgets = db.scalars(
        select(UsageBudget)
        .where(UsageBudget.tenant_id == principal.tenant_id, UsageBudget.active.is_(True))
        .order_by(UsageBudget.created_at.desc())
    ).all()
    orders = db.scalars(
        select(Order)
        .where(Order.tenant_id == principal.tenant_id)
        .order_by(Order.created_at.desc())
        .limit(20)
    ).all()
    invoices = db.scalars(
        select(Invoice)
        .where(Invoice.tenant_id == principal.tenant_id)
        .order_by(Invoice.created_at.desc())
        .limit(20)
    ).all()
    db.commit()
    return {
        "subscription": {
            "id": str(subscription.id),
            "status": subscription.status,
            "provider": subscription.provider,
            "current_period_start": subscription.current_period_start,
            "current_period_end": subscription.current_period_end,
            "cancel_at_period_end": subscription.cancel_at_period_end,
            "grace_ends_at": subscription.grace_ends_at,
        },
        "plan": {
            "code": plan.code,
            "name": plan.name,
            "sales_motion": plan.sales_motion,
            "limits": plan.limits_json,
            "features": plan.features_json,
        },
        "usage": snapshot["usage"],
        "budgets": [
            {
                "id": str(item.id),
                "scope_type": item.scope_type,
                "scope_id": str(item.scope_id) if item.scope_id else None,
                "meter_key": item.meter_key,
                "hard_limit": item.hard_limit,
                "warning_threshold": item.warning_threshold,
            }
            for item in budgets
        ],
        "orders": [
            {
                "id": str(item.id),
                "order_no": item.order_no,
                "product_code": item.product_code,
                "amount": float(item.amount),
                "currency": item.currency,
                "status": item.status,
                "created_at": item.created_at,
            }
            for item in orders
        ],
        "tax_invoices": [
            {
                "id": str(item.id),
                "order_id": str(item.order_id),
                "invoice_no": item.invoice_no,
                "total_amount": float(item.total_amount),
                "status": item.status,
                "created_at": item.created_at,
            }
            for item in invoices
        ],
        "paid_plan_checkout_available": False,
        "paid_plan_checkout_message": "No paid subscription PriceVersion is configured.",
    }


@router.post("/budgets", status_code=201)
def upsert_budget(
    payload: BudgetUpsert,
    principal: Principal = Depends(require_roles(UserRole.owner, UserRole.admin)),
    db: Session = Depends(get_db),
) -> dict:
    scope_id = principal.tenant_id if payload.scope_type == "organization" else payload.scope_id
    budget = db.scalar(
        select(UsageBudget).where(
            UsageBudget.tenant_id == principal.tenant_id,
            UsageBudget.scope_type == payload.scope_type,
            UsageBudget.scope_id == scope_id,
            UsageBudget.meter_key == payload.meter_key,
        )
    )
    if not budget:
        budget = UsageBudget(
            tenant_id=principal.tenant_id,
            scope_type=payload.scope_type,
            scope_id=scope_id,
            meter_key=payload.meter_key,
            hard_limit=payload.hard_limit,
            warning_threshold=payload.warning_threshold,
        )
        db.add(budget)
        db.flush()
    else:
        budget.hard_limit = payload.hard_limit
        budget.warning_threshold = payload.warning_threshold
        budget.active = True
    record_audit(
        db,
        tenant_id=principal.tenant_id,
        actor_user_id=principal.user.id,
        action="billing.budget.upserted",
        resource_type="usage_budget",
        resource_id=str(budget.id),
        details={"scope_type": payload.scope_type, "meter_key": payload.meter_key},
    )
    db.commit()
    return {"id": str(budget.id), "scope_type": budget.scope_type, "scope_id": str(budget.scope_id), "meter_key": budget.meter_key, "hard_limit": budget.hard_limit, "warning_threshold": budget.warning_threshold}
