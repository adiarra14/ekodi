"""
Ekodi – JWT authentication middleware and helpers.
Supports access tokens, refresh tokens, token blacklisting,
per-user force-logout, and session tracking.

Token durations:
  - Staff: 24h access, 30d refresh
  - Regular users: 1h access, 7d refresh
"""

import hashlib
import secrets
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models.user import User
from app.models.api_key import ApiKey

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer(auto_error=False)

# ── In-memory stores (use Redis in production) ────────────────
_token_blacklist: set[str] = set()

# Per-user invalidation: tokens issued before this timestamp are rejected
# { user_id: timestamp }
_user_invalidated_before: dict[str, float] = {}

# Active session tracking: { user_id: set of (token_jti) }
_active_sessions: dict[str, set[str]] = defaultdict(set)

STAFF_ROLES = {"superadmin", "admin", "support", "marketing", "finance", "moderator", "developer"}

# ── Token durations ───────────────────────────────────────────
STAFF_ACCESS_HOURS = 24
STAFF_REFRESH_DAYS = 30
USER_ACCESS_HOURS = 1
USER_REFRESH_DAYS = 7


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(user_id: str, role: str = "user") -> str:
    settings = get_settings()
    is_staff = role in STAFF_ROLES
    hours = STAFF_ACCESS_HOURS if is_staff else USER_ACCESS_HOURS
    expire = datetime.now(timezone.utc) + timedelta(hours=hours)
    jti = secrets.token_hex(16)
    payload = {
        "sub": user_id,
        "role": role,
        "type": "access",
        "jti": jti,
        "iat": datetime.now(timezone.utc).timestamp(),
        "exp": expire,
    }
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

    # Track session
    _active_sessions[user_id].add(jti)

    return token


def create_refresh_token(user_id: str, is_staff: bool = False) -> str:
    settings = get_settings()
    days = STAFF_REFRESH_DAYS if is_staff else USER_REFRESH_DAYS
    expire = datetime.now(timezone.utc) + timedelta(days=days)
    jti = secrets.token_hex(16)
    payload = {
        "sub": user_id,
        "type": "refresh",
        "jti": jti,
        "iat": datetime.now(timezone.utc).timestamp(),
        "exp": expire,
    }
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

    _active_sessions[user_id].add(jti)

    return token


def decode_token(token: str) -> dict:
    settings = get_settings()
    if token in _token_blacklist:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token revoked")
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    # Check per-user invalidation
    user_id = payload.get("sub")
    iat = payload.get("iat", 0)
    if user_id and user_id in _user_invalidated_before:
        if iat < _user_invalidated_before[user_id]:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired, please login again")

    return payload


def blacklist_token(token: str):
    """Add a token to the blacklist."""
    _token_blacklist.add(token)
    # Also remove from session tracking
    try:
        settings = get_settings()
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM],
                             options={"verify_exp": False})
        user_id = payload.get("sub")
        jti = payload.get("jti")
        if user_id and jti and jti in _active_sessions.get(user_id, set()):
            _active_sessions[user_id].discard(jti)
    except Exception:
        pass


def force_logout_user(user_id: str):
    """Invalidate ALL tokens for a user (force-logout)."""
    _user_invalidated_before[user_id] = time.time()
    _active_sessions[user_id] = set()


def get_active_session_count(user_id: str) -> int:
    """Get number of active sessions for a user."""
    return len(_active_sessions.get(user_id, set()))


def get_all_session_counts() -> dict[str, int]:
    """Get session counts for all users with active sessions."""
    return {uid: len(jtis) for uid, jtis in _active_sessions.items() if jtis}


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extract and validate JWT from Bearer token."""
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    payload = decode_token(credentials.credentials)
    if payload.get("type") == "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token cannot be used for API access")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """Same as get_current_user but returns None instead of raising."""
    if not credentials:
        return None
    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None


async def get_admin_user(user: User = Depends(get_current_user)) -> User:
    """Require staff role (any staff role is admin-level for backward compat)."""
    if user.role not in STAFF_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Staff access required")
    return user


# ── API Key auth ──────────────────────────────────────────────

def generate_api_key() -> tuple[str, str]:
    """Generate a new API key. Returns (raw_key, key_hash)."""
    raw_key = "ek-" + secrets.token_urlsafe(32)
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    return raw_key, key_hash


async def get_api_key_user(request: Request, db: AsyncSession = Depends(get_db)) -> User:
    """Authenticate via X-API-Key header."""
    api_key = request.headers.get("X-API-Key", "")
    if not api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API key required")

    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    result = await db.execute(
        select(ApiKey).where(ApiKey.key_hash == key_hash, ApiKey.active == True)
    )
    ak = result.scalar_one_or_none()
    if not ak:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

    # Increment usage
    ak.usage_count += 1
    await db.flush()

    # Get the user
    result = await db.execute(select(User).where(User.id == ak.user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user
