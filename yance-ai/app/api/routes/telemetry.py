from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import Principal, get_principal
from app.core.db import get_db
from app.schemas.schemas import AgentRunCreate, AgentRunFinish, AnalyticsEventCreate, Message

router = APIRouter(tags=["analytics", "agent-runs"])


@router.post("/analytics/events", response_model=Message, status_code=202)
def capture_event(
    payload: AnalyticsEventCreate,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> Message:
    raise HTTPException(
        status_code=501,
        detail="Client-authored analytics are disabled until event provenance is enforced",
    )


@router.post("/agent-runs", status_code=201)
def start_agent_run(
    payload: AgentRunCreate,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> dict:
    raise HTTPException(
        status_code=501,
        detail="Agent runs can only be written by the server execution harness",
    )


@router.patch("/agent-runs/{run_id}")
def finish_agent_run(
    run_id: UUID,
    payload: AgentRunFinish,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> dict:
    raise HTTPException(
        status_code=501,
        detail="Agent runs can only be written by the server execution harness",
    )
