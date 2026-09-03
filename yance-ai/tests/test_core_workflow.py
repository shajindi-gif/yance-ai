import os
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.api.routes import auth
from app.core.db import SessionLocal
from app.main import app
from app.models.models import Membership, Opportunity, Policy, PolicyScan
from app.services.oss import get_oss_storage

pytestmark = pytest.mark.skipif(
    os.getenv("APP_ENV") != "test",
    reason="Core workflow integration tests require the migrated PostgreSQL CI database",
)


class FakeStorage:
    def __init__(self):
        self.size = 0

    def presign_put(self, object_key: str, content_type: str) -> str:
        return f"https://upload.invalid/{object_key}?content-type={content_type}"

    def exists(self, _object_key: str) -> bool:
        return True

    def object_size(self, _object_key: str) -> int:
        return self.size


def _register(client: TestClient, suffix: str) -> tuple[dict[str, str], str]:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "company_name": f"Workflow Company {suffix}",
            "industry": "人工智能",
            "province": "上海市",
            "city": "上海市",
            "owner_email": f"owner-{suffix}@example.com",
            "owner_name": "Workflow Owner",
            "owner_password": "integration-password-123",
        },
    )
    assert response.status_code == 201, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}, token


def _complete_profile() -> dict:
    return {
        "industry": "人工智能",
        "province": "上海市",
        "city": "上海市",
        "registered_address": "上海市徐汇区测试路 1 号",
        "founded_date": "2022-01-15",
        "company_scale": "小型",
        "employee_count": 42,
        "revenue_stage": "成长期",
        "annual_revenue": 12_000_000,
        "funding_stage": "A轮",
        "high_tech_status": "准备申报",
        "tech_sme_status": "已认定",
        "specialized_sme_status": "未认定",
        "intellectual_property": ["软件著作权 3 项"],
        "core_products": ["企业知识管理平台"],
        "rd_summary": "持续进行大模型检索与企业工作流研发。",
        "rd_expense_ratio": 12.5,
        "talent_summary": "研发人员 20 人。",
        "projects": ["企业知识智能化项目"],
        "current_needs": ["研发补贴", "高企申报"],
    }


