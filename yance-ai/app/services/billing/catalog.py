from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.models import Plan, PriceVersion, Subscription, Tenant


def active_price(db: Session, plan_id: UUID) -> PriceVersion | None:
    now = datetime.now(UTC)
    return db.scalar(
        select(PriceVersion)
        .where(
            PriceVersion.plan_id == plan_id,
            PriceVersion.status == "active",
            PriceVersion.effective_at <= now,
            (PriceVersion.retired_at.is_(None) | (PriceVersion.retired_at > now)),
        )
        .order_by(PriceVersion.version.desc())
    )


def list_plan_catalog(db: Session) -> list[dict]:
    plans = db.scalars(select(Plan).where(Plan.status == "active").order_by(Plan.tier)).all()
    return [
        {
            "code": plan.code,
            "name": plan.name,
            "description": plan.description,
            "tier": plan.tier,
            "sales_motion": plan.sales_motion,
            "limits": plan.limits_json,
            "features": plan.features_json,
            "price": (
                {
                    "version": price.version,
                    "currency": price.currency,
                    "unit_amount": float(price.unit_amount),
                    "billing_interval": price.billing_interval,
                    "provider": price.provider,
                    "checkout_available": bool(price.provider_price_id) or plan.code == "free",
                }
                if (price := active_price(db, plan.id))
                else None
            ),
        }
        for plan in plans
    ]


def ensure_current_subscription(db: Session, tenant_id: UUID) -> tuple[Subscription, Plan]:
    """Return a locked usable subscription, lazily provisioning the database Free plan."""
    db.scalar(select(Tenant.id).where(Tenant.id == tenant_id).with_for_update())
    now = datetime.now(UTC)
    subscription = db.scalar(
        select(Subscription)
        .where(
            Subscription.tenant_id == tenant_id,
            Subscription.status.in_(("active", "grace_period")),
            Subscription.current_period_end > now,
        )
        .order_by(Subscription.created_at.desc())
        .with_for_update()
    )
    if subscription:
        plan = db.get(Plan, subscription.plan_id)
        if not plan or plan.status != "active":
            raise RuntimeError("subscription_plan_unavailable")
        return subscription, plan
    plan = db.scalar(select(Plan).where(Plan.code == "free", Plan.status == "active"))
    if not plan:
        raise RuntimeError("free_plan_not_configured")
    price = active_price(db, plan.id)
    subscription = Subscription(
        tenant_id=tenant_id,
        plan_id=plan.id,
        price_version_id=price.id if price else None,
        provider="internal",
        status="active",
        current_period_start=now,
        current_period_end=now + timedelta(days=30),
        metadata_json={"provisioning": "automatic_free_fallback"},
    )
    db.add(subscription)
    db.flush()
    return subscription, plan
