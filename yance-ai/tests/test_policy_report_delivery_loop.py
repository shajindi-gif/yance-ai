"""P0-3: register → profile → scan → buy POLICY_REPORT → download with ReportCard gate."""

from __future__ import annotations

import asyncio
import hashlib
import os
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.db import SessionLocal
from app.main import app
from app.models.models import (
    AgentRun,
    Deliverable,
    EligibilityRule,
    Entitlement,
    Order,
    Policy,
    PolicyChunk,
    PolicyVersion,
    Product,
)
from app.services.agents.harness import AgentHarness
from app.services.oss import get_oss_storage
from app.services.report.quality import assert_sellable_report_content

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(
        os.getenv("APP_ENV") != "test",
        reason="Delivery loop requires migrated PostgreSQL test database",
    ),
]


class FakeStorage:
    def __init__(self):
        self.payload = b""

    def presign_put(self, object_key: str, content_type: str) -> str:
        return f"https://upload.invalid/{object_key}?content-type={content_type}"

    def exists(self, _object_key: str) -> bool:
        return True

    def object_size(self, _object_key: str) -> int:
        return len(self.payload)

    def read_bytes(self, _object_key: str, max_bytes: int) -> bytes:
        assert len(self.payload) <= max_bytes
        return self.payload


def _register(client: TestClient, suffix: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "company_name": f"Report Loop {suffix}",
            "industry": "人工智能",
            "province": "上海市",
            "city": "上海市",
            "owner_email": f"report-loop-{suffix}@example.com",
            "owner_name": "Report Loop Owner",
            "owner_password": "integration-password-123",
            "agreed_terms_version": "test-terms",
        },
    )
    assert response.status_code == 201, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


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


