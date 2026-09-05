from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.models import (
    AgentRun,
    AgentStep,
    Application,
    ApplicationArtifact,
    ApplicationRequirement,
    Company,
    CompanyProfileVersion,
    DemoScenario,
    Document,
    EligibilityResult,
    Evidence,
    Opportunity,
    Policy,
    PolicyScan,
    Task,
    Tenant,
    ToolCall,
)
from app.services.applications.artifacts import render_artifact

router = APIRouter(prefix="/demo", tags=["demo"])
DATA_NOTICE = (
    "DEMO synthetic example. It is not a customer, policy, government relationship, "
    "revenue record, accuracy claim, or submission outcome."
)


def _scenario_query():
    return (
        select(DemoScenario)
        .join(Tenant, Tenant.id == DemoScenario.tenant_id)
        .where(
            DemoScenario.status == "published",
            DemoScenario.data_classification == "synthetic",
            Tenant.is_demo.is_(True),
            Tenant.is_active.is_(True),
        )
    )


def _get_scenario(db: Session, key: str) -> DemoScenario:
    scenario = db.scalar(_scenario_query().where(DemoScenario.key == key))
    if not scenario:
        raise HTTPException(status_code=404, detail="Demo scenario not found")
    return scenario


def _same_tenant(scenario: DemoScenario, *records) -> None:
    if any(record is None or record.tenant_id != scenario.tenant_id for record in records):
        raise HTTPException(status_code=409, detail="Demo scenario integrity check failed")


@router.get("/scenarios")
def list_demo_scenarios(db: Session = Depends(get_db)) -> dict:
    scenarios = db.scalars(_scenario_query().order_by(DemoScenario.display_order)).all()
    return {
        "dataset_version": scenarios[0].dataset_version if scenarios else None,
        "data_classification": "synthetic",
        "data_notice": DATA_NOTICE,
        "items": [
            {
                "key": item.key,
                "title": item.title,
                "industry": item.industry,
                "persona": item.persona,
                "summary": item.summary,
                "next_best_action": item.next_best_action,
                "display_order": item.display_order,
            }
            for item in scenarios
        ],
    }


