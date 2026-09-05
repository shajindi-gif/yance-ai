import uuid

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.core.db import SessionLocal
from app.main import app
from app.models.models import (
    AgentRun,
    AnalyticsEvent,
    Application,
    ApplicationArtifact,
    Company,
    Opportunity,
    Order,
    Tenant,
    User,
)
from app.services.analytics.events import record_event


def _register(client: TestClient, suffix: str) -> tuple[dict[str, str], str]:
    email = f"admin-metrics-{suffix}@example.com"
    response = client.post(
        "/api/v1/auth/register",
        json={
            "company_name": f"Metrics Company {suffix}",
            "industry": "人工智能",
            "province": "上海市",
            "city": "上海市",
            "owner_name": "Metrics Owner",
            "owner_email": email,
            "owner_password": "integration-password-123",
        },
    )
    assert response.status_code == 201, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}, email


def test_platform_admin_metrics_permissions_provenance_and_safe_resources():
    suffix = uuid.uuid4().hex
    with TestClient(app) as client:
        platform_headers, platform_email = _register(client, f"platform-{suffix}")
        tenant_headers, tenant_email = _register(client, f"tenant-{suffix}")

        with SessionLocal() as db:
            platform_user = db.scalar(select(User).where(User.email == platform_email))
            tenant_user = db.scalar(select(User).where(User.email == tenant_email))
            assert platform_user and tenant_user
            platform_user.is_platform_admin = True
            tenant = db.get(Tenant, tenant_user.tenant_id)
            assert tenant
            tenant.account_stage = "poc"
            company = db.scalar(select(Company).where(Company.tenant_id == tenant.id))
            assert company
            opportunity = Opportunity(
                tenant_id=tenant.id,
                company_id=company.id,
                title="Admin metrics opportunity",
                status="identified",
            )
            application = Application(
                tenant_id=tenant.id,
                company_id=company.id,
                title="Admin metrics application",
                status="draft",
            )
            db.add_all([opportunity, application])
            db.flush()
            db.add(
                ApplicationArtifact(
                    tenant_id=tenant.id,
                    application_id=application.id,
                    created_by=tenant_user.id,
                    title="Metrics artifact",
                    version=1,
                    content_json={"title": "Metrics artifact"},
                    source_snapshot_json={"application_id": str(application.id)},
                    checksum_sha256="a" * 64,
                )
            )
            db.add_all(
                [
                    AgentRun(
                        tenant_id=tenant.id,
                        user_id=tenant_user.id,
                        agent_name="Policy Search Agent",
                        provider="openai-compatible",
                        model="test-model",
                        status="completed",
                        total_tokens=100,
                        cost_usd=0.5,
                    ),
                    AgentRun(
                        tenant_id=tenant.id,
                        user_id=tenant_user.id,
                        agent_name="Policy Search Agent",
                        provider="openai-compatible",
                        model="test-model",
                        status="failed",
                        total_tokens=0,
                        cost_usd=0,
                        error_code="provider_error",
                    ),
                    Order(
                        tenant_id=tenant.id,
                        order_no=f"METRICS-{suffix}",
                        product_code="TEST",
                        amount=123,
                        currency="CNY",
                        status="paid",
                    ),
                ]
            )
            for name in (
                "company_profile_completed",
                "policy_scan_completed",
                "application_created",
                "document_generated",
                "payment_completed",
            ):
                record_event(
                    db,
                    tenant_id=tenant.id,
                    user_id=tenant_user.id,
                    name=name,
                    event_key=f"{name}:metrics:{suffix}",
                )
            db.commit()
            opportunity_id = opportunity.id
            tenant_id = tenant.id

        denied = client.get("/api/v1/admin/investor-metrics", headers=tenant_headers)
        assert denied.status_code == 403

        feedback = client.post(
            "/api/v1/feedback",
            headers=tenant_headers,
            json={"category": "data", "message": "政策来源需要更新", "route": "/opportunities"},
        )
        assert feedback.status_code == 201

        for _ in range(2):
            opened = client.post(
                f"/api/v1/opportunities/{opportunity_id}/opened", headers=tenant_headers
            )
            assert opened.status_code == 204
        with SessionLocal() as db:
            opened_count = db.scalar(
                select(func.count())
                .select_from(AnalyticsEvent)
                .where(
                    AnalyticsEvent.tenant_id == tenant_id,
                    AnalyticsEvent.name == "opportunity_opened",
                )
            )
            assert opened_count == 1

        metrics_response = client.get(
            "/api/v1/admin/investor-metrics", headers=platform_headers
        )
        assert metrics_response.status_code == 200, metrics_response.text
        metrics = metrics_response.json()
        assert metrics["scope"] == "platform"
        assert metrics["totals"]["organizations"] == 2
        assert metrics["totals"]["total_users"] == 2
        assert metrics["totals"]["poc_accounts"] == 1
        assert metrics["totals"]["paying_customers"] == 1
        assert metrics["totals"]["agent_runs"] == 2
        assert metrics["totals"]["successful_runs"] == 1
        assert metrics["totals"]["failed_runs"] == 1
        assert metrics["totals"]["documents_generated"] == 1
        assert metrics["totals"]["llm_cost_usd"] == 0.5
        assert metrics["totals"]["cost_per_run_usd"] == 0.25
        assert metrics["revenue_by_currency"] == [{"currency": "CNY", "amount": 123.0}]
        assert len(metrics["agent_trend_30d"]) == 30
        assert metrics["availability"]["evaluation_metrics"] is False

        users = client.get("/api/v1/admin/resources/users", headers=platform_headers)
        assert users.status_code == 200
        assert users.json()["total"] == 2
        assert "password_hash" not in users.text

        evaluations = client.get("/api/v1/admin/resources/evals", headers=platform_headers)
        assert evaluations.status_code == 200
        assert evaluations.json()["message"] == "No evaluation data yet."

        feedback_rows = client.get(
            "/api/v1/admin/resources/feedback", headers=platform_headers
        )
        assert feedback_rows.status_code == 200
        assert feedback_rows.json()["total"] == 1
        feedback_id = feedback_rows.json()["items"][0]["id"]
        reviewed = client.patch(
            f"/api/v1/admin/feedback/{feedback_id}",
            headers=platform_headers,
            json={"status": "resolved"},
        )
        assert reviewed.status_code == 200

        reclassified = client.patch(
            f"/api/v1/admin/organizations/{tenant_id}",
            headers=platform_headers,
            json={"account_stage": "customer"},
        )
        assert reclassified.status_code == 200
        assert reclassified.json()["account_stage"] == "customer"

        health = client.get("/api/v1/admin/system-health", headers=platform_headers)
        assert health.status_code == 200
        assert health.json()["database"] == "ready"
        assert health.json()["api_latency_history"]["available"] is False
