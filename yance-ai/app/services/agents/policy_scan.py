from datetime import UTC, datetime
from time import perf_counter
from typing import TYPE_CHECKING

import structlog
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.models import (
    AgentRun,
    Artifact,
    Company,
    CompanyProfileVersion,
    Deliverable,
    EligibilityResult,
    Evidence,
    Opportunity,
    Policy,
    PolicyScan,
    Task,
)
from app.services.agents.contracts import (
    ActOutput,
    PlanOutput,
    PolicyScanWorkflowInput,
    PolicyScanWorkflowOutput,
    ReasonOutput,
    RetrieveOutput,
    VerificationCheck,
    VerificationFailed,
    VerificationResult,
)
from app.services.agents.definitions import (
    ELIGIBILITY_AGENT_ID,
    EVIDENCE_AGENT_ID,
    ORCHESTRATOR_AGENT_ID,
    POLICY_SCAN_STEPS,
    POLICY_SEARCH_AGENT_ID,
    REPORT_AGENT_ID,
)
from app.services.analytics.events import record_event
from app.services.policies.eligibility import evaluate_opportunity
from app.services.policies.visibility import visible_policy_clause
from app.services.report.matcher import match_policies_for_company
from app.services.report.pdf import generate_match_report_pdf

if TYPE_CHECKING:
    from app.services.agents.harness import AgentHarness

logger = structlog.get_logger()


