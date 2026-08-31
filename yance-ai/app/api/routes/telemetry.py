from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import Principal, get_principal
from app.core.db import get_db
from app.models.models import AgentRun, AnalyticsEvent
from app.schemas.schemas import AgentRunCreate, AgentRunFinish, AnalyticsEventCreate, Message

router = APIRouter(tags=["analytics", "agent-runs"])


@router.post("/analytics/events", response_model=Message, status_code=202)
def capture_event(
    payload: AnalyticsEventCreate,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> Message:
    db.add(
        AnalyticsEvent(
            tenant_id=principal.tenant_id,
            user_id=principal.user.id,
            **payload.model_dump(),
        )
    )
    db.commit()
    return Message(message="accepted")


@router.post("/agent-runs", status_code=201)
def start_agent_run(
    payload: AgentRunCreate,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> dict:
    run = AgentRun(
        tenant_id=principal.tenant_id,
        user_id=principal.user.id,
        **payload.model_dump(),
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return {"id": run.id, "status": run.status, "started_at": run.started_at}


@router.patch("/agent-runs/{run_id}")
def finish_agent_run(
    run_id: UUID,
    payload: AgentRunFinish,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> dict:
    run = db.scalar(
        select(AgentRun).where(AgentRun.id == run_id, AgentRun.tenant_id == principal.tenant_id)
    )
    if not run:
        raise HTTPException(status_code=404, detail="Agent run not found")
    for key, value in payload.model_dump().items():
        setattr(run, key, value)
    run.finished_at = datetime.now(UTC)
    db.commit()
    return {"id": run.id, "status": run.status, "finished_at": run.finished_at}
