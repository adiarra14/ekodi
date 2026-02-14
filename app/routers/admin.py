"""
Ekodi – Admin routes (dashboard, RBAC user/team management,
API key oversight, feedback, chat history, data retention, billing).
"""

import csv
import io
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select, func, or_, extract, cast, Date
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import (
    get_admin_user, hash_password, STAFF_ROLES,
    force_logout_user, get_active_session_count, get_all_session_counts,
)
from app.middleware.permissions import (
    require_permission, require_staff, has_permission,
    ROLE_PERMISSIONS, ROLE_TABS, TIER_LIMITS,
)
from app.models.user import User
from app.models.conversation import Conversation, Message
from app.models.api_key import ApiKey
from app.models.feedback import Feedback
from app.models.token_usage import TokenUsage

router = APIRouter(prefix="/admin", tags=["admin"])

VALID_ROLES = {"user", "superadmin", "admin", "support", "marketing", "finance", "moderator", "developer"}
VALID_TIERS = {"free", "standard", "pro", "business"}
DEPARTMENTS = {"support", "marketing", "finance", "engineering", "management"}


# ── Dashboard Stats ──────────────────────────────────────────

@router.get("/stats")
async def admin_stats(
    user: User = Depends(require_staff()),
    db: AsyncSession = Depends(get_db),
):
    """Get platform statistics."""
    if not has_permission(user, "stats.read"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No permission")

    users_count = (await db.execute(select(func.count(User.id)))).scalar() or 0
    staff_count = (await db.execute(select(func.count(User.id)).where(User.is_staff == True))).scalar() or 0
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

    # Tier breakdown
    tier_counts = {}
    for tier in VALID_TIERS:
        count = (await db.execute(select(func.count(User.id)).where(User.tier == tier))).scalar() or 0
        tier_counts[tier] = count

    # Token usage / billing summary
    total_tokens = (await db.execute(select(func.sum(TokenUsage.total_tokens)))).scalar() or 0
    total_cost = (await db.execute(select(func.sum(TokenUsage.total_cost)))).scalar() or 0
    total_requests = (await db.execute(select(func.count(TokenUsage.id)))).scalar() or 0

    # This month
    month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_tokens = (await db.execute(
        select(func.sum(TokenUsage.total_tokens)).where(TokenUsage.created_at >= month_start)
    )).scalar() or 0
    month_cost = (await db.execute(
        select(func.sum(TokenUsage.total_cost)).where(TokenUsage.created_at >= month_start)
    )).scalar() or 0
    month_requests = (await db.execute(
        select(func.count(TokenUsage.id)).where(TokenUsage.created_at >= month_start)
    )).scalar() or 0

    return {
        "users": users_count,
        "staff": staff_count,
        "conversations": convos_count,
        "messages": messages_count,
        "api_keys": keys_count,
        "api_usage": api_usage,
        "feedback": {
            "total": feedback_count,
            "positive": positive,
            "negative": negative,
        },
        "tiers": tier_counts,
        "billing": {
            "total_tokens": total_tokens,
            "total_cost": round(total_cost, 4),
            "total_requests": total_requests,
            "month_tokens": month_tokens,
            "month_cost": round(month_cost, 4),
            "month_requests": month_requests,
        },
    }


# ── Who Am I (for admin panel) ───────────────────────────────

@router.get("/me")
async def admin_me(user: User = Depends(require_staff())):
    """Return current staff user info + visible tabs."""
    role = user.role or "user"
    tabs = ROLE_TABS.get(role, [])
    perms = ROLE_PERMISSIONS.get(role, [])
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": role,
        "department": user.department,
        "tabs": tabs,
        "permissions": perms,
    }


# ── User Management ──────────────────────────────────────────

