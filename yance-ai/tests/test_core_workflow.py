import asyncio
import hashlib
import os
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.api.routes import auth
from app.core.db import SessionLocal
from app.main import app
from app.models.models import (
    AgentRun,
    AgentStep,
    Artifact,
    EligibilityResult,
    EligibilityRule,
    Evidence,
    Membership,
    Opportunity,
    Policy,
    PolicyChunk,
    PolicyScan,
    PolicyVersion,
    ToolCall,
)
from app.services.agents.harness import AgentHarness
from app.services.oss import get_oss_storage
from app.services.policies.eligibility import evaluate_opportunity

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
                    select(func.count())
                    .select_from(Membership)
                    .where(Membership.tenant_id == uuid.UUID(companies.json()[0]["tenant_id"]))
                )
                assert membership_count == 1
                tenant_id = uuid.UUID(companies.json()[0]["tenant_id"])

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
                db.flush()
                policy_text = policy.content or ""
                policy_version = PolicyVersion(
                    policy_id=policy.id,
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
                db.add(policy_version)
                db.flush()
                quote = "支持人工智能企业研发费用投入"
                chunk = PolicyChunk(
                    policy_id=policy.id,
                    policy_version_id=policy_version.id,
                    chunk_index=0,
                    content=policy_text,
                    char_start=0,
                    char_end=len(policy_text),
                    content_sha256=hashlib.sha256(policy_text.encode()).hexdigest(),
                    metadata_json={"source": policy.source_url},
                    embedding=[0.25] * 1024,
                )
                db.add(chunk)
                db.add(
                    EligibilityRule(
                        policy_id=policy.id,
                        policy_version_id=policy_version.id,
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
                private_text = "第一条 企业须在上海市依法注册。"
                private_policy = Policy(
                    tenant_id=tenant_id,
                    title="租户私有政策规则测试",
                    issuing_authority="测试发布机关",
                    province="上海市",
                    policy_type="subsidy",
                    source_url="https://policy.example.invalid/private",
                    content=private_text,
                    status="draft",
                )
                db.add(private_policy)
                db.flush()
                private_version = PolicyVersion(
                    policy_id=private_policy.id,
                    tenant_id=tenant_id,
                    version=1,
                    content_sha256=hashlib.sha256(private_text.encode()).hexdigest(),
                    title=private_policy.title,
                    issuer=private_policy.issuing_authority,
                    region=private_policy.jurisdiction,
                    policy_type=private_policy.policy_type,
                    source_url=private_policy.source_url,
                    content=private_text,
                    status="draft",
                )
                db.add(private_version)
                db.flush()
                db.add(
                    PolicyChunk(
                        policy_id=private_policy.id,
                        policy_version_id=private_version.id,
                        tenant_id=tenant_id,
                        chunk_index=0,
                        content=private_text,
                        char_start=0,
                        char_end=len(private_text),
                        content_sha256=hashlib.sha256(private_text.encode()).hexdigest(),
                        metadata_json={"source": private_policy.source_url},
                    )
                )
                db.commit()
                policy_id = policy.id
                policy_version_id = policy_version.id
                private_policy_id = private_policy.id
                private_version_id = private_version.id

            invalid_rule = client.post(
                "/api/v1/eligibility-rules",
                headers=headers,
                json={
                    "policy_id": str(private_policy_id),
                    "policy_version_id": str(private_version_id),
                    "name": "上海注册要求",
                    "fact_key": "province",
                    "operator": "eq",
                    "expected_json": {"value": "上海市"},
                    "source_quote": "不存在的政策原文",
                },
            )
            assert invalid_rule.status_code == 422
            valid_rule = client.post(
                "/api/v1/eligibility-rules",
                headers=headers,
                json={
                    "policy_id": str(private_policy_id),
                    "policy_version_id": str(private_version_id),
                    "name": "上海注册要求",
                    "fact_key": "province",
                    "operator": "eq",
                    "expected_json": {"value": "上海市"},
                    "source_quote": "企业须在上海市依法注册",
                    "article": "第一条",
                },
            )
            assert valid_rule.status_code == 201, valid_rule.text
            listed_rules = client.get(
                f"/api/v1/eligibility-rules?policy_id={private_policy_id}", headers=headers
            )
            assert listed_rules.status_code == 200
            assert [item["id"] for item in listed_rules.json()] == [valid_rule.json()["id"]]

            other_headers, _ = _register(client, f"other-{suffix}")
            isolated_rules = client.get(
                f"/api/v1/eligibility-rules?policy_id={private_policy_id}",
                headers=other_headers,
            )
            assert isolated_rules.status_code == 404

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

            manual_opportunity = client.post("/api/v1/opportunities", headers=headers, json={})
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
            workflow_run_id = scan_response.json()["workflow_run_id"]
            assert scan_response.json()["status"] == "queued"
            assert workflow_run_id

            repeated = client.post(
                "/api/v1/policy-scans",
                headers={**headers, "Idempotency-Key": idempotency_key},
                json={"company_id": company_id},
            )
            assert repeated.status_code == 202
            assert repeated.json()["id"] == scan_id

            with SessionLocal() as db:
                run_id = asyncio.run(AgentHarness().run_once(db, "integration-worker"))
                assert run_id is not None

            scan_detail = client.get(f"/api/v1/policy-scans/{scan_id}", headers=headers)
            assert scan_detail.status_code == 200
            assert scan_detail.json()["status"] == "completed"
            assert scan_detail.json()["total_opportunities"] >= 1

            opportunities = client.get(f"/api/v1/opportunities?scan_id={scan_id}", headers=headers)
            assert opportunities.status_code == 200
            assert len(opportunities.json()) == scan_detail.json()["total_opportunities"]
            assert len({item["policy_id"] for item in opportunities.json()}) == len(
                opportunities.json()
            )
            opportunity = opportunities.json()[0]
            assert opportunity["eligibility_status"] == "POTENTIALLY_ELIGIBLE"
            assert opportunity["policy_version_id"] == str(policy_version_id)
            assert opportunity["policy_snapshot_json"]["policy_version_id"] == str(
                policy_version_id
            )
            assert opportunity["policy_snapshot_json"]["source_url"].startswith("https://")

            agent_runs = client.get("/api/v1/agent-runs", headers=headers)
            assert agent_runs.status_code == 200, agent_runs.text
            run_summary = next(item for item in agent_runs.json() if item["id"] == str(run_id))
            assert run_summary["status"] == "completed"
            assert run_summary["current_step"] == "finish"
            assert run_summary["total_tokens"] == 0
            assert float(run_summary["cost_usd"]) == 0

            run_detail = client.get(f"/api/v1/agent-runs/{run_id}", headers=headers)
            assert run_detail.status_code == 200, run_detail.text
            assert run_detail.json()["workflow_run_id"] == workflow_run_id
            assert run_detail.json()["workflow_version"] == "v2"
            assert [step["step_type"] for step in run_detail.json()["steps"]] == [
                "plan",
                "retrieve",
                "reason",
                "act",
                "verify",
                "finish",
            ]
            assert all(step["status"] == "completed" for step in run_detail.json()["steps"])
            assert {tool["tool_name"] for tool in run_detail.json()["tool_calls"]} == {
                "policy_match",
                "evaluate_eligibility",
                "render_policy_scan_report",
            }
            assert run_detail.json()["artifacts"][0]["artifact_type"] == "policy_scan_report"
            assert run_detail.json()["errors"] == []

            agent_registry = client.get("/api/v1/agents", headers=headers)
            assert agent_registry.status_code == 200, agent_registry.text
            orchestrator = next(
                item for item in agent_registry.json() if item["key"] == "orchestrator"
            )
            assert orchestrator["run_count"] >= 1
            assert orchestrator["success_rate"] == 1
            policy_search_agent = next(
                item for item in agent_registry.json() if item["key"] == "policy_search"
            )
            assert policy_search_agent["run_count"] >= 1
            assert policy_search_agent["last_run_at"] is not None
            eligibility_agent = next(
                item for item in agent_registry.json() if item["key"] == "eligibility"
            )
            evidence_agent = next(
                item for item in agent_registry.json() if item["key"] == "evidence"
            )
            assert eligibility_agent["status"] == "active"
            assert eligibility_agent["run_count"] >= 1
            assert evidence_agent["status"] == "active"
            assert evidence_agent["run_count"] >= 1

            opportunity_detail = client.get(
                f"/api/v1/opportunities/{opportunity['id']}", headers=headers
            )
            assert opportunity_detail.status_code == 200
            assert (
                opportunity_detail.json()["eligibility_result"]["criteria"][0]["status"] == "PASS"
            )
            assert opportunity_detail.json()["evidence"][0]["quote"] == quote
            assert opportunity_detail.json()["evidence"][0]["verified"] is True

            with SessionLocal() as db:
                negative_opportunity = Opportunity(
                    tenant_id=uuid.UUID(opportunity["tenant_id"]),
                    company_id=uuid.UUID(company_id),
                    policy_id=policy_id,
                    policy_version_id=policy_version_id,
                    profile_version_id=uuid.UUID(published.json()["id"]),
                    title="结构化硬门槛反例",
                    score=0.5,
                    status="identified",
                    evidence_json={},
                    policy_snapshot_json={"title": "结构化硬门槛反例", "source_url": None},
                )
                db.add(negative_opportunity)
                db.flush()
                negative_result = evaluate_opportunity(
                    db,
                    negative_opportunity,
                    {**_complete_profile(), "industry": "先进制造"},
                )
                assert negative_result.status == "NOT_ELIGIBLE"
                assert negative_result.criteria_json[0]["status"] == "FAIL"
                db.rollback()

            with SessionLocal() as db:
                assert (
                    db.scalar(
                        select(func.count())
                        .select_from(PolicyScan)
                        .where(PolicyScan.idempotency_key == idempotency_key)
                    )
                    == 1
                )
                assert (
                    db.scalar(
                        select(func.count())
                        .select_from(Opportunity)
                        .where(Opportunity.scan_id == uuid.UUID(scan_id))
                    )
                    == scan_detail.json()["total_opportunities"]
                )
                assert (
                    db.scalar(
                        select(func.count()).select_from(AgentRun).where(AgentRun.id == run_id)
                    )
                    == 1
                )
                assert (
                    db.scalar(
                        select(func.count())
                        .select_from(AgentStep)
                        .where(AgentStep.agent_run_id == run_id)
                    )
                    == 6
                )
                assert (
                    db.scalar(
                        select(func.count())
                        .select_from(ToolCall)
                        .where(ToolCall.agent_run_id == run_id)
                    )
                    == 3
                )
                assert (
                    db.scalar(
                        select(func.count())
                        .select_from(EligibilityResult)
                        .where(EligibilityResult.opportunity_id == uuid.UUID(opportunity["id"]))
                    )
                    == 1
                )
                assert (
                    db.scalar(
                        select(func.count())
                        .select_from(Evidence)
                        .where(Evidence.opportunity_id == uuid.UUID(opportunity["id"]))
                    )
                    == 1
                )
                assert (
                    db.scalar(
                        select(func.count())
                        .select_from(Artifact)
                        .where(Artifact.agent_run_id == run_id)
                    )
                    == 1
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
            assert workspace.json()["tasks"][0]["current_stage"] == "材料准备"
            assert workspace.json()["evidence"][0]["verified"] is True
            assert workspace.json()["activities"][0]["action"] == "application_created"

            requirement_id = workspace.json()["requirements"][0]["id"]
            linked = client.post(
                f"/api/v1/applications/{application_id}/documents",
                headers=headers,
                json={"document_id": document_id, "requirement_id": requirement_id},
            )
            assert linked.status_code == 201, linked.text
            duplicate_link = client.post(
                f"/api/v1/applications/{application_id}/documents",
                headers=headers,
                json={"document_id": document_id, "requirement_id": requirement_id},
            )
            assert duplicate_link.status_code == 201
            assert duplicate_link.json()["id"] == linked.json()["id"]

            comment = client.post(
                f"/api/v1/applications/{application_id}/comments",
                headers=headers,
                json={"body": "请复核研发费用材料。"},
            )
            assert comment.status_code == 201, comment.text

            empty_ask = client.post(
                f"/api/v1/applications/{application_id}/agent-actions",
                headers=headers,
                json={"action": "ask"},
            )
            assert empty_ask.status_code == 422
            checked = client.post(
                f"/api/v1/applications/{application_id}/agent-actions",
                headers=headers,
                json={"action": "check"},
            )
            assert checked.status_code == 200
            assert checked.json()["engine"] == "deterministic-evidence-v1"
            assert checked.json()["readiness"]["verified_evidence"] == 1
            explained = client.post(
                f"/api/v1/applications/{application_id}/agent-actions",
                headers=headers,
                json={"action": "explain"},
            )
            assert explained.status_code == 200
            assert explained.json()["citations"][0]["quote"] == quote
            generated = client.post(
                f"/api/v1/applications/{application_id}/agent-actions",
                headers=headers,
                json={"action": "generate"},
            )
            assert generated.status_code == 200, generated.text
            artifact_v1 = generated.json()["artifact"]
            assert artifact_v1["version"] == 1
            assert artifact_v1["source_snapshot"]["policy_version_id"] == str(policy_version_id)

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

            reviewing = client.patch(
                f"/api/v1/applications/{application_id}/status",
                headers=headers,
                json={"status": "review"},
            )
            assert reviewing.status_code == 200, reviewing.text

            rejected = client.post(
                f"/api/v1/applications/{application_id}/artifacts/{artifact_v1['id']}/review",
                headers=headers,
                json={"decision": "reject", "note": "补充材料状态"},
            )
            assert rejected.status_code == 200
            assert rejected.json()["status"] == "rejected"
            fixed = client.post(
                f"/api/v1/applications/{application_id}/agent-actions",
                headers=headers,
                json={"action": "fix", "instruction": "根据最新材料状态重新生成"},
            )
            assert fixed.status_code == 200
            artifact_v2 = fixed.json()["artifact"]
            assert artifact_v2["version"] == 2
            edited = client.post(
                f"/api/v1/applications/{application_id}/artifacts/{artifact_v2['id']}/edit",
                headers=headers,
                json={"executive_summary": "人工确认后的申报摘要。"},
            )
            assert edited.status_code == 201
            artifact_v3 = edited.json()
            assert artifact_v3["version"] == 3
            assert artifact_v3["content"]["executive_summary"] == "人工确认后的申报摘要。"

            reviewing_again = client.patch(
                f"/api/v1/applications/{application_id}/status",
                headers=headers,
                json={"status": "review"},
            )
            assert reviewing_again.status_code == 200, reviewing_again.text
            stale_review = client.post(
                f"/api/v1/applications/{application_id}/artifacts/{artifact_v1['id']}/review",
                headers=headers,
                json={"decision": "approve"},
            )
            assert stale_review.status_code == 409
            approved_artifact = client.post(
                f"/api/v1/applications/{application_id}/artifacts/{artifact_v3['id']}/review",
                headers=headers,
                json={"decision": "approve", "note": "内容已人工复核"},
            )
            assert approved_artifact.status_code == 200
            assert approved_artifact.json()["status"] == "approved"

            for export_format, expected_type in (
                ("docx", "wordprocessingml.document"),
                ("xlsx", "spreadsheetml.sheet"),
                ("json", "application/json"),
            ):
                downloaded = client.get(
                    f"/api/v1/applications/{application_id}/artifacts/{artifact_v3['id']}/download?format={export_format}",
                    headers=headers,
                )
                assert downloaded.status_code == 200
                assert expected_type in downloaded.headers["content-type"]

            application_approved = client.patch(
                f"/api/v1/applications/{application_id}/status",
                headers=headers,
                json={"status": "approved"},
            )
            assert application_approved.status_code == 200, application_approved.text

            terminal_generate = client.post(
                f"/api/v1/applications/{application_id}/agent-actions",
                headers=headers,
                json={"action": "generate"},
            )
            assert terminal_generate.status_code == 409
            terminal_edit = client.post(
                f"/api/v1/applications/{application_id}/artifacts/{artifact_v3['id']}/edit",
                headers=headers,
                json={"executive_summary": "不应覆盖已批准版本"},
            )
            assert terminal_edit.status_code == 409

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
            assert len(updated_workspace.json()["generated"]) == 3
            assert len(updated_workspace.json()["documents"]) == 1
            assert len(updated_workspace.json()["comments"]) == 1

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

            cross_tenant = client.get(
                f"/api/v1/opportunities/{opportunity['id']}", headers=other_headers
            )
            assert cross_tenant.status_code == 404
            cross_tenant_run = client.get(f"/api/v1/agent-runs/{run_id}", headers=other_headers)
            assert cross_tenant_run.status_code == 404
    finally:
        app.dependency_overrides.pop(get_oss_storage, None)
