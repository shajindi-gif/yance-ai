from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

AgentRunStatus = Literal[
    "queued", "planning", "running", "waiting", "review", "completed", "failed", "cancelled"
]
StepType = Literal["plan", "retrieve", "reason", "act", "verify", "finish"]


class VerificationFailed(RuntimeError):
    pass


class AgentCancelled(RuntimeError):
    pass


class PolicyScanWorkflowInput(BaseModel):
    tenant_id: UUID
    user_id: UUID
    task_id: UUID
    scan_id: UUID
    company_id: UUID
    profile_version_id: UUID


class PolicyScanWorkflowOutput(BaseModel):
    scan_id: UUID
    opportunity_ids: list[UUID]
    total_opportunities: int = Field(ge=0)
    artifact_id: UUID
    verification_passed: bool


class VerificationCheck(BaseModel):
    code: str
    passed: bool
    actual: int | str | bool | None = None


class VerificationResult(BaseModel):
    passed: bool
    checks: list[VerificationCheck]


class PlanOutput(BaseModel):
    workflow: Literal["policy_scan"] = "policy_scan"
    version: Literal["v2"] = "v2"
    steps: list[StepType]
    verification_required: bool = True


class RetrieveOutput(BaseModel):
    opportunity_ids: list[UUID]
    policy_ids: list[UUID]
    total: int = Field(ge=0)


class ReasonOutput(BaseModel):
    states: dict[str, int] = Field(default_factory=dict)
    reason: str


class ActOutput(BaseModel):
    deliverable_id: UUID
    artifact_id: UUID
    report_type: Literal["policy_scan_report"] = "policy_scan_report"