@router.get("/users")
async def admin_users(
    search: str = Query("", description="Search by name or email"),
    tier: str = Query("", description="Filter by tier"),
    is_active: str = Query("", description="Filter by active status: true/false"),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    user: User = Depends(require_permission("users.read")),
    db: AsyncSession = Depends(get_db),
):
    """List external users (non-staff) with search, filter, pagination."""
    q = select(User).where(User.is_staff == False)

    if search:
        q = q.where(or_(User.name.ilike(f"%{search}%"), User.email.ilike(f"%{search}%")))
    if tier and tier in VALID_TIERS:
        q = q.where(User.tier == tier)
    if is_active == "true":
        q = q.where(User.is_active == True)
    elif is_active == "false":
        q = q.where(User.is_active == False)

    # Count
    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    # Paginate
    q = q.order_by(User.created_at.desc()).offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(q)
    users = result.scalars().all()

    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "users": [
            {
                "id": u.id,
                "email": u.email,
                "name": u.name,
                "role": u.role,
                "tier": u.tier or "free",
                "is_active": u.is_active,
                "email_verified": u.email_verified,
                "last_login": u.last_login.isoformat() if u.last_login else None,
                "created_at": u.created_at.isoformat(),
            }
            for u in users
        ],
    }


# ── Team Management (staff) ──────────────────────────────────

@router.get("/team")
async def admin_team(
    user: User = Depends(require_permission("team.read")),
    db: AsyncSession = Depends(get_db),
):
    """List all staff members."""
    result = await db.execute(
        select(User).where(User.is_staff == True).order_by(User.created_at.desc())
    )
    members = result.scalars().all()
    return [
        {
            "id": m.id,
            "email": m.email,
            "name": m.name,
            "role": m.role,
            "department": m.department,
            "is_active": m.is_active,
            "last_login": m.last_login.isoformat() if m.last_login else None,
            "created_at": m.created_at.isoformat(),
        }
        for m in members
    ]


class CreateTeamMemberRequest(BaseModel):
    email: EmailStr
    name: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=6, max_length=100)
    role: str = Field(default="support")
    department: str = Field(default="support")


