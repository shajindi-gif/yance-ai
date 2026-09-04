import re
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.models import Policy, PolicyChunk, PolicyVersion
from app.services.policies.visibility import visible_policy_clause


@dataclass(frozen=True)
class PolicyCandidate:
    policy: Policy
    similarity: float
    chunk_ids: tuple[UUID, ...]


def _tokens(text: str) -> set[str]:
    normalized = re.sub(r"\s+", "", text.lower())
    chinese = {normalized[index : index + 2] for index in range(max(0, len(normalized) - 1))}
    words = set(re.findall(r"[a-z0-9][a-z0-9._+-]+", text.lower()))
    return {item for item in chinese | words if item}


def _lexical_score(query_tokens: set[str], content: str) -> float:
    if not query_tokens:
        return 0
    matches = len(query_tokens & _tokens(content))
    return matches / len(query_tokens)


def hybrid_policy_candidates(
    db: Session,
    *,
    tenant_id: UUID,
    query: str,
    query_vector: list[float],
    limit: int = 50,
) -> list[PolicyCandidate]:
    """Character/term lexical retrieval + vector retrieval + deterministic RRF."""
    latest = (
        select(PolicyVersion.policy_id, func.max(PolicyVersion.version).label("latest_version"))
        .group_by(PolicyVersion.policy_id)
        .subquery()
    )
    base = (
        select(PolicyChunk)
        .join(PolicyVersion, PolicyVersion.id == PolicyChunk.policy_version_id)
        .join(
            latest,
            (latest.c.policy_id == PolicyVersion.policy_id)
            & (latest.c.latest_version == PolicyVersion.version),
        )
        .join(Policy, Policy.id == PolicyChunk.policy_id)
        .where(
            visible_policy_clause(tenant_id),
            Policy.status == "published",
            or_(PolicyChunk.tenant_id.is_(None), PolicyChunk.tenant_id == tenant_id),
        )
    )
    lexical_pool = list(db.scalars(base.order_by(PolicyChunk.created_at.desc()).limit(500)).all())
    query_tokens = _tokens(query)
    lexical = sorted(
        ((chunk, _lexical_score(query_tokens, chunk.content)) for chunk in lexical_pool),
        key=lambda item: item[1],
        reverse=True,
    )[:100]
    vector = list(
        db.scalars(
            base.where(PolicyChunk.embedding.isnot(None))
            .order_by(PolicyChunk.embedding.cosine_distance(query_vector))
            .limit(100)
        ).all()
    )

    fused: dict[UUID, float] = {}
    chunks_by_policy: dict[UUID, set[UUID]] = {}
    for ranking in (
        [chunk for chunk, score in lexical if score > 0],
        vector,
    ):
        for rank, chunk in enumerate(ranking, start=1):
            fused[chunk.policy_id] = fused.get(chunk.policy_id, 0) + 1 / (60 + rank)
            chunks_by_policy.setdefault(chunk.policy_id, set()).add(chunk.id)
    if not fused:
        return []
    policies = {
        item.id: item
        for item in db.scalars(
            select(Policy).where(Policy.id.in_(fused), visible_policy_clause(tenant_id))
        ).all()
    }
    ranked = sorted(fused, key=fused.get, reverse=True)[:limit]
    ceiling = max(fused.values()) or 1
    return [
        PolicyCandidate(
            policy=policies[policy_id],
            similarity=min(1, fused[policy_id] / ceiling),
            chunk_ids=tuple(chunks_by_policy.get(policy_id, set())),
        )
        for policy_id in ranked
        if policy_id in policies
    ]
