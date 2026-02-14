"""
Ekodi – Rate limiter with tier-aware limits and brute force protection.
In-memory for dev, Redis-backed in production.
"""

import time
import logging
from collections import defaultdict
from datetime import date, timezone, datetime

from fastapi import HTTPException, Request, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User

logger = logging.getLogger(__name__)

# In-memory stores
_requests: dict[str, list[float]] = defaultdict(list)
_login_attempts: dict[str, list[float]] = defaultdict(list)

WINDOW = 60  # seconds
DEFAULT_LIMIT = 60  # requests per minute
LOGIN_WINDOW = 900  # 15 minutes
LOGIN_MAX_ATTEMPTS = 5


def check_rate_limit(key: str, limit: int = DEFAULT_LIMIT) -> dict:
    """Check if a key has exceeded rate limits. Returns rate limit info."""
    now = time.time()
    window_start = now - WINDOW

    # Prune old entries
    _requests[key] = [t for t in _requests[key] if t > window_start]

    remaining = max(0, limit - len(_requests[key]))

    if len(_requests[key]) >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Max {limit} requests per minute.",
            headers={
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": "0",
                "Retry-After": str(WINDOW),
            },
        )

    _requests[key].append(now)
    return {"limit": limit, "remaining": remaining - 1}


def check_login_rate(ip: str):
    """Brute force protection: max 5 login attempts per 15 min per IP."""
    now = time.time()
    window_start = now - LOGIN_WINDOW

    _login_attempts[ip] = [t for t in _login_attempts[ip] if t > window_start]

    if len(_login_attempts[ip]) >= LOGIN_MAX_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again in 15 minutes.",
        )

    _login_attempts[ip].append(now)


async def rate_limit_middleware(request: Request, limit: int = DEFAULT_LIMIT):
    """Use as a FastAPI dependency for rate limiting."""
    client_ip = request.client.host if request.client else "unknown"
    key = f"{client_ip}:{request.url.path}"
    check_rate_limit(key, limit)


async def check_user_prompt_limit(user: User, db: AsyncSession):
    """Check and enforce daily prompt limit based on user tier."""
    from app.middleware.permissions import get_tier_limits

    limits = get_tier_limits(user)
    max_prompts = limits.get("daily_prompts", 10)

    # Unlimited
    if max_prompts == -1:
        return

    today = date.today()

    # Reset counter if new day
    if user.prompt_reset_date != today:
        user.daily_prompt_count = 0
        user.prompt_reset_date = today

    if user.daily_prompt_count >= max_prompts:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Daily prompt limit reached ({max_prompts}). Upgrade your plan for more.",
            headers={"X-DailyPrompts-Remaining": "0"},
        )

    user.daily_prompt_count += 1
    await db.flush()
