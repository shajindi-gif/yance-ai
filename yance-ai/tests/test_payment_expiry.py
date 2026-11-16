import uuid
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from test_core_workflow import _register

from app.core.db import SessionLocal
from app.main import app
from app.models.models import AnalyticsEvent, Order, Payment
from app.services.payments import alipay
from app.services.payments.lifecycle import expire_orders
from app.services.payments.settlement import settle_payment


def records(client):
    headers, _ = _register(client, uuid.uuid4().hex)
    tenant = uuid.UUID(client.get("/api/v1/companies", headers=headers).json()[0]["tenant_id"])
    with SessionLocal() as db:
        order = Order(
            tenant_id=tenant,
            order_no="Y" + uuid.uuid4().hex,
            product_code="POLICY_REPORT",
            amount=99,
            currency="CNY",
            status="created",
            expires_at=datetime.now(UTC) - timedelta(minutes=1),
        )
        db.add(order)
        db.flush()
        payment = Payment(
            tenant_id=tenant,
            order_id=order.id,
            provider="alipay",
            provider_trade_no=order.order_no,
            amount=99,
            currency="CNY",
            status="created",
        )
        db.add(payment)
        db.commit()
        return order.id, payment.id


def test_expiry_requires_confirmed_provider_close_and_late_success_is_audited(monkeypatch):
    monkeypatch.setattr(
        alipay,
        "call",
        lambda method, business, signer: (
            {
                "code": "10000",
                "out_trade_no": business["out_trade_no"],
                "trade_status": "WAIT_BUYER_PAY",
            },
            b"{}",
        ),
    )
    with TestClient(app) as client:
        order_id, payment_id = records(client)
        with SessionLocal() as db:
            expire_orders(db)
            assert db.get(Order, order_id).status == "expired"
            payment = db.get(Payment, payment_id)
            assert payment.status == "expired"
            result = settle_payment(
                db,
                payment=payment,
                provider_event_id=uuid.uuid4().hex,
                event_type="TRADE_SUCCESS",
                paid_amount="99.00",
                currency="CNY",
                payload=b"synthetic-late-success",
            )
            assert result.accepted
            assert db.get(Order, order_id).status == "paid"
            assert (
                db.scalar(
                    select(AnalyticsEvent).where(
                        AnalyticsEvent.tenant_id == payment.tenant_id,
                        AnalyticsEvent.name == "payment_late_success",
                    )
                )
                is not None
            )


def test_unknown_provider_result_does_not_expire_order(monkeypatch):
    monkeypatch.setattr(alipay, "call", lambda *args: ({"code": "40004"}, b"{}"))
    with TestClient(app) as client:
        order_id, _ = records(client)
        with SessionLocal() as db:
            expire_orders(db)
            assert db.get(Order, order_id).status == "created"
