"""
Ekodi – Feedback routes.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.models.feedback import Feedback
from app.models.conversation import Message

router = APIRouter(tags=["feedback"])


class FeedbackRequest(BaseModel):
    message_id: str
    rating: int = Field(..., ge=-1, le=1)  # -1 = down, 1 = up
    comment: str | None = None


@router.post("/feedback")
async def submit_feedback(
    req: FeedbackRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit feedback (thumbs up/down) on an AI message."""
    # Verify message exists
    result = await db.execute(select(Message).where(Message.id == req.message_id))
    msg = result.scalar_one_or_none()
    if not msg:
        raise HTTPException(404, "Message not found")

    # Check for existing feedback
    result = await db.execute(
        select(Feedback).where(
            Feedback.user_id == user.id,
            Feedback.message_id == req.message_id,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        existing.rating = req.rating
        existing.comment = req.comment
    else:
        fb = Feedback(
            user_id=user.id,
            message_id=req.message_id,
            rating=req.rating,
            comment=req.comment,
        )
        db.add(fb)

    return {"status": "ok"}
