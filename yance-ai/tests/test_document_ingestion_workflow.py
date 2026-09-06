import hashlib
import os
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.api.routes import auth
from app.core.db import SessionLocal
from app.main import app
from app.models.models import CompanyFact, Tenant
from app.services.oss import get_oss_storage

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(
        os.getenv("APP_ENV") != "test",
        reason="Document ingestion E2E requires the migrated PostgreSQL CI database",
    ),
]


class MemoryStorage:
    def __init__(self, payload: bytes):
        self.payload = payload

    def presign_put(self, object_key: str, content_type: str) -> str:
        return f"https://upload.invalid/{object_key}?content-type={content_type}"

    def exists(self, _object_key: str) -> bool:
        return True

    def object_size(self, _object_key: str) -> int:
        return len(self.payload)

    def read_bytes(self, _object_key: str, max_bytes: int) -> bytes:
        assert len(self.payload) <= max_bytes
        return self.payload


def _register(client: TestClient, suffix: str) -> tuple[dict[str, str], str, str]:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "company_name": f"Document Intelligence {suffix}",
            "industry": "待补充",
            "province": "上海市",
            "city": "上海市",
            "owner_email": f"document-{suffix}@example.com",
            "owner_name": "Document Owner",
            "owner_password": "integration-password-123",
        },
    )
    assert response.status_code == 201, response.text
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    company = client.get("/api/v1/companies", headers=headers).json()[0]
    return headers, company["id"], company["tenant_id"]


def test_document_ingestion_review_and_profile_provenance():
    suffix = uuid.uuid4().hex
    content = """所属行业：人工智能软件
注册地址：上海市徐汇区测试路 18 号
成立日期：2022年1月15日
员工人数：42 人
年度营业收入：1,200 万元
研发投入占营业收入 12.5%
核心产品：企业政策智能平台、申报工作台
当前需求：研发补贴、高企申报
""".encode()
    storage = MemoryStorage(content)
    app.dependency_overrides[get_oss_storage] = lambda: storage
    auth._register_rate.clear()
    tenant_ids: list[uuid.UUID] = []
    try:
        with TestClient(app) as client:
            headers, company_id, tenant_id = _register(client, suffix)
            tenant_ids.append(uuid.UUID(tenant_id))
            presigned = client.post(
                "/api/v1/documents/presign-upload",
                headers=headers,
                json={
                    "filename": "company-profile.txt",
                    "content_type": "text/plain",
                    "company_id": company_id,
                    "size_bytes": len(content),
                },
            )
            assert presigned.status_code == 201, presigned.text
            document_id = presigned.json()["document"]["id"]

            completed = client.post(
                f"/api/v1/documents/{document_id}/complete", headers=headers, json={}
            )
            assert completed.status_code == 200, completed.text
            assert completed.json()["status"] == "quarantined"
            assert completed.json()["ingestion_status"] == "pending"

            ingested = client.post(
                f"/api/v1/documents/{document_id}/ingest",
                headers=headers,
                json={"force": False},
            )
            assert ingested.status_code == 200, ingested.text
            detail = ingested.json()
            assert detail["document"]["status"] == "active"
            assert detail["document"]["ingestion_status"] == "completed"
            assert detail["document"]["checksum_sha256"] == hashlib.sha256(content).hexdigest()
            assert detail["content"]["parser"] == "text"
            assert detail["chunk_count"] >= 1
            assert len(detail["ingestion_runs"]) == 1
            annual_revenue = next(
                item for item in detail["candidates"] if item["field_key"] == "annual_revenue"
            )
            assert annual_revenue["value_json"]["value"] == 12_000_000

            repeated_completion = client.post(
                f"/api/v1/documents/{document_id}/complete", headers=headers, json={}
            )
            assert repeated_completion.status_code == 200
            assert repeated_completion.json()["status"] == "active"
            assert repeated_completion.json()["ingestion_status"] == "completed"

            idempotent = client.post(
                f"/api/v1/documents/{document_id}/ingest",
                headers=headers,
                json={"force": False},
            )
            assert idempotent.status_code == 200
            assert len(idempotent.json()["ingestion_runs"]) == 1

            reviewed = client.post(
                f"/api/v1/documents/{document_id}/facts/review",
                headers=headers,
                json={
                    "decisions": [
                        {"candidate_id": annual_revenue["id"], "decision": "accept"}
                    ]
                },
            )
            assert reviewed.status_code == 200, reviewed.text
            assert reviewed.json()["profile"]["draft_json"]["annual_revenue"] == 12_000_000

            published = client.post(
                f"/api/v1/companies/{company_id}/profile/publish", headers=headers
            )
            assert published.status_code == 201, published.text
            with SessionLocal() as db:
                fact = db.scalar(
                    select(CompanyFact).where(
                        CompanyFact.profile_version_id == uuid.UUID(published.json()["id"]),
                        CompanyFact.fact_key == "annual_revenue",
                    )
                )
                assert fact.source_document_id == uuid.UUID(document_id)
                assert fact.extraction_method == "document_reviewed"
                assert fact.verification_status == "user_accepted"

            other_headers, _, other_tenant_id = _register(client, f"other-{suffix}")
            tenant_ids.append(uuid.UUID(other_tenant_id))
            hidden = client.get(f"/api/v1/documents/{document_id}", headers=other_headers)
            assert hidden.status_code == 404
    finally:
        app.dependency_overrides.pop(get_oss_storage, None)
        with SessionLocal() as db:
            if tenant_ids:
                db.execute(delete(Tenant).where(Tenant.id.in_(tenant_ids)))
                db.commit()
