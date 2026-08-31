from uuid import UUID

from fastapi import APIRouter, Depends, Form, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import Principal, get_principal, require_roles
from app.core.db import get_db
from app.models.models import Policy, PolicyRule, UserRole
from app.schemas.schemas import PolicyCreate, PolicyOut, PolicyRuleCreate, PolicyRuleOut

router = APIRouter(tags=["policy", "policy_rule"])


@router.get("/policies", response_model=list[PolicyOut])
def list_policies(
    principal: Principal = Depends(get_principal), db: Session = Depends(get_db)
) -> list[Policy]:
    return list(db.scalars(select(Policy).where(Policy.tenant_id == principal.tenant_id)).all())


@router.post("/policies", response_model=PolicyOut, status_code=201)
async def create_policy(
    payload: PolicyCreate,
    principal: Principal = Depends(require_roles(UserRole.owner, UserRole.admin, UserRole.member)),
    db: Session = Depends(get_db),
) -> Policy:
    data = payload.model_dump()
    if data.get("content"):
        from app.services.llm.registry import embed_texts

        embeddings = await embed_texts([data["content"]])
        data["embedding"] = embeddings[0]
    policy = Policy(tenant_id=principal.tenant_id, **data)
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return policy


@router.get("/policies/{policy_id}", response_model=PolicyOut)
def get_policy(
    policy_id: UUID,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> Policy:
    policy = db.scalar(
        select(Policy).where(Policy.id == policy_id, Policy.tenant_id == principal.tenant_id)
    )
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    return policy


@router.put("/policies/{policy_id}", response_model=PolicyOut)
async def update_policy(
    policy_id: UUID,
    payload: PolicyCreate,
    principal: Principal = Depends(require_roles(UserRole.owner, UserRole.admin, UserRole.member)),
    db: Session = Depends(get_db),
) -> Policy:
    policy = db.scalar(
        select(Policy).where(Policy.id == policy_id, Policy.tenant_id == principal.tenant_id)
    )
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    data = payload.model_dump()
    if data.get("content"):
        from app.services.llm.registry import embed_texts

        embeddings = await embed_texts([data["content"]])
        data["embedding"] = embeddings[0]
    else:
        data["embedding"] = None

    for key, value in data.items():
        setattr(policy, key, value)
    db.commit()
    db.refresh(policy)
    return policy


@router.post("/test-embed")
async def test_embed(text: str = Form(...)):
    from app.services.llm.registry import embed_texts

    vecs = await embed_texts([text])
    return {"dims": len(vecs[0]), "first_3": vecs[0][:3]}


@router.post("/policies/search", response_model=list[PolicyOut])
async def search_policies(
    query: str = Form(...),
    limit: int = Form(default=5),
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> list[Policy]:
    """语义搜索策略：将查询文本向量化，用 PGVector cosine 近似度排序返回。"""
    from app.services.llm.registry import embed_texts

    embeddings = await embed_texts([query])
    query_vector = embeddings[0]

    results = (
        db.query(Policy)
        .filter(
            Policy.tenant_id == principal.tenant_id,
            Policy.embedding.isnot(None),
        )
        .order_by(Policy.embedding.cosine_distance(query_vector))
        .limit(limit)
        .all()
    )
    return results


@router.get("/policy-rules", response_model=list[PolicyRuleOut])
def list_policy_rules(
    principal: Principal = Depends(get_principal), db: Session = Depends(get_db)
) -> list[PolicyRule]:
    return list(
        db.scalars(select(PolicyRule).where(PolicyRule.tenant_id == principal.tenant_id)).all()
    )


@router.post("/policy-rules", response_model=PolicyRuleOut, status_code=201)
def create_policy_rule(
    payload: PolicyRuleCreate,
    principal: Principal = Depends(require_roles(UserRole.owner, UserRole.admin, UserRole.member)),
    db: Session = Depends(get_db),
) -> PolicyRule:
    policy_exists = db.scalar(
        select(Policy.id).where(
            Policy.id == payload.policy_id, Policy.tenant_id == principal.tenant_id
        )
    )
    if not policy_exists:
        raise HTTPException(status_code=404, detail="Policy not found")
    rule = PolicyRule(tenant_id=principal.tenant_id, **payload.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule
