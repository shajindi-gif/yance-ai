from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.core.db import SessionLocal
from app.main import app
from app.models.models import (
    AnalyticsEvent,
    DemoScenario,
    Invoice,
    Order,
    Payment,
    Tenant,
    User,
)
from app.services.admin.metrics import investor_metrics
from app.services.demo.scenarios import DATASET_VERSION, SCENARIOS, seed_investor_demo


def test_investor_demo_is_complete_idempotent_and_excluded_from_metrics():
    with SessionLocal() as db:
        before = investor_metrics(db)
        first = seed_investor_demo(db, replace=True)
        second = seed_investor_demo(db)
        after = investor_metrics(db)

        assert len(first) == len(SCENARIOS) == 5
        assert [item.id for item in first] == [item.id for item in second]
        assert before["totals"] == after["totals"]
        assert before["revenue_by_currency"] == after["revenue_by_currency"]
        assert before["funnel"] == after["funnel"]

        tenant_ids = select(Tenant.id).where(Tenant.is_demo.is_(True))
        assert db.scalar(select(func.count()).select_from(User).where(User.tenant_id.in_(tenant_ids))) == 0
        assert db.scalar(select(func.count()).select_from(Order).where(Order.tenant_id.in_(tenant_ids))) == 0
        assert db.scalar(select(func.count()).select_from(Payment).where(Payment.tenant_id.in_(tenant_ids))) == 0
        assert db.scalar(select(func.count()).select_from(Invoice).where(Invoice.tenant_id.in_(tenant_ids))) == 0
        assert db.scalar(
            select(func.count()).select_from(AnalyticsEvent).where(AnalyticsEvent.tenant_id.in_(tenant_ids))
        ) == 0

    with TestClient(app) as client:
        catalog_response = client.get("/api/v1/demo/scenarios")
        assert catalog_response.status_code == 200, catalog_response.text
        catalog = catalog_response.json()
        assert catalog["dataset_version"] == DATASET_VERSION
        assert catalog["data_classification"] == "synthetic"
        assert len(catalog["items"]) == 5
        assert all("DEMO" in item["title"] or "演示" in item["title"] for item in catalog["items"])

        for item in catalog["items"]:
            response = client.get(f"/api/v1/demo/scenarios/{item['key']}")
            assert response.status_code == 200, response.text
            detail = response.json()
            assert detail["data_classification"] == "synthetic"
            assert detail["company"]["name"].startswith("DEMO ·")
            assert detail["document"]["ingestion_status"] == "completed"
            assert detail["scan"]["status"] == "completed"
            assert detail["opportunity"]["eligibility"] in {
                "ELIGIBLE", "POTENTIALLY_ELIGIBLE", "NEED_MORE_INFORMATION"
            }
            assert detail["eligibility"]["review_status"] == "system_verified"
            assert detail["evidence"] and all(evidence["verified"] for evidence in detail["evidence"])
            assert detail["application"]["requirements"]
            assert detail["application"]["tasks"]
            assert [step["type"] for step in detail["agent_run"]["steps"]] == [
                "plan", "retrieve", "reason", "act", "verify", "finish"
            ]
            assert detail["artifact"]["formats"] == ["docx", "pdf", "xlsx", "json"]
            assert detail["next_best_action"]

        key = catalog["items"][0]["key"]
        detail = client.get(f"/api/v1/demo/scenarios/{key}").json()
        artifact_id = detail["artifact"]["id"]
        expected = {
            "docx": ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", b"PK"),
            "pdf": ("application/pdf", b"%PDF"),
            "xlsx": ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", b"PK"),
            "json": ("application/json", b"{"),
        }
        for format_name, (content_type, signature) in expected.items():
            download = client.get(
                f"/api/v1/demo/scenarios/{key}/artifacts/{artifact_id}/download",
                params={"format": format_name},
            )
            assert download.status_code == 200, download.text
            assert download.headers["content-type"].startswith(content_type)
            assert download.content.startswith(signature)
            assert download.headers["x-content-type-options"] == "nosniff"

        wrong_artifact = client.get(
            f"/api/v1/demo/scenarios/{key}/artifacts/00000000-0000-0000-0000-000000000000/download"
        )
        assert wrong_artifact.status_code == 404


def test_public_demo_fails_closed_for_non_demo_tenant():
    with SessionLocal() as db:
        scenario = db.scalar(select(DemoScenario).order_by(DemoScenario.display_order))
        assert scenario
        tenant = db.get(Tenant, scenario.tenant_id)
        assert tenant and tenant.is_demo
        tenant.is_demo = False
        db.commit()
        key = scenario.key

    try:
        response = TestClient(app).get(f"/api/v1/demo/scenarios/{key}")
        assert response.status_code == 404
    finally:
        with SessionLocal() as db:
            tenant = db.scalar(select(Tenant).where(Tenant.demo_dataset_key == key))
            assert tenant
            tenant.is_demo = True
            db.commit()
