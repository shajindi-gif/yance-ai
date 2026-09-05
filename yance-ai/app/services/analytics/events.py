from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.models import AnalyticsEvent


def record_event(
    db: Session,
    *,
    tenant_id: UUID,
    user_id: UUID | None,
    name: str,
    properties: dict | None = None,
    event_key: str | None = None,
    request_id: str | None = None,
) -> AnalyticsEvent:
    """Add a server-owned event, returning the existing row for a repeated event key."""
    if event_key:
        existing = db.scalar(
            select(AnalyticsEvent).where(
                AnalyticsEvent.tenant_id == tenant_id,
                AnalyticsEvent.event_key == event_key,
            )
        )
        if existing:
            return existing
    event = AnalyticsEvent(
        tenant_id=tenant_id,
        user_id=user_id,
        name=name,
        source="server",
        event_key=event_key,
        request_id=request_id,
        properties=properties or {},
    )
    db.add(event)
    return event
