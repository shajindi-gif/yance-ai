import uuid

from fastapi.testclient import TestClient
from test_core_workflow import _register

from app.core.db import SessionLocal
from app.main import app
from app.models.models import Order, Payment


def test_order_number_lookup_is_tenant_scoped_and_handles_old_attempts():
    with TestClient(app) as client:
        owner, _ = _register(client, uuid.uuid4().hex)
        other, _ = _register(client, uuid.uuid4().hex)
        tenant = client.get("/api/v1/companies", headers=owner).json()[0]["tenant_id"]
        with SessionLocal() as db:
            order = Order(
                tenant_id=uuid.UUID(tenant),
                order_no="Y" + uuid.uuid4().hex,
                product_code="POLICY_REPORT",
                amount=99,
                currency="CNY",
                status="created",
            )
            db.add(order)
            db.flush()
            attempt = order.order_no + "_1790437313"
            db.add(
                Payment(
                    tenant_id=order.tenant_id,
                    order_id=order.id,
                    provider="alipay",
                    provider_trade_no=attempt,
                    amount=99,
                    currency="CNY",
                    status="created",
                )
            )
            db.commit()
            number, order_id = order.order_no, str(order.id)
        for reference in [number, attempt]:
            url = "/api/v1/orders/by-no/" + reference
            response = client.get(url, headers=owner)
            assert response.status_code == 200
            assert response.json()["id"] == order_id
            assert client.get(url, headers=other).status_code == 404
            assert client.get(url).status_code == 401
