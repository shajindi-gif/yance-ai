"""Policy Evaluation Engine — Schemas (Pydantic structured output)"""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class CriterionResult(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    INSUFFICIENT = "INSUFFICIENT"


class OverallResult(StrEnum):
    ELIGIBLE = "ELIGIBLE"
    NOT_ELIGIBLE = "NOT_ELIGIBLE"
    INSUFFICIENT_INFO = "INSUFFICIENT_INFO"


class CriterionEvaluation(BaseModel):
    criterion: str = Field(description="政策条件描述")
    enterprise_fact: str = Field(description="企业对应事实")
    policy_requirement: str = Field(description="政策原文要求")
    evidence_quote: str = Field(default="", description="政策原文引用")
    evidence_source: str = Field(default="", description="来源")
    result: CriterionResult
    reason: str = Field(default="", description="判定理由")
    missing_information: str = Field(default="", description="缺失信息说明")
    confidence: float = Field(default=0.5, ge=0, le=1)


class EvidenceItem(BaseModel):
    source_type: str = "policy_document"
    source_title: str = ""
    source_url: str = ""
    publisher: str = ""
    quote: str = Field(default="", description="原文引用片段")
    reference: str = Field(default="", description="对应条款编号或章节")
    confidence: float = Field(default=0.8, ge=0, le=1)


class MissingMaterial(BaseModel):
    material: str
    reason: str = ""
    urgency: str = "normal"  # high / normal / low


class RiskItem(BaseModel):
    risk: str
    severity: str = "medium"  # high / medium / low
    mitigation: str = ""


class NextBestAction(BaseModel):
    action: str
    description: str = ""
    product_code: str | None = None
    cta: str = ""


class PolicyEvaluationResult(BaseModel):
    """Policy Evaluation Engine 统一输出"""

    overall_result: OverallResult
    matched_policy_id: str = ""
    matched_policy_title: str = ""
    criteria: list[CriterionEvaluation] = Field(default_factory=list)
    hard_failures: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    missing_materials: list[MissingMaterial] = Field(default_factory=list)
    risks: list[RiskItem] = Field(default_factory=list)
    next_best_actions: list[NextBestAction] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    summary: str = ""
    model_metadata: dict[str, Any] = Field(default_factory=dict)


class CriteriaExtraction(BaseModel):
    """LLM Step 1: 从政策原文提取硬性条件"""

    criteria: list[dict[str, str]] = Field(
        default_factory=list, description="每项 {criterion: 条件描述, policy_quote: 原文引用}"
    )


class EligibilityJudgment(BaseModel):
    """LLM Step 2: 逐项判定"""

    criteria: list[CriterionEvaluation]
    overall_result: OverallResult
    summary: str = ""
