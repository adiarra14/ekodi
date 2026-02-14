"""
Ekodi – Admin routes (dashboard, RBAC user/team management,
API key oversight, feedback, chat history, data retention).
"""

import csv
import io
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_admin_user, hash_password, STAFF_ROLES
from app.middleware.permissions import (
    require_permission, require_staff, has_permission,
    ROLE_PERMISSIONS, ROLE_TABS, TIER_LIMITS,
)
from app.models.user import User
from app.models.conversation import Conversation, Message
from app.models.api_key import ApiKey
from app.models.feedback import Feedback

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
