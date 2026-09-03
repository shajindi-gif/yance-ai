"""Policy Evaluation Engine API — Evidence-Grounded assessment"""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.deps import Principal, require_roles
from app.core.db import get_db
from app.models.models import AnalyticsEvent, Company, Policy, UserRole
from app.services.policy_engine.evaluator import evaluate_policy

router = APIRouter(prefix="/policy-engine", tags=["policy-engine"])


class EvaluateRequest(BaseModel):
    policy_id: str
    company_id: str
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
            Policy.id == uuid.UUID(req.policy_id),
            or_(Policy.tenant_id.is_(None), Policy.tenant_id == principal.tenant_id),
        )
    )
    if not policy:
        raise HTTPException(404, "政策不存在")
    company = db.scalar(
        select(Company).where(
            Company.id == uuid.UUID(req.company_id), Company.tenant_id == principal.tenant_id
        )
    )
    if not company:
        raise HTTPException(404, "企业不存在")

    company_profile = {
        "name": company.name,
        "industry": company.industry or "",
        "province": company.province or "",
        "city": company.city or "",
        **(company.metadata_json or {}),
    }

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
            "policy_id": req.policy_id,
            "company_id": req.company_id,
            "result": result.overall_result.value,
            "provider": req.provider,
        },
    )
    db.add(event)
    db.commit()

    return result.model_dump()