@router.post("/team")
async def create_team_member(
    req: CreateTeamMemberRequest,
    user: User = Depends(require_permission("team.write")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new staff member (admin/superadmin only)."""
    if req.role not in STAFF_ROLES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Invalid role. Must be one of: {', '.join(STAFF_ROLES)}")

    # Only superadmin can create admin/superadmin roles
    if req.role in ("superadmin", "admin") and user.role != "superadmin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only superadmin can create admin roles")

    # Check duplicate email
    existing = await db.execute(select(User).where(User.email == req.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")

    member = User(
        email=req.email,
        name=req.name,
        password_hash=hash_password(req.password),
        role=req.role,
        tier="pro",
        is_staff=True,
        department=req.department if req.department in DEPARTMENTS else "support",
        email_verified=True,
        consent_given=True,
        consent_date=datetime.now(timezone.utc),
    )
    db.add(member)
    await db.flush()
    await db.refresh(member)

    return {
        "id": member.id,
        "email": member.email,
        "name": member.name,
        "role": member.role,
        "department": member.department,
    }


# ── Create External User ─────────────────────────────────────

class CreateExternalUserRequest(BaseModel):
    email: EmailStr
    name: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=6, max_length=100)
    tier: str = Field(default="free")


@router.post("/users")
async def create_external_user(
    req: CreateExternalUserRequest,
    user: User = Depends(require_permission("users.write")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new external user (admin)."""
    if req.tier not in VALID_TIERS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Invalid tier. Must be one of: {', '.join(VALID_TIERS)}")

    existing = await db.execute(select(User).where(User.email == req.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")

    new_user = User(
        email=req.email,
        name=req.name,
        password_hash=hash_password(req.password),
        role="user",
        tier=req.tier,
        email_verified=True,
        consent_given=True,
        consent_date=datetime.now(timezone.utc),
    )
    db.add(new_user)
    await db.flush()
    await db.refresh(new_user)

    return {"id": new_user.id, "email": new_user.email, "name": new_user.name, "tier": new_user.tier}


# ── User Role/Tier Updates ───────────────────────────────────

class RoleUpdate(BaseModel):
    role: str


class TierUpdate(BaseModel):
    tier: str


class ActiveUpdate(BaseModel):
    is_active: bool


@router.patch("/users/{user_id}/role")
async def update_user_role(
    user_id: str,
    req: RoleUpdate,
    admin: User = Depends(require_permission("users.write")),
    db: AsyncSession = Depends(get_db),
):
    """Change a user's role."""
    if req.role not in VALID_ROLES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Invalid role. Must be one of: {', '.join(VALID_ROLES)}")
    if user_id == admin.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot change your own role")

    # Only superadmin can set admin/superadmin
    if req.role in ("superadmin", "admin") and admin.role != "superadmin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only superadmin can assign admin roles")

    result = await db.execute(select(User).where(User.id == user_id))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    target.role = req.role
    target.is_staff = req.role in STAFF_ROLES
    await db.flush()
    return {"id": target.id, "email": target.email, "role": target.role, "is_staff": target.is_staff}


@router.patch("/users/{user_id}/tier")
async def update_user_tier(
    user_id: str,
    req: TierUpdate,
    admin: User = Depends(require_permission("users.write")),
    db: AsyncSession = Depends(get_db),
):
    """Change a user's subscription tier."""
    if req.tier not in VALID_TIERS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Invalid tier. Must be one of: {', '.join(VALID_TIERS)}")

    result = await db.execute(select(User).where(User.id == user_id))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    target.tier = req.tier
    await db.flush()
    return {"id": target.id, "email": target.email, "tier": target.tier}


@router.patch("/users/{user_id}/active")
async def update_user_active(
    user_id: str,
    req: ActiveUpdate,
    admin: User = Depends(require_permission("users.write")),
    db: AsyncSession = Depends(get_db),
):
    """Activate or deactivate a user."""
    if user_id == admin.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot deactivate yourself")

    result = await db.execute(select(User).where(User.id == user_id))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    target.is_active = req.is_active
    await db.flush()
    return {"id": target.id, "email": target.email, "is_active": target.is_active}


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    admin: User = Depends(require_permission("users.delete")),
    db: AsyncSession = Depends(get_db),
):
    """Delete a user and all their data."""
    if user_id == admin.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot delete yourself")

    result = await db.execute(select(User).where(User.id == user_id))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    # Protect superadmin from deletion by non-superadmins
    if target.role == "superadmin" and admin.role != "superadmin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot delete a superadmin")

    await db.delete(target)
    await db.flush()
    return {"deleted": True, "email": target.email}


# ── API Key Admin ────────────────────────────────────────────

@router.get("/api-keys")
async def admin_api_keys(
    user: User = Depends(require_permission("apikeys.read")),
    db: AsyncSession = Depends(get_db),
):
    """List all API keys across all users."""
    result = await db.execute(
        select(ApiKey, User.email, User.name)
        .join(User, ApiKey.user_id == User.id)
        .order_by(ApiKey.created_at.desc())
    )
    rows = result.all()
    return [
        {
            "id": ak.id,
            "user_id": ak.user_id,
            "user_email": email,
            "user_name": name,
            "name": ak.name,
            "key_prefix": ak.key_prefix,
            "usage_count": ak.usage_count,
            "rate_limit": ak.rate_limit,
            "active": ak.active,
            "created_at": ak.created_at.isoformat(),
        }
        for ak, email, name in rows
    ]


class RateLimitUpdate(BaseModel):
    rate_limit: int


@router.patch("/api-keys/{key_id}/rate-limit")
async def update_key_rate_limit(
    key_id: str,
    req: RateLimitUpdate,
    admin: User = Depends(require_permission("apikeys.write")),
    db: AsyncSession = Depends(get_db),
):
    """Update rate limit for an API key."""
    result = await db.execute(select(ApiKey).where(ApiKey.id == key_id))
    ak = result.scalar_one_or_none()
    if not ak:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "API key not found")

    ak.rate_limit = req.rate_limit
    await db.flush()
    return {"id": ak.id, "rate_limit": ak.rate_limit}


@router.patch("/api-keys/{key_id}/revoke")
async def admin_revoke_key(
    key_id: str,
    admin: User = Depends(require_permission("apikeys.write")),
    db: AsyncSession = Depends(get_db),
):
    """Revoke any API key (admin)."""
    result = await db.execute(select(ApiKey).where(ApiKey.id == key_id))
    ak = result.scalar_one_or_none()
    if not ak:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "API key not found")

    ak.active = False
    await db.flush()
    return {"revoked": True, "id": ak.id}


# ── Feedback Management ──────────────────────────────────────