@router.get("/scenarios/{key}")
def get_demo_scenario(key: str, db: Session = Depends(get_db)) -> dict:
    scenario = _get_scenario(db, key)
    company = db.get(Company, scenario.company_id)
    profile = db.get(CompanyProfileVersion, scenario.profile_version_id)
    document = db.get(Document, scenario.document_id)
    scan = db.get(PolicyScan, scenario.scan_id)
    opportunity = db.get(Opportunity, scenario.opportunity_id)
    eligibility = db.get(EligibilityResult, scenario.eligibility_result_id)
    application = db.get(Application, scenario.application_id)
    artifact = db.get(ApplicationArtifact, scenario.artifact_id)
    agent_run = db.get(AgentRun, scenario.agent_run_id)
    _same_tenant(
        scenario,
        company,
        profile,
        document,
        scan,
        opportunity,
        eligibility,
        application,
        artifact,
        agent_run,
    )
    if (
        opportunity.scan_id != scan.id
        or eligibility.opportunity_id != opportunity.id
        or application.opportunity_id != opportunity.id
        or artifact.application_id != application.id
    ):
        raise HTTPException(status_code=409, detail="Demo scenario relationship check failed")

    policy = db.get(Policy, opportunity.policy_id)
    if not policy or policy.tenant_id != scenario.tenant_id:
        raise HTTPException(status_code=409, detail="Demo policy isolation check failed")
    evidence = db.scalars(
        select(Evidence)
        .where(
            Evidence.tenant_id == scenario.tenant_id,
            Evidence.eligibility_result_id == eligibility.id,
        )
        .order_by(Evidence.created_at)
    ).all()
    requirements = db.scalars(
        select(ApplicationRequirement)
        .where(
            ApplicationRequirement.tenant_id == scenario.tenant_id,
            ApplicationRequirement.application_id == application.id,
        )
        .order_by(ApplicationRequirement.sort_order)
    ).all()
    tasks = db.scalars(
        select(Task)
        .where(Task.tenant_id == scenario.tenant_id, Task.application_id == application.id)
        .order_by(Task.created_at)
    ).all()
    steps = db.scalars(
        select(AgentStep)
        .where(AgentStep.tenant_id == scenario.tenant_id, AgentStep.agent_run_id == agent_run.id)
        .order_by(AgentStep.sequence)
    ).all()
    step_ids = [step.id for step in steps]
    tool_calls = (
        db.scalars(
            select(ToolCall)
            .where(
                ToolCall.tenant_id == scenario.tenant_id,
                ToolCall.agent_step_id.in_(step_ids),
            )
            .order_by(ToolCall.started_at)
        ).all()
        if step_ids
        else []
    )
    for item in evidence:
        if item.quote != policy.original_text[item.quote_start : item.quote_end]:
            raise HTTPException(status_code=409, detail="Demo evidence exact-span check failed")

    return {
        "key": scenario.key,
        "title": scenario.title,
        "industry": scenario.industry,
        "persona": scenario.persona,
        "summary": scenario.summary,
        "dataset_version": scenario.dataset_version,
        "data_classification": scenario.data_classification,
        "data_notice": DATA_NOTICE,
        "company": {
            "id": str(company.id),
            "name": company.name,
            "industry": company.industry,
            "province": company.province,
            "city": company.city,
            "profile_version": profile.version,
            "completeness_score": profile.completeness_score,
            "profile": profile.snapshot_json,
        },
        "document": {
            "id": str(document.id),
            "filename": document.filename,
            "content_type": document.content_type,
            "ingestion_status": document.ingestion_status,
            "metadata": document.metadata_json,
        },
        "scan": {
            "id": str(scan.id),
            "status": scan.status,
            "provider": scan.provider,
            "total_opportunities": scan.total_opportunities,
            "completed_at": scan.completed_at,
        },
        "opportunity": {
            "id": str(opportunity.id),
            "title": opportunity.title,
            "match_score": opportunity.score,
            "eligibility": opportunity.eligibility_status,
            "confidence": float(opportunity.eligibility_confidence or 0),
            "potential_benefit": policy.support_amount,
            "deadline": policy.deadline,
            "region": policy.jurisdiction,
            "authority": policy.issuing_authority,
            "policy_type": policy.policy_type,
            "evidence_count": len(evidence),
        },
        "eligibility": {
            "id": str(eligibility.id),
            "status": eligibility.status,
            "confidence": float(eligibility.confidence),
            "summary": eligibility.summary,
            "criteria": eligibility.criteria_json,
            "missing_information": eligibility.missing_information_json,
            "engine_version": eligibility.engine_version,
            "review_status": eligibility.review_status,
            "verified_at": eligibility.verified_at,
        },
        "evidence": [
            {
                "id": str(item.id),
                "conclusion": eligibility.status,
                "source_title": item.source_title,
                "source_url": item.source_url,
                "issuer": item.issuer,
                "article": item.article,
                "quote": item.quote,
                "publish_date": policy.published_at,
                "effective_date": policy.effective_at,
                "expiry_date": policy.deadline,
                "region": policy.jurisdiction,
                "confidence": float(item.confidence),
                "verified": item.verified,
                "verifier": item.verifier,
            }
            for item in evidence
        ],
        "application": {
            "id": str(application.id),
            "title": application.title,
            "status": application.status,
            "progress": application.progress,
            "review_status": application.review_status,
            "due_at": application.due_at,
            "requirements": [
                {
                    "id": str(item.id),
                    "title": item.title,
                    "description": item.description,
                    "status": item.status,
                    "is_hard_gate": item.is_hard_gate,
                }
                for item in requirements
            ],
            "tasks": [
                {
                    "id": str(item.id),
                    "title": item.title,
                    "status": item.status,
                    "priority": item.priority,
                    "progress": item.progress,
                }
                for item in tasks
            ],
        },
        "agent_run": {
            "id": str(agent_run.id),
            "status": agent_run.status,
            "agent_name": agent_run.agent_name,
            "model": agent_run.model,
            "latency_ms": agent_run.latency_ms,
            "tokens": agent_run.total_tokens,
            "cost_usd": float(agent_run.cost_usd or 0),
            "steps": [
                {
                    "sequence": item.sequence,
                    "type": item.step_type,
                    "status": item.status,
                    "output": item.output_json,
                    "verification": item.verification_json,
                }
                for item in steps
            ],
            "tool_calls": [
                {
                    "tool_name": item.tool_name,
                    "status": item.status,
                    "latency_ms": item.latency_ms,
                    "result": item.result_json,
                }
                for item in tool_calls
            ],
        },
        "artifact": {
            "id": str(artifact.id),
            "title": artifact.title,
            "version": artifact.version,
            "status": artifact.status,
            "generation_method": artifact.generation_method,
            "checksum_sha256": artifact.checksum_sha256,
            "content": artifact.content_json,
            "formats": ["docx", "pdf", "xlsx", "json"],
        },
        "next_best_action": scenario.next_best_action,
    }


@router.get("/scenarios/{key}/artifacts/{artifact_id}/download")
def download_demo_artifact(
    key: str,
    artifact_id: str,
    format: Literal["docx", "pdf", "xlsx", "json"] = "docx",
    db: Session = Depends(get_db),
) -> Response:
    scenario = _get_scenario(db, key)
    if str(scenario.artifact_id) != artifact_id:
        raise HTTPException(status_code=404, detail="Demo artifact not found")
    artifact = db.get(ApplicationArtifact, scenario.artifact_id)
    _same_tenant(scenario, artifact)
    payload, media_type, extension = render_artifact(artifact.content_json, format)
    return Response(
        content=payload,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="demo-{scenario.key}.{extension}"',
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "public, max-age=300",
        },
    )
