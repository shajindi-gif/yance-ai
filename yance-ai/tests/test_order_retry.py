import uuid
from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient
from test_funding_os import _register

from app.main import app


def test_order_retry_concurrency_conflict_and_tenant_isolation():
    with TestClient(app) as client:
        headers, _ = _register(client, "order-retry-" + uuid.uuid4().hex)
        other, _ = _register(client, "order-other-" + uuid.uuid4().hex)
        company = client.post(
            "/api/v1/companies", headers=headers, json={"name": "合成订单企业"}
        ).json()
        company2 = {
            "id": str(uuid.uuid4())
        }  # Different payload; no need to consume a second-company quota.
        payload = {
            "product_code": "POLICY_REPORT",
            "resource_id": company["id"],
            "client_request_id": str(uuid.uuid4()),
        }

        def create(_):
            with TestClient(app) as parallel:
                return parallel.post("/api/v1/orders", headers=headers, json=payload)

        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(create, range(4)))
        assert all(r.status_code == 201 for r in results)
        assert len({r.json()["id"] for r in results}) == 1
        first = results[0].json()
        assert client.post("/api/v1/orders", headers=headers, json=payload).json() == first
        assert len(client.get("/api/v1/orders", headers=headers).json()) == 1
        conflict = client.post(
            "/api/v1/orders", headers=headers, json={**payload, "resource_id": company2["id"]}
        )
        assert conflict.status_code == 409
        assert client.post("/api/v1/orders", headers=other, json=payload).status_code == 404
        assert client.get("/api/v1/orders", headers=other).json() == []
        assert (
            client.post(
                "/api/v1/orders", headers=headers, json={**payload, "client_request_id": "bad"}
            ).status_code
            == 422
        )
