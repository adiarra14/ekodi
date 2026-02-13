"""
Ekodi – Admin routes (dashboard stats, user management).
"""

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_admin_user
from app.models.user import User
from app.models.conversation import Conversation, Message
from app.models.api_key import ApiKey
from app.models.feedback import Feedback

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/stats")
async def admin_stats(
    user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Get platform statistics."""
    users_count = (await db.execute(select(func.count(User.id)))).scalar() or 0
    convos_count = (await db.execute(select(func.count(Conversation.id)))).scalar() or 0
    messages_count = (await db.execute(select(func.count(Message.id)))).scalar() or 0
    keys_count = (await db.execute(select(func.count(ApiKey.id)))).scalar() or 0
    feedback_count = (await db.execute(select(func.count(Feedback.id)))).scalar() or 0

    positive = (
        await db.execute(select(func.count(Feedback.id)).where(Feedback.rating == 1))
    ).scalar() or 0
    negative = (
        await db.execute(select(func.count(Feedback.id)).where(Feedback.rating == -1))
    ).scalar() or 0

    api_usage = (
        await db.execute(select(func.sum(ApiKey.usage_count)))
    ).scalar() or 0

    return {
        "users": users_count,
        "conversations": convos_count,
        "messages": messages_count,
        "api_keys": keys_count,
        "api_usage": api_usage,
        "feedback": {
            "total": feedback_count,
            "positive": positive,
            "negative": negative,
        },
    }


@router.get("/users")
async def admin_users(
    user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """List all users."""
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    users = result.scalars().all()
    return [
        {
            "id": u.id,
            "email": u.email,
            "name": u.name,
            "role": u.role,
            "is_active": u.is_active,
            "created_at": u.created_at.isoformat(),
        }
        for u in users
    ]


@router.get("/feedback")
async def admin_feedback(
    user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """List all feedback entries."""
    result = await db.execute(
        select(Feedback).order_by(Feedback.created_at.desc()).limit(100)
    )
    feedbacks = result.scalars().all()
    return [
        {
            "id": f.id,
            "user_id": f.user_id,
            "message_id": f.message_id,
            "rating": f.rating,
            "comment": f.comment,
            "created_at": f.created_at.isoformat(),
        }
        for f in feedbacks
    ]
