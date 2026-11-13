"""Legacy intents need provider-confirmed closure before a new payable reference."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from report_fixture import ready_report
from sqlalchemy import select
from test_funding_os import _register

from app.api.routes import payments
from app.core.db import SessionLocal
from app.main import app
from app.models.models import Order, Payment
from app.services.payments import alipay


@pytest.mark.parametrize("confirmed", [True, False])
def test_old_alipay_intent_is_never_reissued_without_confirmed_close(monkeypatch, confirmed):
    monkeypatch.setattr(payments, "_alipay_available", lambda: True)
    monkeypatch.setattr(payments, "_build_alipay_sign", lambda _: "synthetic-signature")
    monkeypatch.setattr(
        alipay,
        "call",
        lambda method, business, signer: (
            {"code": "10000", "out_trade_no": business["out_trade_no"], "trade_status": "TRADE_CLOSED"}
            if confirmed else {"code": "40004"},
            b"{}",
        ),
    )
    with TestClient(app) as client:
        headers, _ = _register(client, uuid.uuid4().hex)
        company = client.get("/api/v1/companies", headers=headers).json()[0]
        ready_report(company["id"])
        created = client.post("/api/v1/orders", headers=headers, json={
            "product_code": "POLICY_REPORT", "resource_id": company["id"],
        })
        assert created.status_code == 201
        order_id = uuid.UUID(created.json()["id"])
        with SessionLocal() as db:
            order = db.get(Order, order_id)
            order.expires_at = None  # Historical orders are never backfilled.
            reference = order.order_no + "_1790437313"
            db.add(Payment(tenant_id=order.tenant_id, order_id=order.id,
                provider="alipay", provider_trade_no=reference, amount=99,
                currency="CNY", status="created", created_at=datetime.now(UTC)-timedelta(days=1)))
            db.commit()
        response = client.post(f"/api/v1/payments/alipay/page-pay?order_id={order_id}", headers=headers)
        assert response.status_code == (200 if confirmed else 409)
        with SessionLocal() as db:
            rows = list(db.scalars(select(Payment).where(Payment.order_id == order_id).order_by(Payment.created_at)))
            assert len(rows) == (2 if confirmed else 1)
            assert rows[0].status == ("expired" if confirmed else "created")
            assert db.get(Order, order_id).expires_at is None
            if confirmed:
                assert response.json()["out_trade_no"] != reference
