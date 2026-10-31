from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import Principal, get_principal
from app.core.db import get_db
from app.models.models import Feedback, User
from app.schemas.schemas import FeedbackCreate
from app.services.analytics.events import record_event

router = APIRouter(tags=["analytics", "feedback"])


def _feedback_out(feedback: Feedback) -> dict:
    return {
        "id": str(feedback.id),
        "category": feedback.category,
        "message": feedback.message,
        "route": feedback.route,
        "status": feedback.status,
        "created_at": feedback.created_at,
        "updated_at": feedback.updated_at,
    }


@router.get("/feedback")
def list_my_feedback(
    limit: int = Query(default=20, ge=1, le=50),
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> list[dict]:
    """Private history for this user in this tenant, never a public review feed."""
    rows = db.scalars(
        select(Feedback)
        .where(
            Feedback.tenant_id == principal.tenant_id,
            Feedback.user_id == principal.user.id,
        )
        .order_by(Feedback.created_at.desc())
        .limit(limit)
    ).all()
    return [_feedback_out(row) for row in rows]


@router.post("/feedback", status_code=201)
def create_feedback(
    payload: FeedbackCreate,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> dict:
    if payload.client_request_id:
        # Serialize duplicate requests before lookup; legacy clients need no key.
        db.execute(
            select(User.id)
            .where(
                User.id == principal.user.id,
            )
            .with_for_update()
        )
        existing = db.scalar(
            select(Feedback).where(
                Feedback.tenant_id == principal.tenant_id,
                Feedback.user_id == principal.user.id,
                Feedback.client_request_id == payload.client_request_id,
            )
        )
        if existing:
            if (existing.category, existing.message, existing.route) != (
                payload.category,
                payload.message,
                payload.route,
            ):
                raise HTTPException(
                    status_code=409, detail="该反馈请求编号已用于其他内容，请重新提交。"
                )
            return _feedback_out(existing)
    feedback = Feedback(
        tenant_id=principal.tenant_id,
        user_id=principal.user.id,
        category=payload.category,
        message=payload.message,
        route=payload.route,
        client_request_id=payload.client_request_id,
        status="open",
    )
    db.add(feedback)
    db.flush()
    if feedback.category == "sales":
        record_event(db, tenant_id=principal.tenant_id, user_id=principal.user.id,
                     name="demo_request_submitted", event_key=f"demo_request:{feedback.id}",
                     properties={"feedback_id": str(feedback.id)})
    db.commit()
    db.refresh(feedback)
    return _feedback_out(feedback)
