"""AI 报告生成：语义搜索 → LLM 分析 → 交付报告"""

import uuid

from fastapi import APIRouter, Depends, Form, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import Principal, require_roles
from app.core.db import get_db
from app.models.models import Policy, UserRole
from app.services.analytics.events import record_event
from app.services.billing.usage import QuotaExceeded, consume_usage_once
from app.services.llm.registry import embed_texts
from app.services.llm.router import LLMRouter
from app.services.policies.visibility import visible_policy_clause

router = APIRouter(tags=["reports"])

_llm = LLMRouter()


class ReportResponse(BaseModel):
    query: str
    matched_policies: list[dict]
    report: str
    model: str
    provider: str


@router.post("/reports/generate")
async def generate_report(
    query: str = Form(...),
    limit: int = Form(default=5),
    principal: Principal = Depends(require_roles(UserRole.owner, UserRole.admin, UserRole.member)),
    db: Session = Depends(get_db),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", max_length=128),
):
    """生成 AI 政策分析报告：语义搜索 + LLM 综合分析"""
    report_key = f"report:{idempotency_key or uuid.uuid4()}"
    try:
        _, created = consume_usage_once(
            db,
            tenant_id=principal.tenant_id,
            meter="reports",
            quantity=1,
            idempotency_key=report_key,
            user_id=principal.user.id,
            resource_type="report",
        )
    except QuotaExceeded as exc:
        db.rollback()
        raise HTTPException(status_code=429, detail=exc.detail()) from exc
    if not created:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail={
                "code": "idempotency_replay_unavailable",
                "message": "This report request was already processed; use a new idempotency key.",
            },
        )

    # 1. 语义搜索
    embeddings = await embed_texts([query])
    query_vector = embeddings[0]

    results = (
        db.query(Policy)
        .filter(
            visible_policy_clause(principal.tenant_id),
            Policy.embedding.isnot(None),
        )
        .order_by(Policy.embedding.cosine_distance(query_vector))
        .limit(limit)
        .all()
    )

    if not results:
        raise HTTPException(status_code=404, detail="No matching policies found")

    # 2. 构建 LLM Prompt
    policy_texts = "\n\n---\n\n".join(
        f"政策标题：{p.title}\n政策内容：{p.content or '(无内容)'}" for p in results
    )

    system_prompt = (
        "你是衍策引擎 AI 政策分析助手。根据用户查询和相关政策，生成一份结构化分析报告。"
        "报告格式：\n"
        "## 分析概述\n一句话总结\n\n"
        "## 匹配政策\n逐条列出相关政策和关键条款\n\n"
        "## 合规建议\n3-5 条可执行建议\n\n"
        "## 风险评估\n潜在风险和应对策略\n\n"
        "## 行动步骤\n推荐的下一步行动清单"
    )

    # 3. 调用 LLM
    from app.services.llm.base import LLMRequest

    response = await _llm.complete(
        LLMRequest(
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": f"用户查询：{query}\n\n匹配到以下政策：\n\n{policy_texts}",
                },
            ],
            model="qwen-plus",
            temperature=0.3,
            max_tokens=2048,
        )
    )

    record_event(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user.id,
        name="report_generated",
        event_key=f"report_generated:{report_key}",
        properties={"provider": response.provider, "model": response.model},
    )
    db.commit()

    return {
        "query": query,
        "matched_policies": [
            {"title": p.title, "id": str(p.id), "status": p.status or "draft"} for p in results
        ],
        "report": response.content,
        "model": response.model,
        "provider": response.provider,
    }
