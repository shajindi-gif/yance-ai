"""Replay-safe, server-validated payment settlement."""

import hashlib
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.models import (
    AnalyticsEvent,
    Entitlement,
    Order,
    Payment,
    PaymentEvent,
    Product,
)


@dataclass(frozen=True)
class SettlementResult:
    accepted: bool
    replayed: bool = False
    error_code: str | None = None


def _commit_or_resolve_replay(db: Session, *, event: PaymentEvent) -> SettlementResult | None:
    """Commit once; resolve a concurrent duplicate provider event as a replay."""
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.scalar(
            select(PaymentEvent).where(
                PaymentEvent.provider == event.provider,
                PaymentEvent.provider_event_id == event.provider_event_id,
            )
        )
        if existing:
            return SettlementResult(
                accepted=existing.status == "processed",
                replayed=True,
                error_code=existing.error_code,
            )
        raise
    return None


def _money(value: object) -> Decimal:
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError("invalid_amount") from exc


def validate_settlement(
    *, order: Order, payment: Payment, paid_amount: object, currency: str
) -> str | None:
    if payment.order_id != order.id or payment.tenant_id != order.tenant_id:
        return "payment_order_mismatch"
    try:
        expected = _money(order.amount)
        recorded = _money(payment.amount)
        received = _money(paid_amount)
    except ValueError:
        return "invalid_amount"
    if expected != recorded or expected != received:
        return "amount_mismatch"
    if (currency or "").upper() != (order.currency or "").upper():
        return "currency_mismatch"
    return None


def settle_payment(
    db: Session,
    *,
    payment: Payment,
    provider_event_id: str,
    event_type: str,
    paid_amount: object,
    currency: str,
    payload: bytes,
) -> SettlementResult:
    existing = db.scalar(
        select(PaymentEvent).where(
            PaymentEvent.provider == payment.provider,
            PaymentEvent.provider_event_id == provider_event_id,
        )
    )
    if existing:
        return SettlementResult(
            accepted=existing.status == "processed",
            replayed=True,
            error_code=existing.error_code,
        )

    order = db.scalar(
        select(Order)
        .where(Order.id == payment.order_id, Order.tenant_id == payment.tenant_id)
        .with_for_update()
    )
    event = PaymentEvent(
        tenant_id=payment.tenant_id,
        payment_id=payment.id,
        provider=payment.provider,
        provider_event_id=provider_event_id,
        event_type=event_type,
        payload_sha256=hashlib.sha256(payload).hexdigest(),
        status="received",
    )
    db.add(event)
    if not order:
        event.status = "rejected"
        event.error_code = "order_not_found"
        replay = _commit_or_resolve_replay(db, event=event)
        return replay or SettlementResult(False, error_code=event.error_code)

    error = validate_settlement(
        order=order,
        payment=payment,
        paid_amount=paid_amount,
        currency=currency,
    )
    if error:
        event.status = "rejected"
        event.error_code = error
        replay = _commit_or_resolve_replay(db, event=event)
        return replay or SettlementResult(False, error_code=error)

    product = db.scalar(select(Product).where(Product.code == order.product_code))
    if not product:
        event.status = "rejected"
        event.error_code = "product_not_found"
        replay = _commit_or_resolve_replay(db, event=event)
        return replay or SettlementResult(False, error_code=event.error_code)

    if payment.status == "completed" and order.status == "paid":
        event.status = "processed"
        replay = _commit_or_resolve_replay(db, event=event)
        return replay or SettlementResult(True)

    payment.status = "completed"
    order.status = "paid"
    entitlement = db.scalar(
        select(Entitlement).where(
            Entitlement.order_id == order.id,
            Entitlement.tenant_id == order.tenant_id,
        )
    )
    if not entitlement:
        db.add(
            Entitlement(
                tenant_id=order.tenant_id,
                user_id=None,
                product_id=product.id,
                order_id=order.id,
                resource_type=product.entitlement_type,
                resource_id=order.resource_id,
                status="active",
            )
        )
    db.add(
        AnalyticsEvent(
            tenant_id=order.tenant_id,
            user_id=None,
            name="payment_completed",
            properties={"order_id": str(order.id), "provider": payment.provider},
        )
    )
    event.status = "processed"
    replay = _commit_or_resolve_replay(db, event=event)
    return replay or SettlementResult(True)
