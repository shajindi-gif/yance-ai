"""Run using archived pre-0033 app code, on a disposable local test database."""

import json
import os
import sys
import uuid
from pathlib import Path

from sqlalchemy.engine import make_url


def main():
    phase, raw_output = sys.argv[1:]
    url = make_url(os.environ["DATABASE_URL"])
    if (
        phase not in {"seed", "verify"}
        or os.environ.get("APP_ENV") != "test"
        or url.host not in {"localhost", "127.0.0.1"}
        or not url.database
        or not url.database.endswith("_test")
        or "prod" in url.database
        or os.environ.get("YANCE_TEST_DATABASE_ACK") != url.database
    ):
        raise RuntimeError("Explicit disposable test database required")
    output = Path(raw_output).resolve()
    if output.is_relative_to(Path(__file__).resolve().parents[2]):
        raise RuntimeError("Compatibility fixture must stay outside repository")
    import app as legacy_package

    if (
        not Path(legacy_package.__file__)
        .resolve()
        .is_relative_to(Path(os.environ["LEGACY_APP_ROOT"]).resolve())
    ):
        raise RuntimeError("The archived legacy app must be imported")
    from fastapi.testclient import TestClient
    from sqlalchemy import text

    from app.core.db import SessionLocal
    from app.main import app
    from app.models.models import Order

    with TestClient(app) as client:
        if phase == "seed":
            email = f"compat-{uuid.uuid4().hex}@example.com"
            registered = client.post(
                "/api/v1/auth/register",
                json={
                    "company_name": "合成迁移企业",
                    "owner_name": "合成用户",
                    "owner_email": email,
                    "owner_password": "synthetic-compat-password-123",
                    "agreed_terms_version": "test-terms",
                },
            )
            assert registered.status_code == 201
            token = registered.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            tenant = uuid.UUID(client.get("/api/v1/auth/me", headers=headers).json()["tenant_id"])
            feedback = client.post(
                "/api/v1/feedback", headers=headers, json={"message": "迁移前合成反馈"}
            )
            assert feedback.status_code == 201
            with SessionLocal() as db:
                order = Order(
                    tenant_id=tenant,
                    order_no=uuid.uuid4().hex,
                    product_code="APPLICATION_PLAN",
                    amount=699,
                    currency="CNY",
                    status="paid",
                )
                db.add(order)
                db.commit()
                data = {
                    "email": email,
                    "order_id": str(order.id),
                    "feedback_id": feedback.json()["id"],
                }
            output.write_text(json.dumps(data))
            output.chmod(0o600)
        else:
            data = json.loads(output.read_text())
            login = client.post(
                "/api/v1/auth/login",
                data={"username": data["email"], "password": "synthetic-compat-password-123"},
            )
            assert login.status_code == 200
            headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
            orders = client.get("/api/v1/orders", headers=headers).json()
            assert any(
                row["id"] == data["order_id"]
                and float(row["amount"]) == 699
                and row["status"] == "paid"
                for row in orders
            )
            created = client.post(
                "/api/v1/feedback",
                headers=headers,
                json={"message": "旧客户端在新库继续提交合成反馈"},
            )
            assert created.status_code == 201
            with SessionLocal() as db:
                key = db.execute(
                    text("SELECT client_request_id FROM feedback WHERE id = CAST(:id AS uuid)"),
                    {"id": created.json()["id"]},
                ).scalar_one()
                assert key is None
            assert "feedback_revision" not in client.get("/api/v1/auth/config").json()
    print(
        json.dumps(
            {
                "phase": phase,
                "legacy_import_verified": True,
                "legacy_feedback_works": True,
                "historical_order_preserved": phase == "verify",
            }
        )
    )


if __name__ == "__main__":
    main()
