"""Regression for acceptance ACC-10: lexical retrieval must not be capped to the newest chunks.

Before the fix only the 500 most recently created chunks were scored lexically,
so once a corpus grew past that, older policies were invisible to the lexical
channel regardless of how well they matched.
"""
import asyncio
import hashlib
import os
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import update

from app.core.db import SessionLocal
from app.models.models import Policy, PolicyChunk, Tenant
from app.services.policies.ingestion import version_and_chunk_policy
from app.services.policies.retrieval import hybrid_policy_candidates

pytestmark = pytest.mark.skipif(os.getenv("APP_ENV") != "test", reason="isolated PostgreSQL required")


def _policy(db, tenant_id, title, content):
    policy = Policy(
        tenant_id=tenant_id, title=title, content=content, status="published",
        effective_at=datetime.now(UTC) - timedelta(days=1),
        expires_at=datetime.now(UTC) + timedelta(days=90),
        deadline=datetime.now(UTC) + timedelta(days=30),
    )
    db.add(policy)
    db.flush()
    version = asyncio.run(version_and_chunk_policy(db, policy))
    return policy, version


def test_oldest_matching_policy_is_found_beyond_600_newer_chunks(monkeypatch):
    async def fake_embed(inputs):
        return [[0.25] * 1024 for _ in inputs]

    monkeypatch.setattr("app.services.policies.ingestion.embed_texts", fake_embed)
    marker = f"量子鹦鹉{uuid.uuid4().hex[:6]}专项扶持"
    with SessionLocal() as db:
        tenant = Tenant(name="合成检索租户", slug=f"lex-{uuid.uuid4().hex[:10]}")
        db.add(tenant)
        db.flush()
        target, _ = _policy(db, tenant.id, "最早入库的目标政策", f"本政策面向{marker}企业，提供研发补贴。")
        filler, filler_version = _policy(db, tenant.id, "填充政策", "填充内容，与目标无关的一般性条款。")
        db.flush()
        base_time = datetime.now(UTC) + timedelta(minutes=1)  # all filler chunks are newer than the target
        for index in range(1, 601):
            text = f"填充条款第{index}条，一般性说明文字。"
            db.add(PolicyChunk(
                policy_id=filler.id, policy_version_id=filler_version.id, tenant_id=tenant.id,
                chunk_index=1000 + index, content=text, char_start=0, char_end=len(text),
                content_sha256=hashlib.sha256(text.encode()).hexdigest(),
                created_at=base_time + timedelta(seconds=index),
            ))
        # Isolate the lexical channel: the vector channel ignores chunks without embeddings.
        db.execute(update(PolicyChunk).where(PolicyChunk.tenant_id == tenant.id).values(embedding=None))
        db.commit()

        candidates = hybrid_policy_candidates(
            db, tenant_id=tenant.id, query=marker, query_vector=[0.25] * 1024, limit=10,
        )
        assert target.id in {item.policy.id for item in candidates}
        db.rollback()