@router.get("/feedback")
async def admin_feedback(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    user: User = Depends(require_permission("feedback.read")),
    db: AsyncSession = Depends(get_db),
):
    """List all feedback entries with pagination."""
    count = (await db.execute(select(func.count(Feedback.id)))).scalar() or 0

    result = await db.execute(
        select(Feedback, User.name, User.email)
        .join(User, Feedback.user_id == User.id)
        .order_by(Feedback.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    rows = result.all()
    return {
        "total": count,
        "page": page,
        "per_page": per_page,
        "feedback": [
            {
                "id": f.id,
                "user_id": f.user_id,
                "user_name": name,
                "user_email": email,
                "message_id": f.message_id,
                "rating": f.rating,
                "comment": f.comment,
                "created_at": f.created_at.isoformat(),
            }
            for f, name, email in rows
        ],
    }


@router.delete("/feedback/{feedback_id}")
async def delete_feedback(
    feedback_id: str,
    admin: User = Depends(require_permission("feedback.delete")),
    db: AsyncSession = Depends(get_db),
):
    """Delete a feedback entry."""
    result = await db.execute(select(Feedback).where(Feedback.id == feedback_id))
    fb = result.scalar_one_or_none()
    if not fb:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Feedback not found")

    await db.delete(fb)
    await db.flush()
    return {"deleted": True}


# ── Admin Chat History Access ────────────────────────────────

@router.get("/users/{user_id}/conversations")
async def admin_user_conversations(
    user_id: str,
    admin: User = Depends(require_permission("chats.read")),
    db: AsyncSession = Depends(get_db),
):
    """View a user's conversations."""
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == user_id)
        .order_by(Conversation.updated_at.desc())
    )
    convos = result.scalars().all()

    data = []
    for c in convos:
        msg_result = await db.execute(
            select(Message).where(Message.conversation_id == c.id).order_by(Message.created_at)
        )
        msgs = msg_result.scalars().all()
        data.append({
            "id": c.id,
            "title": c.title,
            "created_at": c.created_at.isoformat(),
            "message_count": len(msgs),
            "messages": [
                {
                    "id": m.id,
                    "role": m.role,
                    "text_fr": m.text_fr,
                    "text_bm": m.text_bm,
                    "created_at": m.created_at.isoformat(),
                }
                for m in msgs
            ],
        })
    return data


@router.delete("/users/{user_id}/conversations")
async def admin_delete_user_conversations(
    user_id: str,
    admin: User = Depends(require_permission("chats.delete")),
    db: AsyncSession = Depends(get_db),
):
    """Delete all conversations for a specific user."""
    result = await db.execute(
        select(Conversation).where(Conversation.user_id == user_id)
    )
    convos = result.scalars().all()
    count = len(convos)
    for c in convos:
        await db.delete(c)
    await db.flush()
    return {"deleted": count}


# ── Data Export (CSV) ────────────────────────────────────────

@router.get("/export/users")
async def export_users_csv(
    admin: User = Depends(require_permission("export.read")),
    db: AsyncSession = Depends(get_db),
):
    """Export all users as CSV."""
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    users = result.scalars().all()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["id", "email", "name", "role", "tier", "is_staff", "is_active", "email_verified", "created_at", "last_login"])
    for u in users:
        writer.writerow([
            u.id, u.email, u.name, u.role, u.tier,
            u.is_staff, u.is_active, u.email_verified,
            u.created_at.isoformat(), u.last_login.isoformat() if u.last_login else "",
        ])

    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=ekodi-users.csv"},
    )


# ── Roles & Tiers Reference (for frontend dropdowns) ─────────

@router.get("/roles-config")
async def get_roles_config(user: User = Depends(require_staff())):
    """Return available roles, tiers, departments for admin UI."""
    return {
        "staff_roles": list(STAFF_ROLES),
        "tiers": list(VALID_TIERS),
        "departments": list(DEPARTMENTS),
        "tier_limits": TIER_LIMITS,
    }


# ── Billing & Token Usage ────────────────────────────────────

