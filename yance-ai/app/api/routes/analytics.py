from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import Principal, get_principal
from app.core.db import get_db
from app.models.models import Feedback
from app.schemas.schemas import FeedbackCreate

router = APIRouter(tags=["analytics", "feedback"])


@router.post("/feedback", status_code=201)
def create_feedback(
    payload: FeedbackCreate,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> dict:
    feedback = Feedback(
        tenant_id=principal.tenant_id,
        user_id=principal.user.id,
        category=payload.category,
        message=payload.message.strip(),
        route=payload.route,
        status="open",
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return {
        "id": str(feedback.id),
        "category": feedback.category,
        "status": feedback.status,
        "created_at": feedback.created_at,
    }
