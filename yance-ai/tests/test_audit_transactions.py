"""Synthetic PostgreSQL concurrency and invoice contract tests; no providers."""
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from test_invoice_flow import _paid_order, _register
from test_payment_settlement import _records

from app.core.db import SessionLocal
from app.main import app
from app.models.models import AnalyticsEvent, Entitlement, Invoice, Payment, PaymentEvent, Tenant
from app.services.payments.settlement import settle_payment

pytestmark = [pytest.mark.e2e, pytest.mark.skipif(os.getenv("APP_ENV") != "test", reason="isolated PostgreSQL required")]


@pytest.mark.parametrize("same_event", [True, False])
def test_concurrent_callback_grants_exactly_one_entitlement(same_event):
    order, payment, product = _records()
    suffix = uuid.uuid4().hex
    order.order_no = suffix
    payment.provider_trade_no = f"audit-{suffix}"
    product.code = f"AUDIT_{suffix}"
    order.product_code = product.code
    with SessionLocal() as db:
        db.add(Tenant(id=order.tenant_id, name="合成交易租户", slug=f"txn-{suffix}"))
        db.add(product)
        db.flush()
        db.add(order)
        db.flush()
        db.add(payment)
        db.commit()
    payment_id, order_id = payment.id, order.id
    barrier = Barrier(6)
    def callback(index):
        with SessionLocal() as db:
            loaded = db.get(Payment, payment_id)
            barrier.wait(timeout=10)
            return settle_payment(db, payment=loaded, provider_event_id=f"audit-{suffix}-{'same' if same_event else index}", event_type="TRADE_SUCCESS", paid_amount="299.00", currency="CNY", payload=b"synthetic signed-contract equivalent")
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(callback, range(6)))
    assert all(result.accepted for result in results)
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(Entitlement).where(Entitlement.order_id == order_id)) == 1
        assert db.scalar(select(func.count()).select_from(AnalyticsEvent).where(AnalyticsEvent.event_key == f"payment_completed:{order_id}")) == 1
        assert db.scalar(select(func.count()).select_from(PaymentEvent).where(PaymentEvent.payment_id == payment_id)) == (1 if same_event else 6)


def test_invoice_retries_share_request_and_amounts_are_server_owned():
    client = TestClient(app)
    headers, _ = _register(f"audit-{uuid.uuid4().hex}")
    order_id = _paid_order(headers)
    payload = {"order_id":order_id, "title":"合成发票抬头", "tax_number":"91310000MA1FL0000X", "items":[{"name":"forged", "amount":1, "price":1}], "seller_name":"forged seller"}
    first = client.post("/api/v1/invoices", headers=headers, json=payload)
    assert first.status_code == 202, first.text
    second = client.post("/api/v1/invoices", headers=headers, json=payload)
    assert second.status_code == 202
    assert first.json()["id"] == second.json()["id"]
    with SessionLocal() as db:
        invoice = db.get(Invoice, uuid.UUID(first.json()["id"]))
        assert invoice.seller_name != "forged seller"
        assert invoice.items_json[0]["name"] != "forged"
        assert invoice.items_json[0]["amount"] == float(invoice.total_amount)
    changed = client.post("/api/v1/invoices", headers=headers, json={**payload, "title":"另一个抬头"})
    assert changed.status_code == 409
    other, _ = _register(f"foreign-{uuid.uuid4().hex}")
    assert client.get(f"/api/v1/invoices/{first.json()['id']}/voucher", headers=other).status_code == 404


def test_concurrent_invoice_requests_are_idempotent():
    headers, _ = _register(f"invoice-race-{uuid.uuid4().hex}")
    order_id = _paid_order(headers)
    def request(_):
        with TestClient(app) as session:
            response = session.post("/api/v1/invoices", headers=headers, json={"order_id":order_id, "title":"合成并发开票", "tax_number":"91310000MA1FL0000X"})
            assert response.status_code == 202, response.text
            return response.json()["id"]
    with ThreadPoolExecutor(max_workers=5) as pool:
        ids = list(pool.map(request, range(5)))
    assert len(set(ids)) == 1


def test_checkout_reuses_provider_intent_and_blocks_channel_switch(monkeypatch):
    from app.api.routes import payments
    client = TestClient(app)
    headers, _ = _register(f"checkout-{uuid.uuid4().hex}")
    company = client.get("/api/v1/companies", headers=headers).json()[0]
    order = client.post("/api/v1/orders", headers=headers, json={"product_code":"POLICY_REPORT", "resource_id":company["id"]})
    assert order.status_code == 201, order.text
    order_id = order.json()["id"]
    monkeypatch.setattr(payments, "_alipay_available", lambda: True)
    monkeypatch.setattr(payments, "_build_alipay_sign", lambda _: "synthetic-signature")
    first = client.post(f"/api/v1/payments/alipay/page-pay?order_id={order_id}", headers=headers)
    second = client.post(f"/api/v1/payments/alipay/page-pay?order_id={order_id}", headers=headers)
    assert first.status_code == second.status_code == 200, second.text
    assert first.json()["out_trade_no"] == second.json()["out_trade_no"]
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(Payment).where(Payment.order_id == uuid.UUID(order_id))) == 1
    monkeypatch.setattr(payments.wx, "is_wechat_configured", lambda: True)
    def forbidden(*args):
        raise AssertionError("must not create a second provider charge")
    monkeypatch.setattr(payments.wx, "create_native_order", forbidden)
    switched = client.post(f"/api/v1/payments/wechat/native?order_id={order_id}", headers=headers)
    assert switched.status_code == 409