async def execute_policy_scan(db: Session, run: AgentRun, harness: "AgentHarness") -> None:
    """Execute the versioned policy scan while the harness owns reliability concerns."""

    started = perf_counter()
    payload = PolicyScanWorkflowInput.model_validate(run.input_json)
    scan = harness._owned(db, PolicyScan, payload.scan_id, payload.tenant_id)
    task = harness._owned(db, Task, payload.task_id, payload.tenant_id)
    company = harness._owned(db, Company, payload.company_id, payload.tenant_id)
    workflow_run = harness._workflow_run(db, run)
    started_at = datetime.now(UTC)
    scan.status = "running"
    scan.started_at = scan.started_at or started_at
    task.status = "running"
    task.started_at = task.started_at or started_at
    task.current_stage = "规划执行"
    task.progress = max(task.progress or 0, 5)
    db.commit()

    plan = PlanOutput(steps=list(POLICY_SCAN_STEPS), verification_required=True)
    harness._complete_step(
        db,
        run,
        workflow_run,
        sequence=1,
        step_type="plan",
        agent_id=ORCHESTRATOR_AGENT_ID,
        input_json={"workflow": "policy_scan", "version": "v2"},
        output_json=plan.model_dump(mode="json"),
    )

    retrieve_step = harness._start_step(
        db,
        run,
        workflow_run,
        sequence=2,
        step_type="retrieve",
        agent_id=POLICY_SEARCH_AGENT_ID,
        input_json={
            "company_id": str(company.id),
            "scan_id": str(scan.id),
            "profile_version_id": str(payload.profile_version_id),
        },
    )
    if retrieve_step.status == "completed":
        retrieve = RetrieveOutput.model_validate(retrieve_step.output_json)
        opportunities = list(
            db.scalars(
                select(Opportunity).where(
                    Opportunity.tenant_id == payload.tenant_id,
                    Opportunity.id.in_(retrieve.opportunity_ids),
                )
            ).all()
        )
    else:
        tool = harness._start_tool(
            db,
            run,
            retrieve_step,
            "policy_match",
            {
                "company_id": str(company.id),
                "scan_id": str(scan.id),
                "profile_version_id": str(payload.profile_version_id),
            },
        )
        tool_started = perf_counter()
        opportunities = await match_policies_for_company(
            db,
            company,
            payload.tenant_id,
            scan_id=scan.id,
            profile_version_id=payload.profile_version_id,
        )
        retrieve = RetrieveOutput(
            opportunity_ids=[item.id for item in opportunities],
            policy_ids=[item.policy_id for item in opportunities if item.policy_id],
            total=len(opportunities),
        )
        harness._finish_tool(
            db,
            tool,
            {
                "opportunity_ids": [str(item.id) for item in opportunities],
                "total": len(opportunities),
            },
            tool_started,
        )
        harness._finish_step(db, retrieve_step, retrieve.model_dump(mode="json"))

    reason_step = harness._start_step(
        db,
        run,
        workflow_run,
        sequence=3,
        step_type="reason",
        agent_id=ELIGIBILITY_AGENT_ID,
        input_json={"opportunity_count": len(opportunities)},
    )
    if reason_step.status == "completed":
        reason = ReasonOutput.model_validate(reason_step.output_json)
    else:
        tool = harness._start_tool(
            db,
            run,
            reason_step,
            "evaluate_eligibility",
            {"opportunity_ids": [str(item.id) for item in opportunities]},
        )
        tool_started = perf_counter()
        states: dict[str, int] = {}
        profile_snapshot = (
            db.scalar(
                select(CompanyProfileVersion.snapshot_json).where(
                    CompanyProfileVersion.id == payload.profile_version_id,
                    CompanyProfileVersion.tenant_id == payload.tenant_id,
                )
            )
            or {}
        )
        for opportunity in opportunities:
            result = evaluate_opportunity(db, opportunity, profile_snapshot)
            states[result.status] = states.get(result.status, 0) + 1
        db.commit()
        reason = ReasonOutput(
            states=states,
            reason="资格由已审核结构化规则确定；缺失规则、事实或精确来源时保持需要更多信息。",
        )
        harness._finish_tool(db, tool, {"states": states}, tool_started)
        harness._finish_step(db, reason_step, reason.model_dump(mode="json"))

    act_step = harness._start_step(
        db,
        run,
        workflow_run,
        sequence=4,
        step_type="act",
        agent_id=REPORT_AGENT_ID,
        input_json={"opportunity_ids": [str(item.id) for item in opportunities]},
    )
    if act_step.status == "completed":
        act = ActOutput.model_validate(act_step.output_json)
    else:
        act = _create_report_artifact(db, run, task, company, opportunities, act_step, harness)
        harness._finish_step(db, act_step, act.model_dump(mode="json"))

    verification = _verify(db, scan, payload, opportunities)
    verify_step = harness._complete_step(
        db,
        run,
        workflow_run,
        sequence=5,
        step_type="verify",
        agent_id=EVIDENCE_AGENT_ID,
        input_json={"opportunity_count": len(opportunities)},
        output_json={"passed": verification.passed},
        verification_json=verification.model_dump(mode="json"),
    )
    if not verification.passed:
        verify_step.status = "failed"
        verify_step.error_code = "verification_failed"
        db.commit()
        raise VerificationFailed("Policy scan verification failed")

    output = PolicyScanWorkflowOutput(
        scan_id=scan.id,
        opportunity_ids=[item.id for item in opportunities],
        total_opportunities=len(opportunities),
        artifact_id=act.artifact_id,
        verification_passed=True,
    )
    harness._complete_step(
        db,
        run,
        workflow_run,
        sequence=6,
        step_type="finish",
        agent_id=ORCHESTRATOR_AGENT_ID,
        input_json={"verification_passed": True},
        output_json=output.model_dump(mode="json"),
    )
    finished = datetime.now(UTC)
    latency_ms = round((perf_counter() - started) * 1000)
    run.status = "completed"
    run.output_json = output.model_dump(mode="json")
    run.finished_at = finished
    run.latency_ms = latency_ms
    run.lease_owner = None
    run.lease_expires_at = None
    workflow_run.status = "completed"
    workflow_run.current_step = "finish"
    workflow_run.output_json = output.model_dump(mode="json")
    workflow_run.finished_at = finished
    workflow_run.latency_ms = latency_ms
    scan.status = "completed"
    scan.total_opportunities = len(opportunities)
    scan.completed_at = finished
    task.status = "delivered"
    task.delivery_status = "delivered"
    task.progress = 100
    task.current_stage = "已完成"
    task.completed_at = finished
    record_event(
        db,
        tenant_id=run.tenant_id,
        user_id=run.user_id,
        name="policy_scan_completed",
        event_key=f"policy_scan_completed:{scan.id}",
        properties={
            "scan_id": str(scan.id),
            "workflow_run_id": str(workflow_run.id),
            "agent_run_id": str(run.id),
            "total_opportunities": len(opportunities),
        },
    )
    db.commit()
    logger.info("agent_run_completed", status="completed", latency_ms=latency_ms)


