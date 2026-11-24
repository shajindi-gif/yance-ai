"""Regression for acceptance ACC-13: the paid match report must not award points it never evaluated.

Before the fix, region/scale/tech/finance each started from a non-zero default
(10/5-8/5/5), so a policy the company had no evidence of matching still scored
roughly 25 points before semantic similarity.
"""
import asyncio
import os
import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.core.db import SessionLocal
from app.models.models import Company, Policy, Tenant
from app.services.policies.ingestion import version_and_chunk_policy
from app.services.report.matcher import match_policies_for_company

pytestmark = pytest.mark.skipif(os.getenv("APP_ENV") != "test", reason="isolated PostgreSQL required")


async def _fake_embed(inputs):
    return [[0.25] * 1024 for _ in inputs]


def test_unevaluated_dimensions_score_zero_and_are_flagged(monkeypatch):
    monkeypatch.setattr("app.services.policies.ingestion.embed_texts", _fake_embed)
    monkeypatch.setattr("app.services.report.matcher.embed_texts", _fake_embed)
    marker = f"无约束合成政策{uuid.uuid4().hex[:6]}"
    with SessionLocal() as db:
        tenant = Tenant(name="合成匹配租户", slug=f"match-{uuid.uuid4().hex[:10]}")
        db.add(tenant)
        db.flush()
        company = Company(tenant_id=tenant.id, name=marker, metadata_json={})
        db.add(company)
        policy = Policy(
            tenant_id=tenant.id, title=marker, content=f"{marker}：本条款仅作一般性说明。",
            status="published", effective_at=datetime.now(UTC) - timedelta(days=1),
            expires_at=datetime.now(UTC) + timedelta(days=90), deadline=datetime.now(UTC) + timedelta(days=30),
        )
        db.add(policy)
        db.flush()
        asyncio.run(version_and_chunk_policy(db, policy))
        db.commit()

        opportunities = asyncio.run(match_policies_for_company(db, company, tenant.id))
        target = next(item for item in opportunities if item.policy_id == policy.id)
        evidence = target.evidence_json
        breakdown = evidence["score_breakdown"]
        for dimension in ("region", "scale", "tech", "finance"):
            assert breakdown[dimension] == 0, (dimension, breakdown)
        assert set(evidence["not_evaluated_dimensions"]) >= {"region", "scale", "tech", "finance"}
        assert evidence["total_score"] == breakdown["semantic"] + breakdown["industry"] + breakdown["qualification"]
        db.rollback()
