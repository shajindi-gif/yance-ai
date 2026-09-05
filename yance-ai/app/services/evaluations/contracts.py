from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

EvalType = Literal[
    "policy_retrieval_eval",
    "eligibility_eval",
    "citation_eval",
    "hallucination_eval",
    "document_generation_eval",
]
Dimension = Literal[
    "correctness",
    "completeness",
    "evidence",
    "citation_accuracy",
    "hallucination",
    "actionability",
]
RiskTier = Literal["low", "medium", "high", "critical"]

EVAL_TYPES: tuple[EvalType, ...] = (
    "policy_retrieval_eval",
    "eligibility_eval",
    "citation_eval",
    "hallucination_eval",
    "document_generation_eval",
)
DIMENSIONS: tuple[Dimension, ...] = (
    "correctness",
    "completeness",
    "evidence",
    "citation_accuracy",
    "hallucination",
    "actionability",
)


class DatasetCard(BaseModel):
    key: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{2,119}$")
    name: str = Field(min_length=3, max_length=240)
    eval_type: EvalType
    description: str = Field(min_length=10, max_length=2000)
    version: str = Field(pattern=r"^[0-9]{4}\.[0-9]{2}\.[0-9]+$")
    target_key: str = Field(min_length=3, max_length=160)
    target_version: str = Field(min_length=1, max_length=80)
    scorer_version: str = Field(min_length=1, max_length=80)
    review_status: Literal["unreviewed", "reviewed", "deprecated"] = "unreviewed"
    reviewed_by: str | None = Field(default=None, max_length=160)
    reviewed_at: date | None = None
    data_classification: Literal["synthetic", "public", "authorized_deidentified"]
    contains_customer_data: bool = False
    is_demo: bool = False
    thresholds: dict[Dimension | Literal["overall"], float]

    @model_validator(mode="after")
    def reviewed_metadata_is_required(self) -> "DatasetCard":
        if self.review_status == "reviewed" and not (self.reviewed_by and self.reviewed_at):
            raise ValueError("reviewed datasets require reviewed_by and reviewed_at")
        if self.contains_customer_data:
            raise ValueError("repository datasets cannot contain customer data")
        return self


class EvidenceExpectation(BaseModel):
    reference: str = Field(min_length=1, max_length=500)
    required: bool = True


class EvalCaseContract(BaseModel):
    case_id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{2,159}$")
    eval_type: EvalType
    question: str = Field(min_length=3, max_length=4000)
    input: dict[str, Any]
    ground_truth: dict[str, Any]
    expected_evidence: list[EvidenceExpectation] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list, max_length=40)
    risk_tier: RiskTier
    reference_date: date | None = None
    dataset_version: str


class EvidenceObservation(BaseModel):
    expectation: str
    observed: str
    source_reference: str | None = None
    passed: bool


class TargetOutput(BaseModel):
    answer: dict[str, Any]
    evidence: list[EvidenceObservation] = Field(default_factory=list)
    error_types: list[str] = Field(default_factory=list)
    hallucination_detected: bool = False


class DimensionResult(BaseModel):
    dimension: Dimension
    score: float | None = Field(default=None, ge=0, le=1)
    is_applicable: bool = True
    rationale: str


class CaseExecution(BaseModel):
    case_id: str
    status: Literal["completed", "error"]
    model_answer: dict[str, Any] = Field(default_factory=dict)
    dimensions: list[DimensionResult]
    evidence: list[EvidenceObservation] = Field(default_factory=list)
    error_types: list[str] = Field(default_factory=list)
    error_code: str | None = None
    safe_error_message: str | None = None
    hallucination_detected: bool = False
    overall_score: float | None = Field(default=None, ge=0, le=1)
    passed: bool = False
    latency_ms: int = Field(default=0, ge=0)
    cost_usd: float = Field(default=0, ge=0)


class DatasetExecution(BaseModel):
    dataset: DatasetCard
    content_sha256: str
    cases: list[EvalCaseContract]
    results: list[CaseExecution]
    requested_cases: int
    completed_cases: int
    passed_cases: int
    error_cases: int
    total_latency_ms: int
    total_cost_usd: float
    release_gate_passed: bool
