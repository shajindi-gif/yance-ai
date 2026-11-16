"""Full refunds retain one durable provider reference across failures and retries."""

import hashlib
from decimal import Decimal, InvalidOperation

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.models import Entitlement, Invoice, Order, Payment, PaymentEvent, Refund
from app.services.analytics.events import record_event
from app.services.payments import alipay, wechat


def complete_refund(
    db: Session, refund: Refund, *, provider_id: str, amount: object, currency: str, payload: bytes
) -> None:
    order = db.scalar(select(Order).where(Order.id == refund.order_id).with_for_update())
    db.refresh(refund)
    try:
        valid_amount = Decimal(str(amount)) == Decimal(str(refund.amount))
    except InvalidOperation:
        valid_amount = False
    if not valid_amount or currency != refund.currency:
        raise HTTPException(409, "Refund amount or currency mismatch")
    if refund.status == "succeeded":
        return
    if not provider_id or order.status != "paid":
        raise HTTPException(409, "Refund state requires reconciliation")
    refund.provider_refund_id = provider_id
    refund.status = "succeeded"
    order.status = "refunded"
    for entitlement in db.scalars(
        select(Entitlement).where(
            Entitlement.order_id == order.id, Entitlement.tenant_id == order.tenant_id
        )
    ):
        entitlement.status = "revoked"
    db.add(
        PaymentEvent(
            tenant_id=order.tenant_id,
            payment_id=refund.payment_id,
            provider=refund.provider,
            provider_event_id=f"refund:{refund.provider_refund_no}:SUCCESS",
            event_type="REFUND.SUCCESS",
            payload_sha256=hashlib.sha256(payload).hexdigest(),
            status="processed",
        )
    )
    record_event(
        db,
        tenant_id=order.tenant_id,
        user_id=refund.requested_by,
        name="refund_completed",
        event_key=f"refund_completed:{refund.id}",
        properties={"order_id": str(order.id), "refund_id": str(refund.id)},
    )
    if db.scalar(select(Invoice.id).where(Invoice.order_id == order.id)):
        record_event(
            db,
            tenant_id=order.tenant_id,
            user_id=None,
            name="invoice_refund_review_required",
            event_key=f"invoice_refund_review:{refund.id}",
            properties={"order_id": str(order.id)},
        )
    db.commit()


def submit_refund(db: Session, refund: Refund, payment: Payment) -> Refund:
    from app.api.routes.payments import _build_alipay_sign

    if refund.provider == "alipay":
        result, raw = alipay.call(
            "alipay.trade.refund",
            {
                "out_trade_no": payment.provider_trade_no,
                "refund_amount": f"{refund.amount:.2f}",
                "out_request_no": refund.provider_refund_no,
                "refund_reason": refund.reason,
            },
            _build_alipay_sign,
        )
        if result.get("code") != "10000" or result.get("out_trade_no") != payment.provider_trade_no:
            raise HTTPException(502, "Refund not confirmed by Alipay; retry the same request")
        if payment.alipay_trade_no and result.get("trade_no") != payment.alipay_trade_no:
            raise HTTPException(502, "Refund transaction mismatch")
        complete_refund(
            db,
            refund,
            provider_id=result.get("trade_no", ""),
            amount=result.get("refund_fee"),
            currency="CNY",
            payload=raw,
        )
    elif refund.provider == "wechat":
        result, raw = wechat.request_refund(
            payment.provider_trade_no,
            refund.provider_refund_no,
            int(Decimal(str(refund.amount)) * 100),
            refund.reason,
        )
        amounts = result.get("amount") or {}
        if (
            result.get("out_trade_no") != payment.provider_trade_no
            or result.get("out_refund_no") != refund.provider_refund_no
        ):
            raise HTTPException(502, "Refund transaction mismatch")
        if (
            amounts.get("total") != int(Decimal(str(payment.amount)) * 100)
            or amounts.get("refund") != int(Decimal(str(refund.amount)) * 100)
            or amounts.get("currency") != "CNY"
        ):
            raise HTTPException(502, "Refund amount mismatch")
        if result.get("status") == "SUCCESS":
            complete_refund(
                db,
                refund,
                provider_id=result.get("refund_id", ""),
                amount=Decimal(str(amounts["refund"])) / 100,
                currency="CNY",
                payload=raw,
            )
        elif result.get("status") == "PROCESSING":
            refund.status = "processing"
            db.commit()
        else:
            raise HTTPException(502, "Refund requires provider reconciliation")
    else:
        raise HTTPException(409, "该支付渠道的退款需人工处理")
    return refund