def test_register_scan_purchase_download_report_cards(monkeypatch):
    suffix = uuid.uuid4().hex
    fake_storage = FakeStorage()
    app.dependency_overrides[get_oss_storage] = lambda: fake_storage

    async def fake_embed(_inputs: list[str]) -> list[list[float]]:
        return [[0.25] * 1024]

    monkeypatch.setattr("app.services.report.matcher.embed_texts", fake_embed)

    try:
        with TestClient(app) as client:
            headers = _register(client, suffix)
            company_id = client.get("/api/v1/companies", headers=headers).json()[0]["id"]
            tenant_id = client.get("/api/v1/companies", headers=headers).json()[0]["tenant_id"]

            with SessionLocal() as db:
                quote = "支持人工智能企业研发费用投入"
                policy_text = f"{quote}，申报需提供知识产权与研发费用材料。"
                policy = Policy(
                    tenant_id=uuid.UUID(tenant_id),
                    title="上海市人工智能企业研发支持政策",
                    issuing_authority="测试政策发布机关",
                    level="municipal",
                    province="上海市",
                    city="上海市",
                    industry="人工智能",
                    policy_type="subsidy",
                    source_url="https://policy.example.invalid/source",
                    content=policy_text,
                    support_amount="以政策原文为准",
                    effective_at=datetime.now(UTC) - timedelta(days=30),
                    expires_at=datetime.now(UTC) + timedelta(days=365),
                    deadline=datetime.now(UTC) + timedelta(days=60),
                    status="published",
                    embedding=[0.25] * 1024,
                )
                db.add(policy)
                db.flush()
                version = PolicyVersion(
                    policy_id=policy.id,
                    tenant_id=uuid.UUID(tenant_id),
                    version=1,
                    content_sha256=hashlib.sha256(policy_text.encode()).hexdigest(),
                    title=policy.title,
                    issuer=policy.issuing_authority,
                    region=policy.jurisdiction,
                    industry=policy.industry,
                    policy_type=policy.policy_type,
                    source_url=policy.source_url,
                    content=policy_text,
                    status="published",
                )
                db.add(version)
                db.flush()
                db.add(
                    PolicyChunk(
                        policy_id=policy.id,
                        policy_version_id=version.id,
                        tenant_id=uuid.UUID(tenant_id),
                        chunk_index=0,
                        content=policy_text,
                        char_start=0,
                        char_end=len(policy_text),
                        content_sha256=hashlib.sha256(policy_text.encode()).hexdigest(),
                        metadata_json={"source": policy.source_url},
                        embedding=[0.25] * 1024,
                    )
                )
                db.add(
                    EligibilityRule(
                        policy_id=policy.id,
                        policy_version_id=version.id,
                        name="人工智能行业要求",
                        fact_key="industry",
                        operator="eq",
                        expected_json={"value": "人工智能"},
                        is_hard_gate=True,
                        source_quote=quote,
                        article="申报条件",
                        status="active",
                    )
                )
                db.commit()
                policy_id = str(policy.id)

            assert client.put(
                f"/api/v1/companies/{company_id}/profile",
                headers=headers,
                json=_complete_profile(),
            ).status_code == 200
            published = client.post(
                f"/api/v1/companies/{company_id}/profile/publish", headers=headers
            )
            assert published.status_code == 201, published.text

            scan = client.post(
                "/api/v1/policy-scans",
                headers={**headers, "Idempotency-Key": f"report-loop-{suffix}"},
                json={"company_id": company_id},
            )
            assert scan.status_code == 202, scan.text
            workflow_run_id = scan.json()["workflow_run_id"]

            with SessionLocal() as db:
                run_id = db.scalar(
                    select(AgentRun.id).where(
                        AgentRun.workflow_run_id == uuid.UUID(workflow_run_id),
                        AgentRun.tenant_id == uuid.UUID(tenant_id),
                    )
                )
                assert run_id is not None
                asyncio.run(AgentHarness().execute(db, run_id))

            scan_detail = client.get(f"/api/v1/policy-scans/{scan.json()['id']}", headers=headers)
            assert scan_detail.status_code == 200
            assert scan_detail.json()["status"] == "completed"
            assert scan_detail.json()["total_opportunities"] >= 1

            with SessionLocal() as db:
                deliverable = db.scalar(
                    select(Deliverable)
                    .where(
                        Deliverable.tenant_id == uuid.UUID(tenant_id),
                        Deliverable.company_id == uuid.UUID(company_id),
                        Deliverable.deliverable_type == "policy_scan",
                    )
                    .order_by(Deliverable.created_at.desc())
                )
                assert deliverable is not None
                assert deliverable.frozen_pdf.startswith(b"%PDF")
                content = deliverable.content_json or {}
                document = assert_sellable_report_content(content)
                assert document.schema_version == "report-card-v1"
                assert document.total_matches == len(document.opportunities)
                assert document.company_id == uuid.UUID(company_id)
                assert document.scan_id is not None
                target = next(
                    card for card in document.opportunities if str(card.policy_id) == policy_id
                )
                assert target.eligibility_status == "POTENTIALLY_ELIGIBLE"
                assert target.citations
                assert target.citations[0].quote == quote
                assert target.next_step
                assert deliverable.task_id is not None
                task_id = deliverable.task_id
                # Mark task delivered so commerce accepts the artifact.
                from app.models.models import Task

                task = db.get(Task, task_id)
                task.status = "delivered"
                db.commit()
                pdf_bytes = deliverable.frozen_pdf
                deliverable_id = deliverable.id

            order = client.post(
                "/api/v1/orders",
                headers=headers,
                json={
                    "product_code": "POLICY_REPORT",
                    "resource_id": company_id,
                    "client_request_id": str(uuid.uuid4()),
                },
            )
            assert order.status_code == 201, order.text
            order_id = uuid.UUID(order.json()["id"])

            with SessionLocal() as db:
                row = db.get(Order, order_id)
                assert row is not None
                assert row.report_deliverable_id == deliverable_id
                row.status = "paid"
                product = db.scalar(select(Product).where(Product.code == "POLICY_REPORT"))
                db.add(
                    Entitlement(
                        tenant_id=row.tenant_id,
                        order_id=row.id,
                        product_id=product.id,
                        resource_type="report",
                        resource_id=row.resource_id,
                        status="active",
                    )
                )
                db.commit()

            download = client.get(f"/api/v1/reports/{company_id}/download", headers=headers)
            assert download.status_code == 200
            assert download.content == pdf_bytes
            assert download.content.startswith(b"%PDF")
    finally:
        app.dependency_overrides.pop(get_oss_storage, None)
