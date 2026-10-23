"""Synthetic policy text, real eligibility/source gates and real quota ledger; no mocks."""

import hashlib
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from test_core_workflow import _complete_profile, _register

from app.core.db import SessionLocal
from app.main import app
from app.models.models import (
    ApplicationActivity,
    ApplicationArtifact,
    ApplicationComment,
    EligibilityRule,
    Evidence,
    Opportunity,
    Policy,
    PolicyChunk,
    PolicyVersion,
    UsageBudget,
    UsageRecord,
)
from app.services.policies.eligibility import evaluate_opportunity


def _project(client):
    headers, _ = _register(client, "suggest-evidence-" + uuid.uuid4().hex)
    company = client.get("/api/v1/companies", headers=headers).json()[0]
    assert (
        client.put(
            f"/api/v1/companies/{company['id']}/profile", headers=headers, json=_complete_profile()
        ).status_code
        == 200
    )
    published = client.post(
        f"/api/v1/companies/{company['id']}/profile/publish", headers=headers
    ).json()
    tenant = uuid.UUID(company["tenant_id"])
    with SessionLocal() as db:
        text = "合成政策条款：支持人工智能企业。"
        policy = Policy(
            tenant_id=tenant,
            title="合成建议验收政策",
            level="municipal",
            province="上海市",
            city="上海市",
            status="published",
            content=text,
            source_url="https://example.invalid/synthetic",
            effective_at=datetime.now(UTC) - timedelta(days=1),
            expires_at=datetime.now(UTC) + timedelta(days=90),
            deadline=datetime.now(UTC) + timedelta(days=30),
        )
        db.add(policy)
        db.flush()
        version = PolicyVersion(
            tenant_id=tenant,
            policy_id=policy.id,
            version=1,
            title=policy.title,
            content=text,
            source_url=policy.source_url,
            content_sha256=hashlib.sha256(text.encode()).hexdigest(),
            status="published",
        )
        db.add(version)
        db.flush()
        db.add(
            PolicyChunk(
                tenant_id=tenant,
                policy_id=policy.id,
                policy_version_id=version.id,
                chunk_index=0,
                content=text,
                char_start=0,
                char_end=len(text),
                content_sha256=version.content_sha256,
            )
        )
        db.add(
            EligibilityRule(
                tenant_id=tenant,
                policy_id=policy.id,
                policy_version_id=version.id,
                name="行业条件",
                fact_key="industry",
                operator="eq",
                expected_json={"value": "人工智能"},
                is_hard_gate=True,
                source_quote="支持人工智能企业",
                status="active",
            )
        )
        opportunity = Opportunity(
            tenant_id=tenant,
            company_id=uuid.UUID(company["id"]),
            policy_id=policy.id,
            policy_version_id=version.id,
            profile_version_id=uuid.UUID(published["id"]),
            title=policy.title,
            score=0.8,
        )
        db.add(opportunity)
        db.flush()
        evaluate_opportunity(db, opportunity, published["snapshot_json"])
        db.commit()
        opportunity_id = str(opportunity.id)
        policy_id = policy.id
    created = client.post(
        "/api/v1/applications",
        headers=headers,
        json={
            "company_id": company["id"],
            "opportunity_id": opportunity_id,
            "title": "合成建议链路",
        },
    )
    assert created.status_code == 201, created.text
    application_id = created.json()["id"]
    generated = client.post(
        f"/api/v1/applications/{application_id}/agent-actions",
        headers=headers,
        json={"action": "generate"},
    )
    assert generated.status_code == 200, generated.text
    artifact = generated.json()["artifact"]
    comment = client.post(
        f"/api/v1/applications/{application_id}/comments",
        headers=headers,
        json={
            "body": "核对摘要",
            "artifact_id": artifact["id"],
            "proposed_summary": "人工核验后的合成摘要",
        },
    )
    assert comment.status_code == 201, comment.text
    return headers, tenant, application_id, artifact, comment.json()["id"], policy_id


@pytest.mark.parametrize("scenario", ["current", "withdrawn", "quota", "citation_changed"])
def test_suggestion_with_real_evidence_and_atomic_quota_recovery(scenario):
    with TestClient(app) as client:
        headers, tenant, app_id, source, comment_id, policy_id = _project(client)
        with SessionLocal() as db:
            if scenario == "withdrawn":
                db.get(Policy, policy_id).status = "withdrawn"
            if scenario == "citation_changed":
                evidence = db.scalar(select(Evidence).where(Evidence.tenant_id == tenant))
                assert evidence is not None
                evidence.quote = "合成篡改：这不是支持结论的原文"
            if scenario == "quota":
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
        endpoint = f"/api/v1/applications/{app_id}/comments/{comment_id}/decision"
        response = client.post(endpoint, headers=headers, json={"decision": "accept"})
        expected = {"current": 200, "withdrawn": 409, "quota": 429, "citation_changed": 409}[
            scenario
        ]
        assert response.status_code == expected, response.text
        with SessionLocal() as db:
            count = db.scalar(
                select(func.count())
                .select_from(ApplicationArtifact)
                .where(ApplicationArtifact.application_id == uuid.UUID(app_id))
            )
            usage = db.scalar(
                select(func.count())
                .select_from(UsageRecord)
                .where(
                    UsageRecord.tenant_id == tenant, UsageRecord.meter_key == "generated_documents"
                )
            )
            decision = db.get(ApplicationComment, uuid.UUID(comment_id)).resolution_json
            assert count == usage == (2 if scenario == "current" else 1)
            assert bool(decision) == (scenario == "current")
            if scenario != "current":
                assert (
                    db.scalar(
                        select(func.count())
                        .select_from(ApplicationActivity)
                        .where(
                            ApplicationActivity.application_id == uuid.UUID(app_id),
                            ApplicationActivity.action == "suggestion_resolved",
                        )
                    )
                    == 0
                )
            if scenario == "quota":
                budget = db.scalar(select(UsageBudget).where(UsageBudget.tenant_id == tenant))
                budget.hard_limit = 2
                db.commit()
        if scenario == "quota":
            response = client.post(endpoint, headers=headers, json={"decision": "accept"})
            assert response.status_code == 200, response.text
        if scenario in {"current", "quota"}:
            repeated = client.post(endpoint, headers=headers, json={"decision": "accept"})
            assert repeated.json() == response.json()
            with SessionLocal() as db:
                result = db.get(ApplicationArtifact, uuid.UUID(response.json()["artifact_id"]))
                assert (
                    db.scalar(
                        select(func.count())
                        .select_from(UsageRecord)
                        .where(
                            UsageRecord.tenant_id == tenant,
                            UsageRecord.meter_key == "generated_documents",
                        )
                    )
                    == 2
                )
                assert (
                    db.scalar(
                        select(func.count())
                        .select_from(ApplicationArtifact)
                        .where(ApplicationArtifact.application_id == uuid.UUID(app_id))
                    )
                    == 2
                )
                assert result.status == "draft" and result.version == source["version"] + 1
                assert result.content_json["executive_summary"] == "人工核验后的合成摘要"
