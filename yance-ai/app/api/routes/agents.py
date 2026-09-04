from datetime import datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.api.deps import Principal, get_principal
from app.core.db import get_db
from app.models.models import (
    Agent,
    AgentRetry,
    AgentRun,
    AgentRunError,
    AgentStep,
    Artifact,
    ToolCall,
    Workflow,
    WorkflowRun,
)

router = APIRouter(tags=["agents"])

RunStatus = Literal[
    "queued", "planning", "running", "waiting", "review", "completed", "failed", "cancelled"
]


class AgentSummary(BaseModel):
    id: UUID
    key: str
    name: str
    description: str
    version: str
    status: str
    run_count: int
    completed_runs: int
    failed_runs: int
    success_rate: float | None
    average_latency_ms: float | None
    tasks_completed: int
    last_run_at: datetime | None


class AgentRunSummary(BaseModel):
    id: UUID
    workflow_run_id: UUID | None
    task_id: UUID | None
    agent_key: str | None
    agent_name: str
    status: str
    current_step: str | None
    model: str
    prompt_version: str | None
    total_tokens: int
    cost_usd: Decimal
    latency_ms: int | None
    retry_count: int
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    error_code: str | None


class AgentStepOut(BaseModel):
    id: UUID
    sequence: int
    agent_id: UUID | None
    step_type: str
    status: str
    input: dict[str, Any]
    output: dict[str, Any]
    verification: dict[str, Any]
    input_tokens: int
    output_tokens: int
    cost_usd: Decimal
    latency_ms: int | None
    started_at: datetime | None
    finished_at: datetime | None
    error_code: str | None


class ToolCallOut(BaseModel):
    id: UUID
    agent_step_id: UUID
    tool_name: str
    status: str
    arguments: dict[str, Any]
    result: dict[str, Any]
    latency_ms: int | None
    started_at: datetime
    finished_at: datetime | None
    error_code: str | None


class AgentRunErrorOut(BaseModel):
    id: UUID
    agent_step_id: UUID | None
    code: str
    category: str
    safe_message: str
    details: dict[str, Any]
    retryable: bool
    occurred_at: datetime


class AgentRetryOut(BaseModel):
    id: UUID
    retry_number: int
    reason_code: str
    scheduled_at: datetime
    started_at: datetime | None


class ArtifactOut(BaseModel):
    id: UUID
    task_id: UUID | None
    application_id: UUID | None
    artifact_type: str
    title: str
    version: int
    status: str
    mime_type: str | None
    created_at: datetime


class AgentRunDetail(AgentRunSummary):
    workflow_key: str | None
    workflow_version: str | None
    input: dict[str, Any]
    output: dict[str, Any]
    steps: list[AgentStepOut]
    tool_calls: list[ToolCallOut]
    errors: list[AgentRunErrorOut]
    retries: list[AgentRetryOut]
    artifacts: list[ArtifactOut]


def _run_summary(run: AgentRun, agent: Agent | None, workflow_run: WorkflowRun | None):
    return {
        "id": run.id,
        "workflow_run_id": run.workflow_run_id,
        "task_id": run.task_id,
        "agent_key": agent.key if agent else None,
        "agent_name": run.agent_name,
        "status": run.status,
        "current_step": workflow_run.current_step if workflow_run else None,
        "model": run.model,
        "prompt_version": run.prompt_version,
        "total_tokens": run.total_tokens,
        "cost_usd": run.cost_usd,
        "latency_ms": run.latency_ms,
        "retry_count": run.retry_count,
        "created_at": run.created_at,
        "started_at": run.started_at,
        "finished_at": run.finished_at,
        "error_code": run.error_code,
    }


@router.get("/agents", response_model=list[AgentSummary])
def list_agents(
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
):
    completed_run_id = case((AgentRun.status == "completed", AgentRun.id))
    failed_run_id = case((AgentRun.status == "failed", AgentRun.id))
    metrics_rows = db.execute(
        select(
            AgentStep.agent_id,
            func.count(func.distinct(AgentStep.agent_run_id)),
            func.count(func.distinct(completed_run_id)),
            func.count(func.distinct(failed_run_id)),
            func.avg(AgentStep.latency_ms),
            func.max(AgentRun.created_at),
        )
        .join(AgentRun, AgentRun.id == AgentStep.agent_run_id)
        .where(AgentRun.tenant_id == principal.tenant_id)
        .group_by(AgentStep.agent_id)
    ).all()
    metrics = {
        agent_id: (run_count, completed_runs, failed_runs, latency, last_run_at)
        for agent_id, run_count, completed_runs, failed_runs, latency, last_run_at in metrics_rows
    }
    agents = db.scalars(select(Agent).order_by(Agent.created_at, Agent.name)).all()
    result = []
    for agent in agents:
        run_count, completed_runs, failed_runs, average_latency_ms, last_run_at = metrics.get(
            agent.id, (0, 0, 0, None, None)
        )
        completed_count = int(completed_runs or 0)
        failed_count = int(failed_runs or 0)
        terminal_count = completed_count + failed_count
        result.append(
            AgentSummary(
                id=agent.id,
                key=agent.key,
                name=agent.name,
                description=agent.description,
                version=agent.version,
                status=agent.status,
                run_count=int(run_count or 0),
                completed_runs=completed_count,
                failed_runs=failed_count,
                success_rate=round(completed_count / terminal_count, 4) if terminal_count else None,
                average_latency_ms=(
                    round(float(average_latency_ms), 1) if average_latency_ms is not None else None
                ),
                tasks_completed=completed_count,
                last_run_at=last_run_at,
            )
        )
    return result


