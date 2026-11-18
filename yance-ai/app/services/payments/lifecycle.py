"""Provider-confirmed closure. Unknown results remain open for another reconciliation."""

from datetime import UTC, datetime
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.models import Order, Payment
from app.services.payments import alipay, wechat
from app.services.payments.settlement import provider_paid_time, settle_payment


def query_payment(db: Session, payment: Payment) -> dict:
    # Existing route signing functions remain the single signing implementation.
    from app.api.routes.payments import query_alipay_payment

    if payment.provider == "alipay":
        return query_alipay_payment(db, payment)
    if payment.provider != "wechat":
        return {"queried": False}
    state = wechat.query_order(payment.provider_trade_no)
    if state is None:
        return {"queried": False}
    if state.get("trade_state") == "SUCCESS":
        total = state.get("total")
        transaction = state.get("transaction_id")
        if not transaction or not isinstance(total, int) or isinstance(total, bool):
            raise HTTPException(502, "Invalid WeChat transaction")
        payment.raw_response = {
            **(payment.raw_response or {}),
            "transaction_id": transaction,
            "success_time": state.get("success_time"),
        }
        result = settle_payment(
            db,
            payment=payment,
            provider_event_id=transaction,
            event_type="TRANSACTION.SUCCESS.QUERY",
            paid_amount=Decimal(total) / 100,
            currency=state.get("currency") or "",
            payload=b'{"source":"active_query"}',
            paid_at=provider_paid_time(state.get("success_time")),
        )
        if not result.accepted:
            raise HTTPException(409, "Payment reconciliation required")
        return {"queried": True, "status": "paid", "trade_state": "SUCCESS"}
    return {"queried": True, "trade_state": state.get("trade_state")}


def close_payment(db: Session, payment: Payment) -> bool:
    from app.api.routes.payments import _build_alipay_sign

    result = query_payment(db, payment)
    if not result.get("queried") or result.get("status") == "paid":
        return False
    state = result.get("trade_state")
    if state not in {"CLOSED", "TRADE_CLOSED", "REVOKED", "PAYERROR"}:
        if payment.provider == "alipay" and state == "WAIT_BUYER_PAY":
            response, _ = alipay.call(
                "alipay.trade.close",
                {"out_trade_no": payment.provider_trade_no},
                _build_alipay_sign,
            )
            if (
                response.get("code") != "10000"
                or response.get("out_trade_no") != payment.provider_trade_no
            ):
                return False
        elif payment.provider == "wechat" and state == "NOTPAY":
            if not wechat.close_order(payment.provider_trade_no):
                return False
        else:
            return False
    payment.status = "expired"
    return True


def expire_orders(db: Session, limit: int = 50) -> int:
    count = 0
    ids = list(
        db.scalars(
            select(Order.id)
            .where(Order.status.in_(["created", "pending"]), Order.expires_at <= datetime.now(UTC))
            .limit(limit)
        )
    )
    for order_id in ids:
        order = db.scalar(
            select(Order).where(Order.id == order_id).with_for_update(skip_locked=True)
        )
        if not order or order.status not in {"created", "pending"}:
            db.rollback()
            continue
        payments = list(
            db.scalars(
                select(Payment).where(
                    Payment.order_id == order.id, Payment.tenant_id == order.tenant_id
                )
            )
        )
        try:
            confirmed = True
            for payment in payments:
                if payment.status == "completed" or not close_payment(db, payment):
                    confirmed = False
                    break
            if confirmed:
                order.status = "expired"
                count += 1
                db.commit()
            else:
                db.rollback()
        except HTTPException:
            db.rollback()
    return count
