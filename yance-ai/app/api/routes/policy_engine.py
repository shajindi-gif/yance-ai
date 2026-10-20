"""Policy Evaluation Engine API — Evidence-Grounded assessment"""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.deps import Principal, require_roles
from app.core.db import get_db
from app.models.models import AnalyticsEvent, Company, Policy, UserRole
from app.services.policies.applicability import policy_context_issues
from app.services.policies.ingestion import latest_policy_version
from app.services.policy_engine.evaluator import evaluate_policy
from app.services.policy_engine.schemas import OverallResult, PolicyEvaluationResult

router = APIRouter(prefix="/policy-engine", tags=["policy-engine"])


class EvaluateRequest(BaseModel):
    policy_id: uuid.UUID
    company_id: uuid.UUID
    provider: str = Field(default="deepseek", pattern="^(deepseek|qwen)$")


@router.post("/evaluate")
async def evaluate(
    req: EvaluateRequest,
    principal: Principal = Depends(require_roles(UserRole.owner, UserRole.admin, UserRole.member)),
    db: Session = Depends(get_db),
):
    """Evidence-Grounded 政策资格评估：PASS / FAIL / INSUFFICIENT 逐条件判定"""
    policy = db.scalar(
        select(Policy).where(
            Policy.id == req.policy_id,
            or_(Policy.tenant_id.is_(None), Policy.tenant_id == principal.tenant_id),
        )
    )
    if not policy:
        raise HTTPException(404, "政策不存在")
    company = db.scalar(
        select(Company).where(
            Company.id == req.company_id, Company.tenant_id == principal.tenant_id
        )
    )
    if not company:
        raise HTTPException(404, "企业不存在")

    company_profile = {
        **(company.metadata_json or {}),
        "name": company.name,
        "industry": company.industry or "",
        "province": company.province or "",
        "city": company.city or "",
    }

    version = latest_policy_version(db, policy.id)
    issues = policy_context_issues(policy, version, company_profile)
    if issues:
        return PolicyEvaluationResult(
            overall_result=OverallResult.INSUFFICIENT_INFO,
            matched_policy_id=str(policy.id), matched_policy_title=policy.title,
            summary="政策时效、地域或来源尚不满足评估前提，需人工复核。",
            missing_information=issues,
            model_metadata={"gate": "policy_context_v1", "llm_called": False},
        ).model_dump()

    result = await evaluate_policy(
        policy_id=str(policy.id),
        policy_title=policy.title,
        policy_content=policy.content or "",
        policy_level=policy.level or "",
        company_name=company.name,
        company_profile=company_profile,
        provider=req.provider,
    )

    # Track event
    event = AnalyticsEvent(
        tenant_id=principal.tenant_id,
        user_id=principal.user.id,
        name="policy_evaluation",
        properties={
            "policy_id": str(req.policy_id),
            "company_id": str(req.company_id),
            "result": result.overall_result.value,
            "provider": req.provider,
        },
    )
    db.add(event)
    db.commit()

    return result.model_dump()
