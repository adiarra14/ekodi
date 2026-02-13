"""
Ekodi – Simple in-memory rate limiter (Redis-backed in production).
"""

import time
import logging
from collections import defaultdict

from fastapi import HTTPException, Request, status

logger = logging.getLogger(__name__)

# In-memory store: {key: [(timestamp, ...)] }
_requests: dict[str, list[float]] = defaultdict(list)
WINDOW = 60  # seconds
DEFAULT_LIMIT = 60  # requests per minute


def check_rate_limit(key: str, limit: int = DEFAULT_LIMIT):
    """Check if a key has exceeded rate limits."""
    now = time.time()
    window_start = now - WINDOW

    # Prune old entries
    _requests[key] = [t for t in _requests[key] if t > window_start]

    if len(_requests[key]) >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Max {limit} requests per minute.",
        )

    _requests[key].append(now)


async def rate_limit_middleware(request: Request, limit: int = DEFAULT_LIMIT):
    """Use as a FastAPI dependency for rate limiting."""
    # Use IP + path as key
    client_ip = request.client.host if request.client else "unknown"
    key = f"{client_ip}:{request.url.path}"
    check_rate_limit(key, limit)