def test_persisted_company_to_application_workflow(monkeypatch):
    suffix = uuid.uuid4().hex
    fake_storage = FakeStorage()
    app.dependency_overrides[get_oss_storage] = lambda: fake_storage
    auth._register_rate.clear()

    async def fake_embed(_inputs: list[str]) -> list[list[float]]:
        return [[0.25] * 1024]

    monkeypatch.setattr("app.services.report.matcher.embed_texts", fake_embed)

    try:
        with TestClient(app) as client:
            headers, _ = _register(client, suffix)
            companies = client.get("/api/v1/companies", headers=headers)
            assert companies.status_code == 200
            company_id = companies.json()[0]["id"]

            with SessionLocal() as db:
                membership_count = db.scalar(
                    select(func.count()).select_from(Membership).where(
                        Membership.tenant_id == uuid.UUID(companies.json()[0]["tenant_id"])
                    )
                )
                assert membership_count == 1

                policy = Policy(
                    title="上海市人工智能企业研发支持政策",
                    issuing_authority="测试政策发布机关",
                    level="municipal",
                    province="上海市",
                    city="上海市",
                    industry="人工智能",
                    policy_type="subsidy",
                    source_url="https://policy.example.invalid/source",
                    content="支持人工智能企业研发费用投入，申报需提供知识产权与研发费用材料。",
                    support_amount="以政策原文为准",
                    status="published",
                    embedding=[0.25] * 1024,
                )
                db.add(policy)
                db.commit()

            profile_response = client.get(
                f"/api/v1/companies/{company_id}/profile", headers=headers
            )
            assert profile_response.status_code == 200
            assert profile_response.json()["published_version"] is None

            unpublished_scan = client.post(
                "/api/v1/policy-scans",
                headers=headers,
                json={"company_id": company_id},
            )
            assert unpublished_scan.status_code == 409

            legacy_scan_task = client.post(
                "/api/v1/tasks",
                headers=headers,
                json={"company_id": company_id, "task_type": "policy_scan"},
            )
            assert legacy_scan_task.status_code == 409

            unsupported_draft = client.post(
                "/api/v1/tasks",
                headers=headers,
                json={"company_id": company_id, "task_type": "application_draft"},
            )
            assert unsupported_draft.status_code == 501

            manual_opportunity = client.post(
                "/api/v1/opportunities", headers=headers, json={}
            )
            assert manual_opportunity.status_code == 501

            updated_profile = client.put(
                f"/api/v1/companies/{company_id}/profile",
                headers=headers,
                json=_complete_profile(),
            )
            assert updated_profile.status_code == 200, updated_profile.text
            assert updated_profile.json()["completeness_score"] == 100

            published = client.post(
                f"/api/v1/companies/{company_id}/profile/publish", headers=headers
            )
            assert published.status_code == 201, published.text
            assert published.json()["version"] == 1
            assert published.json()["snapshot_json"]["annual_revenue"] == 12_000_000

            fake_storage.size = 2048
            presigned = client.post(
                "/api/v1/documents/presign-upload",
                headers=headers,
                json={
                    "filename": "company-profile.pdf",
                    "content_type": "application/pdf",
                    "company_id": company_id,
                    "size_bytes": fake_storage.size,
                },
            )
            assert presigned.status_code == 201, presigned.text
            document_id = presigned.json()["document"]["id"]
            completed_upload = client.post(
                f"/api/v1/documents/{document_id}/complete", headers=headers, json={}
            )
            assert completed_upload.status_code == 200, completed_upload.text
            assert completed_upload.json()["status"] == "uploaded"
            assert completed_upload.json()["ingestion_status"] == "pending"

            idempotency_key = f"scan-{suffix}"
            scan_response = client.post(
                "/api/v1/policy-scans",
                headers={**headers, "Idempotency-Key": idempotency_key},
                json={"company_id": company_id},
            )
            assert scan_response.status_code == 202, scan_response.text
            scan_id = scan_response.json()["id"]

            repeated = client.post(
                "/api/v1/policy-scans",
                headers={**headers, "Idempotency-Key": idempotency_key},
                json={"company_id": company_id},
            )
            assert repeated.status_code == 202
            assert repeated.json()["id"] == scan_id

            scan_detail = client.get(f"/api/v1/policy-scans/{scan_id}", headers=headers)
            assert scan_detail.status_code == 200
            assert scan_detail.json()["status"] == "completed"
            assert scan_detail.json()["total_opportunities"] >= 1

            opportunities = client.get(
                f"/api/v1/opportunities?scan_id={scan_id}", headers=headers
            )
            assert opportunities.status_code == 200
            assert len(opportunities.json()) == scan_detail.json()["total_opportunities"]
            assert len({item["policy_id"] for item in opportunities.json()}) == len(
                opportunities.json()
            )
            opportunity = opportunities.json()[0]
            assert opportunity["eligibility_status"] == "NEED_MORE_INFORMATION"
            assert opportunity["policy_snapshot_json"]["source_url"].startswith("https://")

            with SessionLocal() as db:
                assert (
                    db.scalar(
                        select(func.count()).select_from(PolicyScan).where(
                            PolicyScan.idempotency_key == idempotency_key
                        )
                    )
                    == 1
                )
                assert (
                    db.scalar(
                        select(func.count()).select_from(Opportunity).where(
                            Opportunity.scan_id == uuid.UUID(scan_id)
                        )
                    )
                    == scan_detail.json()["total_opportunities"]
                )

            application = client.post(
                "/api/v1/applications",
                headers=headers,
                json={
                    "company_id": company_id,
                    "opportunity_id": opportunity["id"],
                    "title": "上海市人工智能企业研发支持政策申报",
                },
            )
            assert application.status_code == 201, application.text
            application_id = application.json()["id"]
            workspace = client.get(f"/api/v1/applications/{application_id}", headers=headers)
            assert workspace.status_code == 200
            assert workspace.json()["company_name"] == f"Workflow Company {suffix}"
            assert workspace.json()["requirements"]
            assert workspace.json()["activities"][0]["action"] == "application_created"

            requirement_id = workspace.json()["requirements"][0]["id"]
            requirement_update = client.patch(
                f"/api/v1/applications/{application_id}/requirements/{requirement_id}",
                headers=headers,
                json={"status": "collecting"},
            )
            assert requirement_update.status_code == 204

            preparing = client.patch(
                f"/api/v1/applications/{application_id}/status",
                headers=headers,
                json={"status": "preparing", "reason": "开始整理材料"},
            )
            assert preparing.status_code == 200
            assert preparing.json()["progress"] == 20

            invalid_transition = client.patch(
                f"/api/v1/applications/{application_id}/status",
                headers=headers,
                json={"status": "completed"},
            )
            assert invalid_transition.status_code == 409

            updated_workspace = client.get(
                f"/api/v1/applications/{application_id}", headers=headers
            )
            assert updated_workspace.status_code == 200
            assert updated_workspace.json()["requirements"][0]["status"] == "collecting"
            assert updated_workspace.json()["activities"][0]["action"] == "status_changed"

            second_company = client.post(
                "/api/v1/companies",
                headers=headers,
                json={"name": "Unrelated Company"},
            )
            assert second_company.status_code == 201
            mismatch = client.post(
                "/api/v1/applications",
                headers=headers,
                json={
                    "company_id": second_company.json()["id"],
                    "opportunity_id": opportunity["id"],
                    "title": "Invalid cross-company application",
                },
            )
            assert mismatch.status_code == 409

            other_headers, _ = _register(client, f"other-{suffix}")
            cross_tenant = client.get(
                f"/api/v1/opportunities/{opportunity['id']}", headers=other_headers
            )
            assert cross_tenant.status_code == 404
    finally:
        app.dependency_overrides.pop(get_oss_storage, None)