@router.get("/billing/overview")
async def billing_overview(
    admin: User = Depends(require_permission("stats.read")),
    db: AsyncSession = Depends(get_db),
):
    """Get billing overview: total cost, tokens, per-model breakdown."""
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Total all-time
    total_cost = (await db.execute(select(func.sum(TokenUsage.total_cost)))).scalar() or 0
    total_tokens = (await db.execute(select(func.sum(TokenUsage.total_tokens)))).scalar() or 0
    total_requests = (await db.execute(select(func.count(TokenUsage.id)))).scalar() or 0

    # This month
    month_cost = (await db.execute(
        select(func.sum(TokenUsage.total_cost)).where(TokenUsage.created_at >= month_start)
    )).scalar() or 0
    month_tokens = (await db.execute(
        select(func.sum(TokenUsage.total_tokens)).where(TokenUsage.created_at >= month_start)
    )).scalar() or 0
    month_requests = (await db.execute(
        select(func.count(TokenUsage.id)).where(TokenUsage.created_at >= month_start)
    )).scalar() or 0

    # Per-model breakdown
    model_rows = (await db.execute(
        select(
            TokenUsage.model,
            func.count(TokenUsage.id).label("requests"),
            func.sum(TokenUsage.prompt_tokens).label("prompt_tokens"),
            func.sum(TokenUsage.completion_tokens).label("completion_tokens"),
            func.sum(TokenUsage.total_tokens).label("total_tokens"),
            func.sum(TokenUsage.total_cost).label("total_cost"),
        ).group_by(TokenUsage.model)
    )).all()
    by_model = [
        {
            "model": r.model,
            "requests": r.requests,
            "prompt_tokens": r.prompt_tokens or 0,
            "completion_tokens": r.completion_tokens or 0,
            "total_tokens": r.total_tokens or 0,
            "total_cost": round(r.total_cost or 0, 4),
        }
        for r in model_rows
    ]

    # Per-endpoint breakdown
    endpoint_rows = (await db.execute(
        select(
            TokenUsage.endpoint,
            func.count(TokenUsage.id).label("requests"),
            func.sum(TokenUsage.total_cost).label("total_cost"),
        ).group_by(TokenUsage.endpoint)
    )).all()
    by_endpoint = [
        {
            "endpoint": r.endpoint,
            "requests": r.requests,
            "total_cost": round(r.total_cost or 0, 4),
        }
        for r in endpoint_rows
    ]

    return {
        "all_time": {
            "total_cost": round(total_cost, 4),
            "total_tokens": total_tokens,
            "total_requests": total_requests,
        },
        "this_month": {
            "total_cost": round(month_cost, 4),
            "total_tokens": month_tokens,
            "total_requests": month_requests,
        },
        "by_model": by_model,
        "by_endpoint": by_endpoint,
    }


@router.get("/billing/users")
async def billing_per_user(
    admin: User = Depends(require_permission("stats.read")),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
):
    """Get token usage and cost per user, sorted by highest cost."""
    offset = (page - 1) * per_page

    rows = (await db.execute(
        select(
            TokenUsage.user_id,
            func.count(TokenUsage.id).label("requests"),
            func.sum(TokenUsage.total_tokens).label("total_tokens"),
            func.sum(TokenUsage.total_cost).label("total_cost"),
        )
        .group_by(TokenUsage.user_id)
        .order_by(func.sum(TokenUsage.total_cost).desc())
        .offset(offset)
        .limit(per_page)
    )).all()

    total_users = (await db.execute(
        select(func.count(func.distinct(TokenUsage.user_id)))
    )).scalar() or 0

    # Enrich with user info
    user_ids = [r.user_id for r in rows]
    if user_ids:
        users_result = await db.execute(select(User).where(User.id.in_(user_ids)))
        users_map = {u.id: u for u in users_result.scalars().all()}
    else:
        users_map = {}

    items = []
    for r in rows:
        u = users_map.get(r.user_id)
        items.append({
            "user_id": r.user_id,
            "name": u.name if u else "Deleted",
            "email": u.email if u else "—",
            "tier": u.tier if u else "—",
            "role": u.role if u else "—",
            "is_staff": u.is_staff if u else False,
            "requests": r.requests,
            "total_tokens": r.total_tokens or 0,
            "total_cost": round(r.total_cost or 0, 6),
            "credits_balance": round(u.credits_balance or 0, 4) if u else 0,
        })

    return {"users": items, "total": total_users, "page": page, "per_page": per_page}