@router.get("/agent-runs", response_model=list[AgentRunSummary])
def list_agent_runs(
    status: RunStatus | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
):
    query = (
        select(AgentRun, Agent, WorkflowRun)
        .outerjoin(Agent, Agent.id == AgentRun.agent_id)
        .outerjoin(WorkflowRun, WorkflowRun.id == AgentRun.workflow_run_id)
        .where(AgentRun.tenant_id == principal.tenant_id)
    )
    if status:
        query = query.where(AgentRun.status == status)
    rows = db.execute(query.order_by(AgentRun.created_at.desc()).limit(limit)).all()
    return [_run_summary(run, agent, workflow_run) for run, agent, workflow_run in rows]


@router.get("/agent-runs/{run_id}", response_model=AgentRunDetail)
def get_agent_run(
    run_id: UUID,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
):
    row = db.execute(
        select(AgentRun, Agent, WorkflowRun, Workflow)
        .outerjoin(Agent, Agent.id == AgentRun.agent_id)
        .outerjoin(WorkflowRun, WorkflowRun.id == AgentRun.workflow_run_id)
        .outerjoin(Workflow, Workflow.id == WorkflowRun.workflow_id)
        .where(AgentRun.id == run_id, AgentRun.tenant_id == principal.tenant_id)
    ).one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Agent Run not found")
    run, agent, workflow_run, workflow = row
    steps = db.scalars(
        select(AgentStep)
        .where(AgentStep.agent_run_id == run.id, AgentStep.tenant_id == principal.tenant_id)
        .order_by(AgentStep.sequence)
    ).all()
    tool_calls = db.scalars(
        select(ToolCall)
        .where(ToolCall.agent_run_id == run.id, ToolCall.tenant_id == principal.tenant_id)
        .order_by(ToolCall.started_at)
    ).all()
    errors = db.scalars(
        select(AgentRunError)
        .where(AgentRunError.agent_run_id == run.id, AgentRunError.tenant_id == principal.tenant_id)
        .order_by(AgentRunError.occurred_at)
    ).all()
    retries = db.scalars(
        select(AgentRetry)
        .where(AgentRetry.agent_run_id == run.id, AgentRetry.tenant_id == principal.tenant_id)
        .order_by(AgentRetry.retry_number)
    ).all()
    artifacts = db.scalars(
        select(Artifact)
        .where(Artifact.agent_run_id == run.id, Artifact.tenant_id == principal.tenant_id)
        .order_by(Artifact.version)
    ).all()
    return {
        **_run_summary(run, agent, workflow_run),
        "workflow_key": workflow.key if workflow else None,
        "workflow_version": workflow.version if workflow else None,
        "input": run.input_json,
        "output": run.output_json,
        "steps": [
            {
                "id": step.id,
                "sequence": step.sequence,
                "agent_id": step.agent_id,
                "step_type": step.step_type,
                "status": step.status,
                "input": step.input_json,
                "output": step.output_json,
                "verification": step.verification_json,
                "input_tokens": step.input_tokens,
                "output_tokens": step.output_tokens,
                "cost_usd": step.cost_usd,
                "latency_ms": step.latency_ms,
                "started_at": step.started_at,
                "finished_at": step.finished_at,
                "error_code": step.error_code,
            }
            for step in steps
        ],
        "tool_calls": [
            {
                "id": tool.id,
                "agent_step_id": tool.agent_step_id,
                "tool_name": tool.tool_name,
                "status": tool.status,
                "arguments": tool.arguments_json,
                "result": tool.result_json,
                "latency_ms": tool.latency_ms,
                "started_at": tool.started_at,
                "finished_at": tool.finished_at,
                "error_code": tool.error_code,
            }
            for tool in tool_calls
        ],
        "errors": [
            {
                "id": error.id,
                "agent_step_id": error.agent_step_id,
                "code": error.code,
                "category": error.category,
                "safe_message": error.safe_message,
                "details": error.details_json,
                "retryable": error.retryable,
                "occurred_at": error.occurred_at,
            }
            for error in errors
        ],
        "retries": [
            {
                "id": retry.id,
                "retry_number": retry.retry_number,
                "reason_code": retry.reason_code,
                "scheduled_at": retry.scheduled_at,
                "started_at": retry.started_at,
            }
            for retry in retries
        ],
        "artifacts": [
            {
                "id": artifact.id,
                "task_id": artifact.task_id,
                "application_id": artifact.application_id,
                "artifact_type": artifact.artifact_type,
                "title": artifact.title,
                "version": artifact.version,
                "status": artifact.status,
                "mime_type": artifact.mime_type,
                "created_at": artifact.created_at,
            }
            for artifact in artifacts
        ],
    }
