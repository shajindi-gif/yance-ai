import uuid
from concurrent.futures import ThreadPoolExecutor

from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import select
from test_core_workflow import _register
from test_payment_expiry import records

from app.core.db import SessionLocal
from app.main import app
from app.models.models import Entitlement, Order, Payment, Refund, User
from app.services.payments import alipay
from app.services.payments.settlement import settle_payment


def paid_order(client):
    order_id, payment_id = records(client)
    with SessionLocal() as db:
        payment = db.get(Payment, payment_id)
        assert settle_payment(
            db,
            payment=payment,
            provider_event_id=uuid.uuid4().hex,
            event_type="synthetic",
            paid_amount="99.00",
            currency="CNY",
            payload=b"{}",
        ).accepted
    headers, _ = _register(client, uuid.uuid4().hex)
    user_id = client.get("/api/v1/auth/me", headers=headers).json()["id"]
    with SessionLocal() as db:
        db.get(User, uuid.UUID(user_id)).is_platform_admin = True
        db.commit()
    return order_id, headers


def test_concurrent_full_refund_replays_and_revokes_once(monkeypatch):
    calls = []

    def gateway(method, business, signer):
        calls.append(business["out_request_no"])
        return {
            "code": "10000",
            "out_trade_no": business["out_trade_no"],
            "trade_no": "TEST-REFUND",
            "refund_fee": "99.00",
        }, b"{}"

    monkeypatch.setattr(alipay, "call", gateway)
    with TestClient(app) as client:
        order_id, headers = paid_order(client)
        data = {"reason": "synthetic acceptance", "idempotency_key": str(uuid.uuid4())}
        path = f"/api/v1/admin/orders/{order_id}/refund"
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(
                pool.map(lambda _: client.post(path, headers=headers, json=data), range(2))
            )
        assert [response.status_code for response in results] == [200, 200]
        assert all(response.json()["status"] == "succeeded" for response in results)
        assert len(calls) == 1
        with SessionLocal() as db:
            assert db.get(Order, order_id).status == "refunded"
            assert (
                db.scalar(select(Entitlement).where(Entitlement.order_id == order_id)).status
                == "revoked"
            )
        assert (
            client.post(path, headers=headers, json={**data, "amount": "1.00"}).status_code == 422
        )
        ordinary, _ = _register(client, uuid.uuid4().hex)
        assert client.post(path, headers=ordinary, json=data).status_code == 403


def test_interrupted_refund_preserves_provider_reference_and_entitlement(monkeypatch):
    calls = []

    def gateway(method, business, signer):
        calls.append(business["out_request_no"])
        if len(calls) == 1:
            raise HTTPException(502, "synthetic interruption")
        return {
            "code": "10000",
            "out_trade_no": business["out_trade_no"],
            "trade_no": "TEST-REFUND",
            "refund_fee": "99.00",
        }, b"{}"

    monkeypatch.setattr(alipay, "call", gateway)
    with TestClient(app) as client:
        order_id, headers = paid_order(client)
        path = f"/api/v1/admin/orders/{order_id}/refund"
        data = {"reason": "synthetic retry", "idempotency_key": str(uuid.uuid4())}
        assert client.post(path, headers=headers, json=data).status_code == 502
        with SessionLocal() as db:
            assert db.get(Order, order_id).status == "paid"
            assert (
                db.scalar(select(Refund).where(Refund.order_id == order_id)).status == "requested"
            )
        assert client.post(path, headers=headers, json=data).status_code == 200
        assert calls[0] == calls[1]
