"""Two tenants × four actual membership roles; synthetic server-side boundaries."""
import asyncio
import os
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from test_audit_auth_lifecycle import _account

from app.core.db import SessionLocal
from app.core.security import create_access_token
from app.main import app
from app.models.models import Company, Membership, Policy, User, UserRole
from app.services.policies.ingestion import version_and_chunk_policy

pytestmark = [pytest.mark.e2e, pytest.mark.skipif(os.getenv("APP_ENV") != "test", reason="isolated PostgreSQL required")]


@pytest.mark.parametrize("role", list(UserRole))
def test_two_tenants_role_matrix_read_write_search_and_scan(role, monkeypatch):
    async def fake_embed(inputs):
        return [[0.25]*1024 for _ in inputs]
    monkeypatch.setattr("app.services.policies.ingestion.embed_texts", fake_embed)
    monkeypatch.setattr("app.services.llm.registry.embed_texts", fake_embed)
    with TestClient(app) as client:
        _, a = _account(client)
        _, b = _account(client)
        ca = client.get("/api/v1/companies", headers=a).json()[0]
        cb = client.get("/api/v1/companies", headers=b).json()[0]
        tenant_id = uuid.UUID(ca["tenant_id"])
        with SessionLocal() as db:
            user = User(tenant_id=tenant_id, email=f"{role}-{uuid.uuid4().hex}@example.com", full_name="合成角色用户", password_hash="unused-test-only", role=role)
            db.add(user)
            db.flush()
            db.add(Membership(tenant_id=tenant_id, user_id=user.id, role=role, status="active"))
            policy = Policy(tenant_id=uuid.UUID(cb["tenant_id"]), title="外国租户私有政策合成样例", content="合成检索政策，人工智能企业研发补贴。", status="published", effective_at=datetime.now(UTC)-timedelta(days=1), expires_at=datetime.now(UTC)+timedelta(days=90), deadline=datetime.now(UTC)+timedelta(days=30))
            db.add(policy)
            db.flush()
            asyncio.run(version_and_chunk_policy(db, policy))
            db.commit()
            token = create_access_token(user_id=user.id, tenant_id=tenant_id, role=role.value)
            policy_id = str(policy.id)
        headers = {"Authorization":f"Bearer {token}"}
        assert client.get(f"/api/v1/companies/{ca['id']}", headers=headers).status_code == 200
        assert client.get(f"/api/v1/companies/{cb['id']}", headers=headers).status_code == 404
        assert client.get(f"/api/v1/policies/{policy_id}", headers=headers).status_code == 404
        changed = client.put(f"/api/v1/companies/{ca['id']}", headers=headers, json={"name":"合成企业修改"})
        assert changed.status_code == (403 if role == UserRole.viewer else 200)
        foreign_change = client.put(f"/api/v1/companies/{cb['id']}", headers=headers, json={"name":"不得写入"})
        assert foreign_change.status_code == (403 if role == UserRole.viewer else 404)
        results = client.post("/api/v1/policies/search", headers=headers, data={"query":"人工智能企业研发补贴"})
        assert results.status_code == 200, results.text
        assert policy_id not in {item["id"] for item in results.json()}
        scan = client.post("/api/v1/policy-scans", headers=headers, json={"company_id":cb["id"]})
        assert scan.status_code == (403 if role == UserRole.viewer else 404)
        with SessionLocal() as db:
            assert db.get(Company, uuid.UUID(cb["id"])).name != "不得写入"
