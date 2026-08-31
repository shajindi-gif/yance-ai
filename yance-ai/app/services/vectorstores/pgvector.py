from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.models import Policy
from app.services.vectorstores.base import VectorDocument, VectorStore


class PgVectorStore(VectorStore):
    def __init__(self, session: Session) -> None:
        self.session = session

    def upsert(self, *, tenant_id: UUID, documents: list[VectorDocument]) -> None:
        for document in documents:
            policy = self.session.scalar(
                select(Policy).where(Policy.id == document.id, Policy.tenant_id == tenant_id)
            )
            if not policy:
                raise ValueError(f"Policy {document.id} not found in tenant")
            policy.content = document.text
            policy.embedding = document.embedding
        self.session.commit()

    def search(
        self, *, tenant_id: UUID, embedding: list[float], limit: int = 10
    ) -> list[VectorDocument]:
        distance = Policy.embedding.cosine_distance(embedding)
        rows = self.session.execute(
            select(Policy, distance.label("distance"))
            .where(Policy.tenant_id == tenant_id, Policy.embedding.is_not(None))
            .order_by(distance)
            .limit(limit)
        ).all()
        return [
            VectorDocument(
                id=policy.id,
                text=policy.content or "",
                embedding=list(policy.embedding or []),
                metadata={"distance": float(distance_value), "title": policy.title},
            )
            for policy, distance_value in rows
        ]

    def delete(self, *, tenant_id: UUID, ids: list[UUID]) -> None:
        # Policies are retained; deleting vectors only clears their embeddings.
        policies = self.session.scalars(
            select(Policy).where(Policy.tenant_id == tenant_id, Policy.id.in_(ids))
        ).all()
        for policy in policies:
            policy.embedding = None
        self.session.commit()
