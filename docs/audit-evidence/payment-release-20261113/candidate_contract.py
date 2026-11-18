"""PG16 candidate contract using synthetic records and no real provider calls."""
import hashlib
import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import settings
from app.core.db import SessionLocal
from app.main import app
from app.models.models import Company, Deliverable, Entitlement, Order, Payment, Task, User
from app.services.payments import alipay
from app.services.payments.settlement import settle_payment
from app.services.report.pdf import generate_match_report_pdf

assert settings.app_env == "test" and settings.database_url.split("?")[0].endswith("_test")
assert not settings.email_enabled and not settings.sms_enabled
assert not settings.alipay_app_id and not settings.wxpay_mch_id


def register(client):
    suffix = uuid.uuid4().hex
    response = client.post("/api/v1/auth/register", json={
        "company_name": "隔离付款验收企业", "owner_email": suffix + "@example.com",
        "owner_name": "合成用户", "owner_password": "synthetic-contract-password-01",
        "agreed_terms_version": "2026-10-30",
    })
    assert response.status_code == 201, response.status_code
    return {"Authorization": "Bearer " + response.json()["access_token"]}


source = uuid.uuid4().bytes
with TestClient(app, client=(f"127.3.{source[0]}.{source[1]}", 50000)) as client:
    owner = register(client)
    other = register(client)
    company = client.get("/api/v1/companies", headers=owner).json()[0]
    with SessionLocal() as db:
        entity = db.get(Company, uuid.UUID(company["id"]))
        task = Task(tenant_id=entity.tenant_id, company_id=entity.id, task_type="policy_scan",
                    title="合成验收任务", status="delivered")
        db.add(task); db.flush()
        data = generate_match_report_pdf(entity, [], [])
        report = Deliverable(tenant_id=entity.tenant_id, task_id=task.id, company_id=entity.id,
            deliverable_type="policy_scan", title="合成付款合同报告",
            content_json={"total_matches": 1, "synthetic_payment_contract_only": True},
            frozen_pdf=data, frozen_pdf_sha256=hashlib.sha256(data).hexdigest(), status="generated")
        db.add(report); db.commit()
    response = client.post("/api/v1/orders", headers=owner, json={
        "product_code": "POLICY_REPORT", "resource_id": company["id"],
    })
    assert response.status_code == 201, response.status_code
    order_id = uuid.UUID(response.json()["id"])
    with SessionLocal() as db:
        order = db.get(Order, order_id)
        assert order.expires_at is not None
        payment = Payment(tenant_id=order.tenant_id, order_id=order.id, provider="alipay",
            provider_trade_no=order.order_no + "_1790437313", amount=order.amount,
            currency=order.currency, status="created")
        db.add(payment); db.commit()
        reference, payment_id = payment.provider_trade_no, payment.id
    url = "/api/v1/orders/by-no/" + reference
    assert client.get(url, headers=owner).status_code == 200
    assert client.get(url, headers=other).status_code == 404
    assert client.get(url).status_code == 401
    # Return lookup does not manufacture a payment.
    assert client.get(url, headers=owner).json()["status"] == "created"
    assert client.post(f"/api/v1/payments/alipay/query?order_id={order_id}", headers=owner).status_code == 503
    with SessionLocal() as db:
        payment = db.get(Payment, payment_id)
        for _ in range(2):
            result = settle_payment(db, payment=payment, provider_event_id="synthetic-pg16-paid:" + reference,
                event_type="synthetic-contract", paid_amount="99.00", currency="CNY", payload=b"synthetic")
            assert result.accepted
        assert len(list(db.scalars(select(Entitlement).where(Entitlement.order_id == order_id)))) == 1
    user_id = uuid.UUID(client.get("/api/v1/auth/me", headers=owner).json()["id"])
    with SessionLocal() as db:
        db.get(User, user_id).is_platform_admin = True
        db.commit()
    calls = []
    def refund_gateway(method, business, signer):
        assert method == "alipay.trade.refund"
        calls.append(business["out_request_no"])
        return {"code": "10000", "out_trade_no": reference, "trade_no": "synthetic-refund",
                "refund_fee": "99.00"}, b"synthetic-refund-response"
    alipay.call = refund_gateway
    body = {"reason": "隔离合同验收", "idempotency_key": str(uuid.uuid4())}
    url = f"/api/v1/admin/orders/{order_id}/refund"
    assert client.post(url, headers=other, json=body).status_code == 403
    for _ in range(2):
        response = client.post(url, headers=owner, json=body)
        assert response.status_code == 200, response.status_code
        assert response.json()["status"] == "succeeded"
    assert len(calls) == 1
    with SessionLocal() as db:
        assert db.get(Order, order_id).status == "refunded"
        assert db.scalar(select(Entitlement).where(Entitlement.order_id == order_id)).status == "revoked"
print("PG16_SYNTHETIC_TENANT_RETURN_SETTLEMENT_REFUND_REPLAY_PASSED")
