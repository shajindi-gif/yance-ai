from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID


@dataclass
class VectorDocument:
    id: UUID
    text: str
    embedding: list[float]
    metadata: dict[str, Any] = field(default_factory=dict)


class VectorStore(ABC):
    """Swap this interface for Qdrant without changing application services."""

    @abstractmethod
    def upsert(self, *, tenant_id: UUID, documents: list[VectorDocument]) -> None:
        raise NotImplementedError

    @abstractmethod
    def search(
        self, *, tenant_id: UUID, embedding: list[float], limit: int = 10
    ) -> list[VectorDocument]:
        raise NotImplementedError

    @abstractmethod
    def delete(self, *, tenant_id: UUID, ids: list[UUID]) -> None:
        raise NotImplementedError
