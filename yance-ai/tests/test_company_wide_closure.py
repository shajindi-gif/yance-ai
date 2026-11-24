"""Real isolated API/database regressions; synthetic business data, no providers."""

import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from test_funding_os import _register
from test_v2_suggestion_evidence import _project

from app.core.db import SessionLocal
from app.main import app
from app.models.models import Feedback, Order, UsageBudget, UsageRecord, User


def test_manual_revisions_remain_available_when_generation_budget_is_exhausted():
    with TestClient(app) as client:
        headers, tenant, app_id, source, _, _ = _project(client)
        with SessionLocal() as db:
            db.add(
                UsageBudget(
                    tenant_id=tenant,
                    scope_type="organization",
                    scope_id=tenant,
                    meter_key="generated_documents",
                    hard_limit=1,
                    active=True,
                )
            )
            db.commit()
        edited = client.post(
            f"/api/v1/applications/{app_id}/artifacts/{source['id']}/edit",
            headers=headers,
            json={"executive_summary": "客户自行补充的合成摘要"},
        )
        assert edited.status_code == 201, edited.text
        comment = client.post(
            f"/api/v1/applications/{app_id}/comments",
            headers=headers,
            json={
                "body": "合成人工建议",
                "artifact_id": edited.json()["id"],
                "proposed_summary": "客户授权团队修改的合成摘要",
            },
        )
        assert comment.status_code == 201, comment.text
        endpoint = f"/api/v1/applications/{app_id}/comments/{comment.json()['id']}/decision"
        accepted = client.post(endpoint, headers=headers, json={"decision": "accept"})
        assert accepted.status_code == 200, accepted.text
        assert (
            client.post(endpoint, headers=headers, json={"decision": "accept"}).json()
            == accepted.json()
        )
        with SessionLocal() as db:
            assert (
                db.scalar(
                    select(func.count())
                    .select_from(UsageRecord)
                    .where(
                        UsageRecord.tenant_id == tenant,
                        UsageRecord.meter_key == "generated_documents",
                    )
                )
                == 1
            )
        # A genuinely new generated artifact still uses the existing quota.
        blocked = client.post(
            f"/api/v1/applications/{app_id}/agent-actions",
            headers=headers,
            json={"action": "generate"},
        )
        assert blocked.status_code == 429, blocked.text


def test_unaccepted_product_orders_fail_on_server_while_historical_orders_remain_visible():
    with TestClient(app) as client:
        headers, me = _register(client, uuid.uuid4().hex)
        company = client.get("/api/v1/companies", headers=headers).json()[0]
        catalogue = {p["code"]: p for p in client.get("/api/v1/products").json()}
        assert catalogue["POLICY_REPORT"]["purchase_available"] is True
        for code in ["POLICY_DIAGNOSIS", "APPLICATION_PLAN"]:
            assert catalogue[code]["purchase_available"] is False
            with SessionLocal() as db:
                old = Order(
                    tenant_id=uuid.UUID(me["tenant_id"]),
                    order_no=uuid.uuid4().hex,
                    product_code=code,
                    amount=299 if code == "POLICY_DIAGNOSIS" else 699,
                    currency="CNY",
                    status="paid",
                    resource_type="diagnosis",
                    resource_id=uuid.uuid4(),
                )
                db.add(old)
                db.commit()
                old_id = str(old.id)
            response = client.post(
                "/api/v1/orders",
                headers=headers,
                json={"product_code": code, "resource_id": company["id"]},
            )
            assert response.status_code == 409, response.text
            assert response.json()["detail"]["code"] == "product_not_available_for_new_orders"
            assert any(
                row["id"] == old_id for row in client.get("/api/v1/orders", headers=headers).json()
            )
        assert (
            client.post(
                "/api/v1/orders",
                headers=headers,
                json={"product_code": "POLICY_REPORT", "resource_id": company["id"]},
            ).status_code
            == 409
        )


