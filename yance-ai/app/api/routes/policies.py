from uuid import UUID

from fastapi import APIRouter, Depends, Form, HTTPException
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.api.deps import Principal, get_principal, require_platform_admin, require_roles
from app.core.config import settings
from app.core.db import get_db
from app.models.models import (
    EligibilityRule,
    Policy,
    PolicyBenefit,
    PolicyChunk,
    PolicyRule,
    PolicyVersion,
    RequiredMaterial,
    UserRole,
)
from app.schemas.schemas import (
    EligibilityRuleCreate,
    EligibilityRuleOut,
    PolicyBenefitCreate,
    PolicyBenefitOut,
    PolicyCreate,
    PolicyOut,
    PolicyRuleCreate,
    PolicyRuleOut,
    RequiredMaterialCreate,
    RequiredMaterialOut,
)
from app.services.policies.eligibility import exact_quote_span
from app.services.policies.ingestion import latest_policy_version, version_and_chunk_policy
from app.services.policies.retrieval import hybrid_policy_candidates
from app.services.policies.visibility import visible_policy_clause

router = APIRouter(tags=["policy", "policy_rule"])


@router.get("/policies", response_model=list[PolicyOut])
def list_policies(
    principal: Principal = Depends(get_principal), db: Session = Depends(get_db)
) -> list[Policy]:
    return list(db.scalars(select(Policy).where(visible_policy_clause(principal.tenant_id))).all())


@router.post("/policies", response_model=PolicyOut, status_code=201)
async def create_policy(
    payload: PolicyCreate,
    principal: Principal = Depends(require_roles(UserRole.owner, UserRole.admin, UserRole.member)),
    db: Session = Depends(get_db),
) -> Policy:
    policy = Policy(tenant_id=principal.tenant_id, **payload.model_dump())
    db.add(policy)
    db.flush()
    await version_and_chunk_policy(db, policy)
    db.commit()
    db.refresh(policy)
    return policy


