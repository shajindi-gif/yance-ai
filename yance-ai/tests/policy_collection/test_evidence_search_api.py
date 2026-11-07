"""API-level check of keyword evidence search: auth, isolation, no model calls.

Two things must hold for a customer-facing search endpoint:

1. it is *authenticated* and tenant-scoped (a customer only sees the public library
   plus their own private documents);
2. it never touches an embedding provider, because during this phase the model
   budget is unapproved and a hidden call would be a silent cost.
"""

from __future__ import annotations

import hashlib
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.db import SessionLocal
from app.main import app
from app.models.models import Policy, PolicyChunk, PolicyVersion

URL_PREFIX = "https://test.invalid/api-search/"


def _register(client: TestClient, suffix: str | None = None) -> dict[str, str]:
    # A fixed suffix made the second run of this file collide with the auth
    # rate limiter (429 instead of 201), which looks like a search bug.
    suffix = suffix or uuid.uuid4().hex[:10]
    response = client.post(
        "/api/v1/auth/register",
        json={
            "company_name": f"Search Company {suffix}",
            "industry": "人工智能",
            "province": "上海市",
            "city": "上海市",
            "owner_name": "Search Owner",
            "owner_email": f"policy-search-{suffix}@example.com",
            "owner_password": "integration-password-123",
            "agreed_terms_version": "test-terms",
        },
    )
    assert response.status_code == 201, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _seed_document(db, *, marker: str, tenant_id=None) -> uuid.UUID:
    body = f"{marker} 申报条件：上年度研发投入不低于三百万元。"
    policy = Policy(
        tenant_id=tenant_id,
        title=f"{marker}申报指南",
        level="municipal",
        province="上海市",
        jurisdiction="上海市",
        status="published",
        source_url=f"{URL_PREFIX}{uuid.uuid4().hex}.html",
        content=body,
    )
    db.add(policy)
    db.flush()
    version = PolicyVersion(
        policy_id=policy.id,
        version=1,
        content_sha256=hashlib.sha256(body.encode()).hexdigest(),
        title=policy.title,
        content=body,
        source_url=policy.source_url,
    )
    db.add(version)
    db.flush()
    db.add(
        PolicyChunk(
            policy_id=policy.id,
            policy_version_id=version.id,
            chunk_index=0,
            content=body,
            char_start=0,
            char_end=len(body),
            content_sha256=hashlib.sha256(body.encode()).hexdigest(),
        )
    )
    db.commit()
    return policy.id


@pytest.fixture(autouse=True)
def _clear_register_rate_limit():
    """Registration is IP rate limited; a test file that registers twice must not 429.

    The limiter is deliberately persistent (it guards a real endpoint), so the test
    clears its own key instead of weakening the limit.
    """
    with SessionLocal() as db:
        db.execute(text("DELETE FROM auth_rate_limit WHERE key LIKE 'register:%'"))
        db.commit()
    yield
    with SessionLocal() as db:
        db.execute(text("DELETE FROM auth_rate_limit WHERE key LIKE 'register:%'"))
        db.commit()


@pytest.fixture()
def seeded():
    marker = f"算力补贴{uuid.uuid4().hex[:8]}"
    with SessionLocal() as db:
        public_id = _seed_document(db, marker=marker)
    try:
        yield marker, public_id
    finally:
        with SessionLocal() as db:
            db.execute(text("DELETE FROM policies WHERE source_url LIKE :p"), {"p": f"{URL_PREFIX}%"})
            db.commit()


def test_evidence_search_requires_authentication(seeded):
    marker, _ = seeded
    with TestClient(app) as client:
        response = client.get("/api/v1/policies/evidence-search", params={"q": marker})
    assert response.status_code in {401, 403}


def test_evidence_search_returns_citable_span_without_model(seeded, monkeypatch):
    marker, public_id = seeded

    def _explode(*_args, **_kwargs):  # pragma: no cover - must never be called
        raise AssertionError("keyword search must not call an embedding provider")

    monkeypatch.setattr("app.services.llm.registry.embed_texts", _explode)

    suffix = uuid.uuid4().hex[:8]
    with TestClient(app) as client:
        headers = _register(client, suffix)
        response = client.get(
            "/api/v1/policies/evidence-search",
            params={"q": marker, "limit": 5},
            headers=headers,
        )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["retrieval"] == "keyword_trigram"
    hit = next(item for item in payload["hits"] if item["policy_id"] == str(public_id))
    assert hit["version_id"] and hit["chunk_id"]
    assert hit["char_start"] == 0 and hit["char_end"] > 0
    assert marker in hit["snippet"]
    assert "corpus" in payload and payload["corpus"]["keyword_searchable"] is True


def test_version_reader_preserves_source_and_denies_other_tenant(seeded):
    marker, public_id = seeded
    with TestClient(app) as client:
        headers = _register(client)
        response = client.get('/api/v1/policies/evidence-search', params={'q': marker}, headers=headers)
        hit = next(h for h in response.json()['hits'] if h['policy_id'] == str(public_id))
        path = f"/api/v1/policies/{public_id}/versions/{hit['version_id']}"
        assert client.get(path).status_code in (401, 403)
        version = client.get(path, headers=headers)
        assert version.status_code == 200
        assert marker in version.json()['content']
        # Private documents stay hidden even when their UUIDs are known.
        with SessionLocal() as db:
            policy = db.get(Policy, public_id)
            from app.models.models import Tenant
            tenant = Tenant(name='Synthetic private version tenant', slug=uuid.uuid4().hex)
            db.add(tenant)
            db.flush()
            policy.tenant_id = tenant.id
            db.commit()
        assert client.get(path, headers=headers).status_code == 404


def test_corpus_counts_do_not_reveal_another_tenants_private_documents(seeded):
    from app.services.policy_collection.keyword_search import searchable_counts
    marker, public_id = seeded
    with SessionLocal() as db:
        from app.models.models import Tenant
        before = searchable_counts(db)
        tenant = Tenant(name='Synthetic corpus privacy tenant', slug=uuid.uuid4().hex)
        db.add(tenant)
        db.flush()
        policy = db.get(Policy, public_id)
        policy.tenant_id = tenant.id
        db.commit()
        public = searchable_counts(db)
        scoped = searchable_counts(db, tenant.id)
        assert public['searchable_policies'] == before['searchable_policies'] - 1
        assert scoped['searchable_policies'] == before['searchable_policies']
        assert scoped['chunks'] > public['chunks']