@pytest.mark.parametrize("category", ["policy", "sales"])
def test_feedback_actual_persistence_admin_processing_and_private_user_history(category):
    with TestClient(app) as client:
        headers, me = _register(client, uuid.uuid4().hex)
        other, _ = _register(client, uuid.uuid4().hex)
        assert (
            client.post("/api/v1/feedback", headers=headers, json={"message": "  "}).status_code
            == 422
        )
        payload = {
            "category": category,
            "message": " 合成反馈：来源需要更新 ",
            "route": "/feedback",
            "client_request_id": str(uuid.uuid4()),
        }

        def submit(_):
            with TestClient(app) as caller:
                response = caller.post("/api/v1/feedback", headers=headers, json=payload)
                assert response.status_code == 201, response.text
                return response.json()["id"]

        with ThreadPoolExecutor(max_workers=3) as pool:
            ids = list(pool.map(submit, range(3)))
        assert len(set(ids)) == 1
        assert (
            client.post(
                "/api/v1/feedback", headers=headers, json={**payload, "message": "另一条不同内容"}
            ).status_code
            == 409
        )
        feedback_id = ids[0]
        assert client.get("/api/v1/feedback").status_code == 401
        assert client.get("/api/v1/feedback", headers=other).json() == []
        rows = client.get("/api/v1/feedback", headers=headers).json()
        assert rows[0]["id"] == feedback_id and rows[0]["message"] == payload["message"].strip()
        assert (
            client.patch(
                f"/api/v1/admin/feedback/{feedback_id}", headers=other, json={"status": "resolved"}
            ).status_code
            == 403
        )
        with SessionLocal() as db:
            assert (
                db.scalar(
                    select(func.count())
                    .select_from(Feedback)
                    .where(Feedback.user_id == uuid.UUID(me["id"]))
                )
                == 1
            )
            db.get(User, uuid.UUID(me["id"])).is_platform_admin = True
            db.commit()
        assert (
            client.patch(
                f"/api/v1/admin/feedback/{feedback_id}",
                headers=headers,
                json={"status": "reviewing"},
            ).status_code
            == 200
        )
        assert (
            client.patch(
                f"/api/v1/admin/feedback/{feedback_id}",
                headers=headers,
                json={"status": "resolved"},
            ).status_code
            == 200
        )
        assert client.get("/api/v1/feedback", headers=headers).json()[0]["status"] == "resolved"


def test_old_unpaid_unaccepted_order_cannot_create_a_new_provider_intent(monkeypatch):
    from app.api.routes import payments
    from app.models.models import Payment

    monkeypatch.setattr(payments, "_alipay_available", lambda: True)

    def forbidden(*_):
        raise AssertionError("must not call a payment provider for an unaccepted product")

    monkeypatch.setattr(payments, "_build_alipay_sign", forbidden)
    with TestClient(app) as client:
        headers, me = _register(client, uuid.uuid4().hex)
        with SessionLocal() as db:
            order = Order(
                tenant_id=uuid.UUID(me["tenant_id"]),
                order_no=uuid.uuid4().hex,
                product_code="APPLICATION_PLAN",
                amount=699,
                currency="CNY",
                status="created",
            )
            db.add(order)
            db.commit()
            order_id = order.id
        response = client.post(
            f"/api/v1/payments/alipay/page-pay?order_id={order_id}", headers=headers
        )
        assert response.status_code == 409, response.text
        with SessionLocal() as db:
            assert (
                db.scalar(
                    select(func.count()).select_from(Payment).where(Payment.order_id == order_id)
                )
                == 0
            )
            assert db.get(Order, order_id).status == "created"


def test_manual_edit_rejects_new_hard_failure_without_partial_version():
    from app.models.models import ApplicationArtifact, EligibilityResult

    with TestClient(app, raise_server_exceptions=False) as client:
        headers, tenant, app_id, source, _, _ = _project(client)
        with SessionLocal() as db:
            row = db.scalar(select(EligibilityResult).where(EligibilityResult.tenant_id == tenant))
            row.status = "NOT_ELIGIBLE"
            db.commit()
        response = client.post(
            f"/api/v1/applications/{app_id}/artifacts/{source['id']}/edit",
            headers=headers,
            json={"executive_summary": "合成硬门槛变更后尝试修改"},
        )
        assert response.status_code == 409, response.text
        with SessionLocal() as db:
            assert (
                db.scalar(
                    select(func.count())
                    .select_from(ApplicationArtifact)
                    .where(ApplicationArtifact.application_id == uuid.UUID(app_id))
                )
                == 1
            )


def test_same_tenant_viewer_history_does_not_include_owner_feedback():
    from app.core.security import create_access_token
    from app.models.models import Membership

    with TestClient(app) as client:
        owner, me = _register(client, uuid.uuid4().hex)
        tenant = uuid.UUID(me["tenant_id"])
        with SessionLocal() as db:
            user = User(
                tenant_id=tenant,
                email=f"feedback-viewer-{uuid.uuid4().hex}@example.com",
                full_name="合成只读用户",
                password_hash="not-used",
                role="owner",
            )
            db.add(user)
            db.flush()
            db.add(Membership(tenant_id=tenant, user_id=user.id, role="viewer", status="active"))
            db.commit()
            token = create_access_token(
                user_id=user.id, tenant_id=tenant, role="owner", auth_version=user.auth_version
            )
        viewer = {"Authorization": f"Bearer {token}"}
        key = str(uuid.uuid4())
        first = client.post(
            "/api/v1/feedback",
            headers=owner,
            json={"message": "合成负责人反馈", "client_request_id": key},
        )
        second = client.post(
            "/api/v1/feedback",
            headers=viewer,
            json={"message": "合成只读用户反馈", "client_request_id": key},
        )
        assert first.status_code == second.status_code == 201
        assert first.json()["id"] != second.json()["id"]
        assert [x["id"] for x in client.get("/api/v1/feedback", headers=owner).json()] == [
            first.json()["id"]
        ]
        assert [x["id"] for x in client.get("/api/v1/feedback", headers=viewer).json()] == [
            second.json()["id"]
        ]