@router.get("/policies/evidence-search")
def evidence_search(
    q: str,
    limit: int = 10,
    level: str | None = None,
    jurisdiction: str | None = None,
    current_only: bool = False,
    include_low_quality: bool = False,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> dict:
    """Keyword evidence search — works with **no model configured**.

    Returns chunks with exact character spans inside an immutable policy version,
    so a UI can quote the source and a reviewer can re-check it.  Vector search
    (``POST /policies/search``) stays a separate, budgeted path; this endpoint must
    never call an embedding provider.
    """
    from app.services.policy_collection.keyword_search import keyword_search, searchable_counts

    hits = keyword_search(
        db,
        q,
        limit=limit,
        level=level,
        jurisdiction=jurisdiction,
        current_only=current_only,
        tenant_id=principal.tenant_id,
    )
    return {
        "query": q,
        "retrieval": "keyword_trigram",
        "count": len(hits),
        "hits": [hit.as_dict() for hit in hits],
        "corpus": searchable_counts(db, principal.tenant_id),
    }


@router.get("/policies/{policy_id}/versions/{version_id}")
def read_policy_version(
    policy_id: UUID, version_id: UUID,
    principal: Principal = Depends(get_principal), db: Session = Depends(get_db),
) -> dict:
    policy = db.scalar(select(Policy).where(
        Policy.id == policy_id, visible_policy_clause(principal.tenant_id),
    ))
    version = db.scalar(select(PolicyVersion).where(
        PolicyVersion.id == version_id, PolicyVersion.policy_id == policy_id,
    )) if policy else None
    if version is None:
        raise HTTPException(404, "Policy version not found")
    return {"id": str(version.id), "version": version.version,
            "title": version.title, "content": version.content,
            "source_url": version.source_url, "content_sha256": version.content_sha256}


@router.get("/policies/quality-summary")
def policy_quality_summary(
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> dict:
    """Distribution of the quality rubric across the corpus.

    This is the answer to "what are you actually delivering": how many documents
    pass the reliability/validity/utility bars, which axis they fail on, and why.
    Counts only — no document text leaves the database here.
    """
    from app.services.policy_collection.quality import RUBRIC_VERSION, summary

    return summary(db, rubric_version=RUBRIC_VERSION)


@router.get("/policies/{policy_id}/quality")
def policy_quality(
    policy_id: UUID,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> dict:
    """Per-document verdict: three axis scores, grade, timeline state and every issue.

    Returned with the *reasons* rather than a bare score so a customer can dispute a
    specific finding (e.g. "this was not repealed") instead of arguing with a number.
    """
    from app.services.policy_collection.quality import RUBRIC_VERSION

    policy = db.scalar(
        select(Policy).where(Policy.id == policy_id, visible_policy_clause(principal.tenant_id))
    )
    if policy is None:
        raise HTTPException(status_code=404, detail="policy_not_found")
    row = db.execute(
        text(
            "SELECT q.grade, q.delivery_tier, q.deliverable, q.reliability, q.validity, "
            "       q.utility, q.total, q.timeline_state, q.source_tier, q.verdict, "
            "       q.issues, q.signals, q.assessed_at, q.rubric_version "
            "FROM policy_quality_assessments q "
            "JOIN policy_versions v ON v.id = q.policy_version_id "
            "WHERE q.policy_id = CAST(:pid AS uuid) AND q.rubric_version = :rv "
            "ORDER BY v.version DESC LIMIT 1"
        ),
        {"pid": str(policy_id), "rv": RUBRIC_VERSION},
    ).mappings().first()
    if row is None:
        return {
            "policy_id": str(policy_id),
            "assessed": False,
            "reason": "not_yet_assessed",
            "deliverable": policy.quality_deliverable,
            "grade": policy.quality_grade,
        }
    return {
        "policy_id": str(policy_id),
        "assessed": True,
        "rubric_version": row["rubric_version"],
        "grade": row["grade"],
        "delivery_tier": row["delivery_tier"],
        "deliverable": row["deliverable"],
        "reliability": float(row["reliability"]),
        "validity": float(row["validity"]),
        "utility": float(row["utility"]),
        "total": float(row["total"]),
        "timeline_state": row["timeline_state"],
        "source_tier": row["source_tier"],
        "verdict": row["verdict"],
        "issues": row["issues"],
        "signals": row["signals"],
        "assessed_at": row["assessed_at"].isoformat() if row["assessed_at"] else None,
    }


@router.get("/policies/{policy_id}", response_model=PolicyOut)
def get_policy(
    policy_id: UUID,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> Policy:
    policy = db.scalar(
        select(Policy).where(
            Policy.id == policy_id,
            visible_policy_clause(principal.tenant_id),
        )
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

    for key, value in payload.model_dump().items():
        setattr(policy, key, value)
    await version_and_chunk_policy(db, policy)
    db.commit()
    db.refresh(policy)
    return policy


@router.post("/test-embed")
async def test_embed(
    text: str = Form(...),
    principal: Principal = Depends(require_roles(UserRole.owner, UserRole.admin)),
):
    if settings.app_env == "production" or not settings.demo_features_enabled:
        raise HTTPException(status_code=404, detail="Not found")
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
    """段落级词法 + 向量混合检索；返回去重后的可见政策。"""
    from app.services.llm.registry import embed_texts

    embeddings = await embed_texts([query])
    query_vector = embeddings[0]

    candidates = hybrid_policy_candidates(
        db,
        tenant_id=principal.tenant_id,
        query=query,
        query_vector=query_vector,
        limit=max(1, min(limit, 50)),
    )
    return [item.policy for item in candidates]


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
            Policy.id == payload.policy_id,
            visible_policy_clause(principal.tenant_id),
        )
    )
    if not policy_exists:
        raise HTTPException(status_code=404, detail="Policy not found")
    rule = PolicyRule(tenant_id=principal.tenant_id, **payload.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.get("/eligibility-rules", response_model=list[EligibilityRuleOut])
def list_eligibility_rules(
    policy_id: UUID,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> list[EligibilityRule]:
    policy = db.scalar(
        select(Policy).where(Policy.id == policy_id, visible_policy_clause(principal.tenant_id))
    )
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    return list(
        db.scalars(
            select(EligibilityRule)
            .where(
                EligibilityRule.policy_id == policy_id,
                (EligibilityRule.tenant_id.is_(None))
                | (EligibilityRule.tenant_id == principal.tenant_id),
            )
            .order_by(EligibilityRule.created_at)
        ).all()
    )


@router.post("/eligibility-rules", response_model=EligibilityRuleOut, status_code=201)
def create_eligibility_rule(
    payload: EligibilityRuleCreate,
    principal: Principal = Depends(require_roles(UserRole.owner, UserRole.admin)),
    db: Session = Depends(get_db),
) -> EligibilityRule:
    version = _owned_policy_version(
        db,
        policy_id=payload.policy_id,
        version_id=payload.policy_version_id,
        tenant_id=principal.tenant_id,
    )
    _require_citable_quote(db, version, payload.source_quote)
    data = payload.model_dump(exclude={"policy_version_id"})
    rule = EligibilityRule(
        tenant_id=principal.tenant_id,
        policy_version_id=version.id,
        **data,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


def _owned_policy_version(
    db: Session, *, policy_id: UUID, version_id: UUID | None, tenant_id: UUID
) -> PolicyVersion:
    policy = db.scalar(select(Policy).where(Policy.id == policy_id, Policy.tenant_id == tenant_id))
    if not policy:
        raise HTTPException(status_code=404, detail="Tenant policy not found")
    version = (
        db.scalar(
            select(PolicyVersion).where(
                PolicyVersion.id == version_id,
                PolicyVersion.policy_id == policy.id,
                PolicyVersion.tenant_id == tenant_id,
            )
        )
        if version_id
        else latest_policy_version(db, policy.id)
    )
    if not version:
        raise HTTPException(status_code=409, detail="Policy source version is required")
    return version


def _require_citable_quote(db: Session, version: PolicyVersion, quote: str) -> None:
    source_span = exact_quote_span(version.content, quote)
    chunks = db.scalars(
        select(PolicyChunk.content).where(PolicyChunk.policy_version_id == version.id)
    ).all()
    if source_span is None or not any(exact_quote_span(content, quote) for content in chunks):
        raise HTTPException(
            status_code=422,
            detail="source_quote must exactly match one indexed policy passage",
        )


@router.post("/required-materials", response_model=RequiredMaterialOut, status_code=201)
def create_required_material(
    payload: RequiredMaterialCreate,
    principal: Principal = Depends(require_roles(UserRole.owner, UserRole.admin)),
    db: Session = Depends(get_db),
) -> RequiredMaterial:
    version = _owned_policy_version(
        db,
        policy_id=payload.policy_id,
        version_id=payload.policy_version_id,
        tenant_id=principal.tenant_id,
    )
    _require_citable_quote(db, version, payload.source_quote)
    item = RequiredMaterial(
        tenant_id=principal.tenant_id,
        policy_version_id=version.id,
        **payload.model_dump(exclude={"policy_version_id"}),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.post("/policy-benefits", response_model=PolicyBenefitOut, status_code=201)
def create_policy_benefit(
    payload: PolicyBenefitCreate,
    principal: Principal = Depends(require_roles(UserRole.owner, UserRole.admin)),
    db: Session = Depends(get_db),
) -> PolicyBenefit:
    version = _owned_policy_version(
        db,
        policy_id=payload.policy_id,
        version_id=payload.policy_version_id,
        tenant_id=principal.tenant_id,
    )
    _require_citable_quote(db, version, payload.source_quote)
    item = PolicyBenefit(
        tenant_id=principal.tenant_id,
        policy_version_id=version.id,
        **payload.model_dump(exclude={"policy_version_id"}),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.post("/policies/parse-amounts")
def parse_support_amounts(
    principal: Principal = Depends(require_platform_admin),
    db: Session = Depends(get_db),
) -> dict:
    """Deterministically backfill structured funding facts from support_amount text.

    Platform-admin curation tool (writes global knowledge-base rows). Only
    parses values it can extract with confidence; everything else stays NULL
    (INSUFFICIENT EVIDENCE by design). Safe to re-run (idempotent).
    """
    from app.services.funding.amounts import infer_funding_type, parse_support_amount

    updated_amounts = 0
    updated_types = 0
    policies = list(
        db.scalars(
            select(Policy).where(Policy.support_amount.is_not(None), Policy.support_amount != "")
        ).all()
    )
    for policy in policies:
        if policy.funding_amount_min is None and policy.funding_amount_max is None:
            parsed = parse_support_amount(policy.support_amount)
            if parsed.parsed:
                policy.funding_amount_min = parsed.amount_min
                policy.funding_amount_max = parsed.amount_max
                if parsed.ratio is not None and policy.funding_ratio is None:
                    policy.funding_ratio = parsed.ratio
                updated_amounts += 1
        if policy.funding_type is None:
            inferred = infer_funding_type(policy.support_amount, policy.support_type)
            if inferred:
                policy.funding_type = inferred
                updated_types += 1
    db.commit()
    return {
        "scanned": len(policies),
        "amounts_backfilled": updated_amounts,
        "types_backfilled": updated_types,
    }