@router.get("/billing/daily")
async def billing_daily(
    admin: User = Depends(require_permission("stats.read")),
    db: AsyncSession = Depends(get_db),
    days: int = Query(30, ge=1, le=365),
):
    """Get daily token usage and cost for the last N days (for charts)."""
    since = datetime.now(timezone.utc) - timedelta(days=days)

    rows = (await db.execute(
        select(
            func.date(TokenUsage.created_at).label("day"),
            func.count(TokenUsage.id).label("requests"),
            func.sum(TokenUsage.total_tokens).label("total_tokens"),
            func.sum(TokenUsage.prompt_tokens).label("prompt_tokens"),
            func.sum(TokenUsage.completion_tokens).label("completion_tokens"),
            func.sum(TokenUsage.total_cost).label("total_cost"),
        )
        .where(TokenUsage.created_at >= since)
        .group_by(func.date(TokenUsage.created_at))
        .order_by(func.date(TokenUsage.created_at))
    )).all()

    return {
        "days": [
            {
                "date": str(r.day),
                "requests": r.requests,
                "total_tokens": r.total_tokens or 0,
                "prompt_tokens": r.prompt_tokens or 0,
                "completion_tokens": r.completion_tokens or 0,
                "total_cost": round(r.total_cost or 0, 6),
            }
            for r in rows
        ],
    }


