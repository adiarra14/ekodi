"""
Ekodi – RBAC permission system.

Roles (internal/staff):
  superadmin, admin, support, marketing, finance, moderator, developer

Tiers (external users):
  free, standard, pro, business
"""

from functools import wraps
from fastapi import Depends, HTTPException, status
from app.middleware.auth import get_current_user
from app.models.user import User


# ── Permission Matrix ─────────────────────────────────────────

ROLE_PERMISSIONS: dict[str, list[str]] = {
    "superadmin": ["*"],
    "admin": [
        "users.read", "users.write", "users.delete",
        "team.read", "team.write",
        "feedback.read", "feedback.write", "feedback.delete",
        "apikeys.read", "apikeys.write", "apikeys.delete",
        "stats.read",
        "chats.read", "chats.delete",
        "export.read",
    ],
    "support": [
        "users.read",
        "feedback.read", "feedback.write",
        "chats.read",
        "stats.read",
    ],
    "marketing": [
        "stats.read",
        "users.read",
    ],
    "finance": [
        "stats.read",
        "apikeys.read",
        "usage.read",
        "export.read",
    ],
    "moderator": [
        "feedback.read", "feedback.write", "feedback.delete",
        "chats.read", "chats.delete",
    ],
    "developer": [
        "apikeys.read", "apikeys.write",
        "stats.read",
        "logs.read",
        "health.read",
    ],
    # Regular users have no admin permissions
    "user": [],
}

# ── Tier Limits ───────────────────────────────────────────────

TIER_LIMITS: dict[str, dict] = {
    "free": {
        "daily_prompts": 10,
        "max_api_keys": 0,
        "api_rate_limit": 0,  # no API access
    },
    "standard": {
        "daily_prompts": 100,
        "max_api_keys": 1,
        "api_rate_limit": 60,  # req/min
    },
    "pro": {
        "daily_prompts": -1,  # unlimited
        "max_api_keys": 5,
        "api_rate_limit": 200,
    },
    "business": {
        "daily_prompts": -1,  # unlimited
        "max_api_keys": 20,
        "api_rate_limit": 1000,
    },
}

# Staff members always get unlimited
STAFF_TIER = {
    "daily_prompts": -1,
    "max_api_keys": 20,
    "api_rate_limit": 1000,
}


def has_permission(user: User, permission: str) -> bool:
    """Check if a user has a specific permission."""
    role = user.role or "user"
    perms = ROLE_PERMISSIONS.get(role, [])

    if "*" in perms:
        return True

    # Check exact match
    if permission in perms:
        return True

    # Check wildcard (e.g. "feedback.*" matches "feedback.read")
    domain = permission.split(".")[0]
    if f"{domain}.*" in perms:
        return True

    return False


def get_tier_limits(user: User) -> dict:
    """Get the effective limits for a user based on tier and staff status."""
    if user.is_staff:
        return STAFF_TIER
    return TIER_LIMITS.get(user.tier or "free", TIER_LIMITS["free"])


def require_permission(permission: str):
    """FastAPI dependency that checks a specific permission."""
    async def _check(user: User = Depends(get_current_user)) -> User:
        if not user.is_staff and user.role == "user":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Staff access required",
            )
        if not has_permission(user, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission}",
            )
        return user
    return _check


def require_staff():
    """FastAPI dependency that requires any staff role."""
    async def _check(user: User = Depends(get_current_user)) -> User:
        if not user.is_staff:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Staff access required",
            )
        return user
    return _check


# ── Visible tabs per role (for frontend) ─────────────────────

ROLE_TABS: dict[str, list[str]] = {
    "superadmin": ["stats", "users", "team", "apikeys", "feedback", "chats", "sessions", "billing", "health"],
    "admin": ["stats", "users", "team", "apikeys", "feedback", "chats", "sessions", "billing", "health"],
    "support": ["stats", "users", "feedback"],
    "marketing": ["stats"],
    "finance": ["stats", "apikeys", "billing"],
    "moderator": ["feedback", "chats"],
    "developer": ["apikeys", "stats", "health"],
}
