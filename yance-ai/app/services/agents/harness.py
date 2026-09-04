import asyncio
import uuid
from datetime import UTC, datetime, timedelta
from time import perf_counter

import structlog
from pydantic import ValidationError
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import (
    AgentRetry,
    AgentRun,
    AgentRunError,
    AgentStep,
    PolicyScan,
    Task,
    ToolCall,
    WorkflowRun,
)
from app.services.agents.contracts import PolicyScanWorkflowInput, VerificationFailed
from app.services.agents.definitions import (
    ORCHESTRATOR_AGENT_ID,
    POLICY_SCAN_WORKFLOW_ID,
)
from app.services.agents.policy_scan import execute_policy_scan

logger = structlog.get_logger()


class AgentHarness:
    """Database-backed Agent queue and structured policy-scan executor."""

    def __init__(self, *, lease_seconds: int | None = None) -> None:
        self.lease_seconds = lease_seconds or settings.agent_lease_seconds

    def enqueue_policy_scan(
        self,
        db: Session,
        *,
        scan: PolicyScan,
        task: Task,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> AgentRun:
        payload = PolicyScanWorkflowInput(
            tenant_id=tenant_id,
            user_id=user_id,
            task_id=task.id,
            scan_id=scan.id,
            company_id=scan.company_id,
            profile_version_id=scan.profile_version_id,
        )
        workflow_run = WorkflowRun(
            tenant_id=tenant_id,
            workflow_id=POLICY_SCAN_WORKFLOW_ID,
            user_id=user_id,
            company_id=scan.company_id,
            task_id=task.id,
            status="queued",
            input_json=payload.model_dump(mode="json"),
        )
        db.add(workflow_run)
        db.flush()
        run = AgentRun(
            tenant_id=tenant_id,
            workflow_run_id=workflow_run.id,
            task_id=task.id,
            user_id=user_id,
            agent_id=ORCHESTRATOR_AGENT_ID,
            agent_name="orchestrator",
            provider="internal",
            model="policy-scan-v2",
            prompt_version="policy-scan-v2",
            status="queued",
            input_json=payload.model_dump(mode="json"),
            metadata_json={"workflow_key": "policy_scan", "workflow_version": "v2"},
            max_retries=settings.agent_max_retries,
        )
        db.add(run)
        db.flush()
        scan.workflow_run_id = workflow_run.id
        return run

    def claim_next(self, db: Session, worker_id: str) -> uuid.UUID | None:
        now = datetime.now(UTC)
        candidate = db.scalar(
            select(AgentRun)
            .where(
                or_(
                    and_(AgentRun.status == "queued", AgentRun.next_attempt_at <= now),
                    and_(
                        AgentRun.status.in_(["planning", "running"]),
                        AgentRun.lease_expires_at.is_not(None),
                        AgentRun.lease_expires_at < now,
                    ),
                )
            )
            .order_by(AgentRun.next_attempt_at, AgentRun.queued_at)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if not candidate:
            db.rollback()
            return None

        if candidate.status in {"planning", "running"}:
            candidate.retry_count += 1
            db.add(
                AgentRetry(
                    tenant_id=candidate.tenant_id,
                    agent_run_id=candidate.id,
                    retry_number=candidate.retry_count,
                    reason_code="lease_expired",
                    error_json={},
                    started_at=now,
                )
            )
            if candidate.retry_count > candidate.max_retries:
                self._terminal_failure(
                    db,
                    candidate,
                    code="lease_recovery_exhausted",
                    safe_message="执行租约多次过期，任务已停止",
                )
                db.commit()
                return None

        candidate.status = "planning"
        candidate.lease_owner = worker_id[:160]
        candidate.lease_expires_at = now + timedelta(seconds=self.lease_seconds)
        candidate.last_heartbeat_at = now
        candidate.started_at = candidate.started_at or now
        workflow_run = self._workflow_run(db, candidate)
        workflow_run.status = "planning"
        workflow_run.started_at = workflow_run.started_at or now
        db.commit()
        return candidate.id

    async def run_once(self, db: Session, worker_id: str) -> uuid.UUID | None:
        run_id = self.claim_next(db, worker_id)
        if not run_id:
            return None
        await self.execute(db, run_id)
        return run_id

    async def execute(self, db: Session, run_id: uuid.UUID) -> None:
        run = db.scalar(select(AgentRun).where(AgentRun.id == run_id))
        if not run:
            return
        structlog.contextvars.bind_contextvars(
            run_id=str(run.id),
            tenant_id=str(run.tenant_id),
            workflow_run_id=str(run.workflow_run_id),
        )
        try:
            await execute_policy_scan(db, run, self)
        except Exception as exc:
            db.rollback()
            self._record_failure(db, run_id, exc)
        finally:
            structlog.contextvars.clear_contextvars()

    def _complete_step(
        self,
        db: Session,
        run: AgentRun,
        workflow_run: WorkflowRun,
        *,
        sequence: int,
        step_type: str,
        agent_id: uuid.UUID,
        input_json: dict,
        output_json: dict,
        verification_json: dict | None = None,
    ) -> AgentStep:
        step = self._start_step(
            db,
            run,
            workflow_run,
            sequence=sequence,
            step_type=step_type,
            agent_id=agent_id,
            input_json=input_json,
        )
        if step.status != "completed":
            self._finish_step(db, step, output_json, verification_json)
        return step

    def _start_step(
        self,
        db: Session,
        run: AgentRun,
        workflow_run: WorkflowRun,
        *,
        sequence: int,
        step_type: str,
        agent_id: uuid.UUID,
        input_json: dict,
    ) -> AgentStep:
        existing = db.scalar(
            select(AgentStep).where(
                AgentStep.agent_run_id == run.id,
                AgentStep.sequence == sequence,
            )
        )
        if existing and existing.status == "completed":
            return existing
        step = existing or AgentStep(
            tenant_id=run.tenant_id,
            agent_run_id=run.id,
            sequence=sequence,
            step_type=step_type,
            agent_id=agent_id,
        )
        step.status = "running"
        step.input_json = input_json
        step.output_json = {}
        step.verification_json = {}
        step.error_code = None
        step.started_at = datetime.now(UTC)
        step.finished_at = None
        run.status = "planning" if step_type == "plan" else "running"
        run.last_heartbeat_at = step.started_at
        run.lease_expires_at = step.started_at + timedelta(seconds=self.lease_seconds)
        workflow_run.status = run.status
        workflow_run.current_step = step_type
        task = (
            db.scalar(select(Task).where(Task.id == run.task_id, Task.tenant_id == run.tenant_id))
            if run.task_id
            else None
        )
        if task:
            stage_progress = {
                "plan": ("规划执行", 10),
                "retrieve": ("检索政策", 30),
                "reason": ("形成判断", 50),
                "act": ("生成交付物", 70),
                "verify": ("验证结果", 90),
                "finish": ("完成收口", 95),
            }
            task.current_stage, task.progress = stage_progress.get(
                step_type, ("Agent 执行中", task.progress or 0)
            )
        db.add(step)
        db.commit()
        db.refresh(step)
        return step

    @staticmethod
    def _finish_step(
        db: Session,
        step: AgentStep,
        output_json: dict,
        verification_json: dict | None = None,
    ) -> None:
        finished = datetime.now(UTC)
        step.output_json = output_json
        step.verification_json = verification_json or {}
        step.status = "completed"
        step.finished_at = finished
        if step.started_at:
            step.latency_ms = max(0, round((finished - step.started_at).total_seconds() * 1000))
        db.commit()

    @staticmethod
    def _start_tool(
        db: Session,
        run: AgentRun,
        step: AgentStep,
        name: str,
        arguments: dict,
    ) -> ToolCall:
        tool = ToolCall(
            tenant_id=run.tenant_id,
            agent_run_id=run.id,
            agent_step_id=step.id,
            tool_name=name,
            idempotency_key=f"{run.id}:{step.sequence}:{name}",
            status="running",
            arguments_json=arguments,
        )
        db.add(tool)
        db.commit()
        db.refresh(tool)
        return tool

    @staticmethod
    def _finish_tool(db: Session, tool: ToolCall, result: dict, started: float) -> None:
        tool.status = "completed"
        tool.result_json = result
        tool.finished_at = datetime.now(UTC)
        tool.latency_ms = round((perf_counter() - started) * 1000)
        db.commit()

    def _record_failure(self, db: Session, run_id: uuid.UUID, exc: Exception) -> None:
        run = db.scalar(select(AgentRun).where(AgentRun.id == run_id))
        if not run:
            return
        code = (
            "invalid_agent_input" if isinstance(exc, ValidationError) else "agent_execution_failed"
        )
        if isinstance(exc, VerificationFailed):
            code = "verification_failed"
        safe_message = "Agent 工作流执行失败"
        active_step = db.scalar(
            select(AgentStep)
            .where(AgentStep.agent_run_id == run.id, AgentStep.status == "running")
            .order_by(AgentStep.sequence.desc())
        )
        if active_step:
            active_step.status = "failed"
            active_step.error_code = code
            active_step.finished_at = datetime.now(UTC)
        open_tools = db.scalars(
            select(ToolCall).where(
                ToolCall.agent_run_id == run.id,
                ToolCall.status == "running",
            )
        ).all()
        for tool in open_tools:
            tool.status = "failed"
            tool.error_code = code
            tool.finished_at = datetime.now(UTC)
        db.add(
            AgentRunError(
                tenant_id=run.tenant_id,
                agent_run_id=run.id,
                agent_step_id=active_step.id if active_step else None,
                code=code,
                category="validation"
                if isinstance(exc, (ValidationError, VerificationFailed))
                else "execution",
                safe_message=safe_message,
                details_json={"exception_type": type(exc).__name__},
                retryable=not isinstance(exc, ValidationError),
            )
        )
        if not isinstance(exc, ValidationError) and run.retry_count < run.max_retries:
            run.retry_count += 1
            delay_seconds = min(60, 2**run.retry_count)
            run.status = "queued"
            run.next_attempt_at = datetime.now(UTC) + timedelta(seconds=delay_seconds)
            run.error_code = code
            run.error_json = {"exception_type": type(exc).__name__}
            run.lease_owner = None
            run.lease_expires_at = None
            db.add(
                AgentRetry(
                    tenant_id=run.tenant_id,
                    agent_run_id=run.id,
                    retry_number=run.retry_count,
                    reason_code=code,
                    error_json={"exception_type": type(exc).__name__},
                    scheduled_at=run.next_attempt_at,
                )
            )
            workflow = self._workflow_run(db, run)
            workflow.status = "queued"
            task = db.scalar(select(Task).where(Task.id == run.task_id)) if run.task_id else None
            if task:
                task.status = "queued"
                task.current_stage = "等待重试"
        else:
            self._terminal_failure(db, run, code=code, safe_message=safe_message)
        db.commit()
        logger.error("agent_run_failed", error_code=code, retry_count=run.retry_count)

    def _terminal_failure(
        self,
        db: Session,
        run: AgentRun,
        *,
        code: str,
        safe_message: str,
    ) -> None:
        finished = datetime.now(UTC)
        run.status = "failed"
        run.error_code = code
        run.error_json = {"message": safe_message}
        run.finished_at = finished
        run.lease_owner = None
        run.lease_expires_at = None
        workflow = self._workflow_run(db, run)
        workflow.status = "failed"
        workflow.error_code = code
        workflow.finished_at = finished
        task = db.scalar(select(Task).where(Task.id == run.task_id)) if run.task_id else None
        if task:
            task.status = "failed"
            task.failure_reason = code
            task.completed_at = finished
        scan = db.scalar(select(PolicyScan).where(PolicyScan.workflow_run_id == workflow.id))
        if scan:
            scan.status = "failed"
            scan.error_code = code
            scan.completed_at = finished

    @staticmethod
    def _workflow_run(db: Session, run: AgentRun) -> WorkflowRun:
        workflow = db.scalar(select(WorkflowRun).where(WorkflowRun.id == run.workflow_run_id))
        if not workflow or workflow.tenant_id != run.tenant_id:
            raise RuntimeError("workflow_run_not_found")
        return workflow

    @staticmethod
    def _owned(db: Session, model, resource_id: uuid.UUID, tenant_id: uuid.UUID):
        resource = db.scalar(
            select(model).where(model.id == resource_id, model.tenant_id == tenant_id)
        )
        if not resource:
            raise RuntimeError(f"{model.__name__.lower()}_not_found")
        return resource


async def run_agent_worker(*, poll_seconds: float | None = None, once: bool = False) -> None:
    from app.core.db import SessionLocal

    harness = AgentHarness()
    resolved_poll_seconds = poll_seconds or settings.agent_worker_poll_seconds
    worker_id = f"worker-{uuid.uuid4()}"
    while True:
        with SessionLocal() as db:
            claimed = await harness.run_once(db, worker_id)
        if once or claimed is not None:
            if once:
                return
        if claimed is None:
            await asyncio.sleep(resolved_poll_seconds)