@router.get("/billing/users/{user_id}")
async def billing_user_detail(
    user_id: str,
    admin: User = Depends(require_permission("users.read")),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
):
    """Get detailed token usage history for a specific user."""
    result = await db.execute(select(User).where(User.id == user_id))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    offset = (page - 1) * per_page
    total = (await db.execute(
        select(func.count(TokenUsage.id)).where(TokenUsage.user_id == user_id)
    )).scalar() or 0

    rows = (await db.execute(
        select(TokenUsage)
        .where(TokenUsage.user_id == user_id)
        .order_by(TokenUsage.created_at.desc())
        .offset(offset)
        .limit(per_page)
    )).scalars().all()

    return {
        "user": {
            "id": target.id,
            "name": target.name,
            "email": target.email,
            "tier": target.tier,
            "total_tokens_used": target.total_tokens_used or 0,
            "total_cost": round(target.total_cost or 0, 6),
            "credits_balance": round(target.credits_balance or 0, 4),
            "monthly_budget": round(target.monthly_budget or 0, 2),
        },
        "usage": [
            {
                "id": u.id,
                "model": u.model,
                "endpoint": u.endpoint,
                "prompt_tokens": u.prompt_tokens,
                "completion_tokens": u.completion_tokens,
                "total_tokens": u.total_tokens,
                "total_cost": round(u.total_cost, 6),
                "created_at": u.created_at.isoformat(),
            }
            for u in rows
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


class CreditUpdate(BaseModel):
    amount: float = Field(..., description="Credits to add (positive) or deduct (negative)")
    reason: str = Field(default="Manual adjustment", max_length=200)


@router.post("/billing/users/{user_id}/credits")
async def update_user_credits(
    user_id: str,
    req: CreditUpdate,
    admin: User = Depends(require_permission("users.write")),
    db: AsyncSession = Depends(get_db),
):
    """Add or deduct credits from a user's balance."""
    result = await db.execute(select(User).where(User.id == user_id))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    old_balance = target.credits_balance or 0
    target.credits_balance = old_balance + req.amount
    await db.flush()

    return {
        "user_id": user_id,
        "old_balance": round(old_balance, 4),
        "adjustment": req.amount,
        "new_balance": round(target.credits_balance, 4),
        "reason": req.reason,
    }


class BudgetUpdate(BaseModel):
    monthly_budget: float = Field(..., ge=0, description="Monthly budget in USD (0 = no limit)")


@router.patch("/billing/users/{user_id}/budget")
async def update_user_budget(
    user_id: str,
    req: BudgetUpdate,
    admin: User = Depends(require_permission("users.write")),
    db: AsyncSession = Depends(get_db),
):
    """Set monthly budget limit for a user."""
    result = await db.execute(select(User).where(User.id == user_id))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    target.monthly_budget = req.monthly_budget
    await db.flush()

    return {
        "user_id": user_id,
        "monthly_budget": round(target.monthly_budget, 2),
    }


@router.get("/billing/pricing")
async def get_pricing(admin: User = Depends(require_staff())):
    """Return current model pricing configuration."""
    from app.services.chat_ai import MODEL_PRICING, DEFAULT_MODEL
    return {
        "default_model": DEFAULT_MODEL,
        "models": MODEL_PRICING,
    }


# ── Session Management ───────────────────────────────────────

@router.get("/sessions")
async def admin_sessions(
    admin: User = Depends(require_permission("users.read")),
    db: AsyncSession = Depends(get_db),
):
    """Get active session counts for all users."""
    counts = get_all_session_counts()
    if not counts:
        return {"sessions": []}

    # Enrich with user info
    user_ids = list(counts.keys())
    result = await db.execute(select(User).where(User.id.in_(user_ids)))
    users = {u.id: u for u in result.scalars().all()}

    sessions = []
    for uid, count in counts.items():
        u = users.get(uid)
        if u:
            sessions.append({
                "user_id": uid,
                "name": u.name,
                "email": u.email,
                "role": u.role,
                "is_staff": u.is_staff,
                "active_sessions": count,
                "last_login": u.last_login.isoformat() if u.last_login else None,
            })
    sessions.sort(key=lambda s: s["active_sessions"], reverse=True)
    return {"sessions": sessions}


@router.get("/users/{user_id}/sessions")
async def admin_user_sessions(
    user_id: str,
    admin: User = Depends(require_permission("users.read")),
):
    """Get active session count for a specific user."""
    count = get_active_session_count(user_id)
    return {"user_id": user_id, "active_sessions": count}


@router.post("/users/{user_id}/force-logout")
async def admin_force_logout(
    user_id: str,
    admin: User = Depends(require_permission("users.write")),
    db: AsyncSession = Depends(get_db),
):
    """Force-logout a user: invalidate all their tokens."""
    if user_id == admin.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot force-logout yourself")

    result = await db.execute(select(User).where(User.id == user_id))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    # Protect superadmin from non-superadmins
    if target.role == "superadmin" and admin.role != "superadmin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot force-logout a superadmin")

    force_logout_user(user_id)
    return {"message": f"All sessions for {target.email} have been invalidated.", "email": target.email}


@router.get("/token-config")
async def admin_token_config(admin: User = Depends(require_staff())):
    """Return current token duration config."""
    from app.middleware.auth import (
        STAFF_ACCESS_HOURS, STAFF_REFRESH_DAYS,
        USER_ACCESS_HOURS, USER_REFRESH_DAYS,
    )
    return {
        "staff": {"access_hours": STAFF_ACCESS_HOURS, "refresh_days": STAFF_REFRESH_DAYS},
        "user": {"access_hours": USER_ACCESS_HOURS, "refresh_days": USER_REFRESH_DAYS},
    }


# ── Server Health (admin only) ───────────────────────────────

@router.get("/health")
async def admin_server_health(admin: User = Depends(require_staff())):
    """Detailed server health stats (admin only)."""
    from app.services.server_monitor import get_monitor, MAX_CONCURRENT_REQUESTS, CPU_THRESHOLD, MEMORY_THRESHOLD
    monitor = get_monitor()
    stats = monitor.get_stats()
    return {
        "status": monitor.get_status_level(),
        "active_requests": stats.active_requests,
        "total_requests": stats.total_requests,
        "total_errors": stats.total_errors,
        "total_rejected": stats.total_rejected,
        "error_rate": round(stats.total_errors / max(stats.total_requests, 1) * 100, 2),
        "cpu_percent": stats.cpu_percent,
        "memory_percent": stats.memory_percent,
        "memory_used_mb": stats.memory_used_mb,
        "memory_total_mb": stats.memory_total_mb,
        "avg_response_time_ms": stats.avg_response_time_ms,
        "uptime_seconds": stats.uptime_seconds,
        "is_overloaded": stats.is_overloaded,
        "overload_reason": stats.overload_reason,
        "limits": {
            "max_concurrent": MAX_CONCURRENT_REQUESTS,
            "cpu_threshold": CPU_THRESHOLD,
            "memory_threshold": MEMORY_THRESHOLD,
        },
    }