def _create_report_artifact(
    db: Session,
    run: AgentRun,
    task: Task,
    company: Company,
    opportunities: list[Opportunity],
    step,
    harness: "AgentHarness",
) -> ActOutput:
    existing = db.scalar(
        select(Artifact).where(
            Artifact.agent_run_id == run.id,
            Artifact.artifact_type == "policy_scan_report",
            Artifact.version == 1,
        )
    )
    if existing:
        deliverable = db.scalar(
            select(Deliverable).where(
                Deliverable.task_id == task.id,
                Deliverable.tenant_id == run.tenant_id,
            )
        )
        if not deliverable:
            raise RuntimeError("artifact_deliverable_missing")
        return ActOutput(deliverable_id=deliverable.id, artifact_id=existing.id)

    policy_ids = [item.policy_id for item in opportunities if item.policy_id]
    policies = (
        list(
            db.scalars(
                select(Policy).where(
                    Policy.id.in_(policy_ids), visible_policy_clause(run.tenant_id)
                )
            ).all()
        )
        if policy_ids
        else []
    )
    tool = harness._start_tool(
        db,
        run,
        step,
        "render_policy_scan_report",
        {"company_id": str(company.id), "opportunity_count": len(opportunities)},
    )
    tool_started = perf_counter()
    pdf_bytes = generate_match_report_pdf(company, opportunities, policies)
    summary = {
        "total_matches": len(opportunities),
        "policy_ids": [str(item.id) for item in policies],
        "byte_length": len(pdf_bytes),
    }
    deliverable = Deliverable(
        tenant_id=run.tenant_id,
        task_id=task.id,
        user_id=run.user_id,
        company_id=company.id,
        deliverable_type="policy_scan",
        title=f"{company.name} - 企业政策机会扫描报告",
        content_json=summary,
        content_markdown=f"# {company.name} 政策扫描报告\n\n匹配政策数: {len(opportunities)}",
        pdf_url=f"/api/v1/tasks/{task.id}/download",
        version=1,
        status="generated",
        generated_at=datetime.now(UTC),
    )
    artifact = Artifact(
        tenant_id=run.tenant_id,
        agent_run_id=run.id,
        task_id=task.id,
        artifact_type="policy_scan_report",
        title=deliverable.title,
        version=1,
        status="generated",
        mime_type="application/pdf",
        content_json=summary,
    )
    db.add_all([deliverable, artifact])
    db.flush()
    harness._finish_tool(db, tool, summary, tool_started)
    return ActOutput(deliverable_id=deliverable.id, artifact_id=artifact.id)


def _verify(
    db: Session,
    scan: PolicyScan,
    payload: PolicyScanWorkflowInput,
    opportunities: list[Opportunity],
) -> VerificationResult:
    policy_ids = [item.policy_id for item in opportunities]
    allowed_eligibility = {
        "ELIGIBLE",
        "POTENTIALLY_ELIGIBLE",
        "NOT_ELIGIBLE",
        "NEED_MORE_INFORMATION",
    }
    checks = [
        VerificationCheck(
            code="scan_profile_pinned",
            passed=scan.profile_version_id == payload.profile_version_id,
        ),
        VerificationCheck(
            code="opportunity_scan_provenance",
            passed=all(
                item.scan_id == scan.id and item.tenant_id == payload.tenant_id
                for item in opportunities
            ),
            actual=len(opportunities),
        ),
        VerificationCheck(
            code="one_opportunity_per_policy",
            passed=len(policy_ids) == len(set(policy_ids)),
            actual=len(policy_ids),
        ),
        VerificationCheck(
            code="policy_snapshot_present",
            passed=all(
                bool(item.policy_snapshot_json.get("title"))
                and "source_url" in item.policy_snapshot_json
                for item in opportunities
            ),
            actual=len(opportunities),
        ),
        VerificationCheck(
            code="policy_source_version_pinned",
            passed=all(
                item.policy_id is None
                or (
                    item.policy_version_id is not None
                    and item.policy_snapshot_json.get("policy_version_id")
                    == str(item.policy_version_id)
                )
                for item in opportunities
            ),
            actual=len(opportunities),
        ),
        VerificationCheck(
            code="eligibility_state_valid",
            passed=all(item.eligibility_status in allowed_eligibility for item in opportunities),
            actual=len(opportunities),
        ),
        VerificationCheck(
            code="eligibility_result_persisted",
            passed=all(
                db.scalar(
                    select(EligibilityResult.id).where(
                        EligibilityResult.opportunity_id == item.id,
                        EligibilityResult.tenant_id == payload.tenant_id,
                        EligibilityResult.policy_version_id == item.policy_version_id,
                    )
                )
                is not None
                for item in opportunities
            ),
            actual=len(opportunities),
        ),
        VerificationCheck(
            code="positive_decisions_have_verified_evidence",
            passed=all(
                item.eligibility_status not in {"ELIGIBLE", "POTENTIALLY_ELIGIBLE"}
                or db.scalar(
                    select(Evidence.id).where(
                        Evidence.opportunity_id == item.id,
                        Evidence.tenant_id == payload.tenant_id,
                        Evidence.verified.is_(True),
                    )
                )
                is not None
                for item in opportunities
            ),
            actual=len(opportunities),
        ),
    ]
    return VerificationResult(passed=all(item.passed for item in checks), checks=checks)
