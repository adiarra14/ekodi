"""
Ekodi – Authentication routes.
register, login, me, verify email, forgot/reset password,
token refresh, logout, account deletion, data export.
"""

import os
import secrets
import json
import io
import zipfile
import httpx
from datetime import datetime, timedelta, timezone

from pydantic import BaseModel, EmailStr, Field
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.conversation import Conversation, Message
from app.models.api_key import ApiKey
from app.models.feedback import Feedback
from app.models.token_usage import TokenUsage
from app.middleware.auth import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    blacklist_token,
    get_current_user,
    security,
)
from app.middleware.rate_limit import check_login_rate
from app.services.email import (
    send_verification_email,
    send_password_reset_email,
    send_account_deleted_email,
)

router = APIRouter(prefix="/auth", tags=["auth"])


# ── Request / Response models ─────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    name: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=6, max_length=100)
    consent: bool = False
    captcha_token: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    token: str
    refresh_token: str
    user: dict


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    role: str
    tier: str
    is_staff: bool
    email_verified: bool
    consent_given: bool
    created_at: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=6, max_length=100)


class DeleteAccountRequest(BaseModel):
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


# ── Helpers ───────────────────────────────────────────────────

def _user_dict(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "tier": user.tier or "free",
        "is_staff": user.is_staff,
        "email_verified": user.email_verified,
        "consent_given": user.consent_given,
        "created_at": user.created_at.isoformat(),
    }


# ── Public Config (serves reCAPTCHA site key, etc.) ──────────

@router.get("/public-config")
async def public_config():
    """Return public client-side configuration (no auth required)."""
    return {
        "recaptcha_site_key": os.getenv("RECAPTCHA_SITE_KEY", ""),
    }


# ── Register ──────────────────────────────────────────────────

async def _verify_captcha(token: str | None):
    """Verify reCAPTCHA token with Google. Skip if secret key not configured."""
    secret = os.getenv("RECAPTCHA_SECRET_KEY", "")
    if not secret:
        return  # CAPTCHA not configured, skip
    if not token:
        raise HTTPException(400, "CAPTCHA verification required")
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://www.google.com/recaptcha/api/siteverify",
                data={"secret": secret, "response": token},
            )
            data = resp.json()
            if not data.get("success"):
                raise HTTPException(400, "CAPTCHA verification failed. Please try again.")
    except HTTPException:
        raise
    except Exception:
        pass  # If Google is unreachable, don't block registration


@router.post("/register", response_model=AuthResponse)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Create a new user account."""
    # Verify CAPTCHA
    await _verify_captcha(req.captcha_token)

    result = await db.execute(select(User).where(User.email == req.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
        )

    verification_token = secrets.token_urlsafe(48)

    user = User(
        email=req.email,
        name=req.name,
        password_hash=hash_password(req.password),
        role="user",
        tier="free",
        verification_token=verification_token,
        consent_given=bool(req.consent),
        consent_date=datetime.now(timezone.utc) if req.consent else None,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)

    # Send verification email (non-blocking, logged on failure)
    send_verification_email(user.email, user.name, verification_token)

    token = create_access_token(user.id, user.role)
    refresh = create_refresh_token(user.id, is_staff=user.is_staff)
    return AuthResponse(
        token=token,
        refresh_token=refresh,
        user=_user_dict(user),
    )


# ── Email Verification ───────────────────────────────────────

@router.get("/verify/{token}")
async def verify_email(token: str, db: AsyncSession = Depends(get_db)):
    """Verify email address via token."""
    result = await db.execute(
        select(User).where(User.verification_token == token)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired verification link")

    user.email_verified = True
    user.verification_token = None
    await db.flush()
    return {"verified": True, "email": user.email}


@router.post("/resend-verification")
async def resend_verification(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Resend verification email."""
    if user.email_verified:
        return {"message": "Email already verified"}

    token = secrets.token_urlsafe(48)
    user.verification_token = token
    await db.flush()
    send_verification_email(user.email, user.name, token)
    return {"message": "Verification email sent"}


# ── Login ─────────────────────────────────────────────────────

@router.post("/login", response_model=AuthResponse)
async def login(req: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """Login with email and password."""
    # Brute force protection
    client_ip = request.client.host if request.client else "unknown"
    check_login_rate(client_ip)

    result = await db.execute(select(User).where(User.email == req.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Contact support.",
        )

    # Update last login
    user.last_login = datetime.now(timezone.utc)
    await db.flush()

    token = create_access_token(user.id, user.role)
    refresh = create_refresh_token(user.id, is_staff=user.is_staff)
    return AuthResponse(
        token=token,
        refresh_token=refresh,
        user=_user_dict(user),
    )


# ── Token Refresh ─────────────────────────────────────────────

@router.post("/refresh")
async def refresh_token(req: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """Refresh access token using refresh token."""
    payload = decode_token(req.refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Not a refresh token")

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")

    new_access = create_access_token(user.id, user.role)
    new_refresh = create_refresh_token(user.id, is_staff=user.is_staff)

    # Blacklist old refresh token
    blacklist_token(req.refresh_token)

    return {"token": new_access, "refresh_token": new_refresh, "user": _user_dict(user)}


# ── Logout ────────────────────────────────────────────────────

@router.post("/logout")
async def logout(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
):
    """Logout (blacklist current token)."""
    if credentials:
        blacklist_token(credentials.credentials)
    return {"message": "Logged out"}


# ── Me ────────────────────────────────────────────────────────

@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)):
    """Get current user profile."""
    return UserResponse(**{
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "tier": user.tier or "free",
        "is_staff": user.is_staff,
        "email_verified": user.email_verified,
        "consent_given": user.consent_given,
        "created_at": user.created_at.isoformat(),
    })


@router.get("/me/usage")
async def my_usage(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current user's token usage summary."""
    from sqlalchemy import func

    total_requests = (await db.execute(
        select(func.count(TokenUsage.id)).where(TokenUsage.user_id == user.id)
    )).scalar() or 0

    month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_tokens = (await db.execute(
        select(func.sum(TokenUsage.total_tokens)).where(
            TokenUsage.user_id == user.id,
            TokenUsage.created_at >= month_start,
        )
    )).scalar() or 0
    month_cost = (await db.execute(
        select(func.sum(TokenUsage.total_cost)).where(
            TokenUsage.user_id == user.id,
            TokenUsage.created_at >= month_start,
        )
    )).scalar() or 0

    return {
        "total_tokens_used": user.total_tokens_used or 0,
        "total_cost": round(user.total_cost or 0, 6),
        "credits_balance": round(user.credits_balance or 0, 4),
        "monthly_budget": round(user.monthly_budget or 0, 2),
        "total_requests": total_requests,
        "this_month": {
            "tokens": month_tokens,
            "cost": round(month_cost, 6),
        },
    }


# ── Forgot Password ──────────────────────────────────────────

@router.post("/forgot-password")
async def forgot_password(req: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    """Send password reset email."""
    result = await db.execute(select(User).where(User.email == req.email))
    user = result.scalar_one_or_none()

    # Always return success (don't reveal if email exists)
    if user:
        token = secrets.token_urlsafe(48)
        user.password_reset_token = token
        user.password_reset_expires = datetime.now(timezone.utc) + timedelta(hours=1)
        await db.flush()
        send_password_reset_email(user.email, user.name, token)

    return {"message": "If an account exists with that email, a reset link has been sent."}


@router.post("/reset-password")
async def reset_password(req: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    """Reset password via token."""
    result = await db.execute(
        select(User).where(User.password_reset_token == req.token)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired reset link")

    if user.password_reset_expires and user.password_reset_expires < datetime.now(timezone.utc):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Reset link expired")

    user.password_hash = hash_password(req.new_password)
    user.password_reset_token = None
    user.password_reset_expires = None
    await db.flush()
    return {"message": "Password reset successful. You can now login."}


# ── Account Self-Deletion ────────────────────────────────────

@router.delete("/account")
async def delete_account(
    req: DeleteAccountRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete current user's account and all associated data."""
    if not verify_password(req.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect password")

    email = user.email
    name = user.name

    await db.delete(user)
    await db.flush()

    send_account_deleted_email(email, name)
    return {"deleted": True, "message": "Account and all data have been permanently deleted."}


# ── Data Export ───────────────────────────────────────────────

@router.get("/export")
async def export_data(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export all user data as a JSON ZIP file."""
    # Profile
    profile = _user_dict(user)

    # Conversations + messages
    result = await db.execute(
        select(Conversation).where(Conversation.user_id == user.id).order_by(Conversation.created_at)
    )
    convos = result.scalars().all()
    conversations_data = []
    for c in convos:
        msgs_result = await db.execute(
            select(Message).where(Message.conversation_id == c.id).order_by(Message.created_at)
        )
        msgs = msgs_result.scalars().all()
        conversations_data.append({
            "id": c.id,
            "title": c.title,
            "created_at": c.created_at.isoformat(),
            "messages": [
                {
                    "role": m.role,
                    "text_fr": m.text_fr,
                    "text_bm": m.text_bm,
                    "created_at": m.created_at.isoformat(),
                }
                for m in msgs
            ],
        })

    # API keys (prefix only)
    result = await db.execute(
        select(ApiKey).where(ApiKey.user_id == user.id)
    )
    keys = result.scalars().all()
    api_keys_data = [
        {"name": k.name, "key_prefix": k.key_prefix, "active": k.active, "created_at": k.created_at.isoformat()}
        for k in keys
    ]

    # Feedback
    result = await db.execute(
        select(Feedback).where(Feedback.user_id == user.id)
    )
    fbs = result.scalars().all()
    feedback_data = [
        {"rating": f.rating, "comment": f.comment, "created_at": f.created_at.isoformat()}
        for f in fbs
    ]

    export = {
        "profile": profile,
        "conversations": conversations_data,
        "api_keys": api_keys_data,
        "feedback": feedback_data,
        "exported_at": datetime.now(timezone.utc).isoformat(),
    }

    # Create ZIP
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("ekodi-export.json", json.dumps(export, indent=2, ensure_ascii=False))
    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=ekodi-data-export.zip"},
    )


# ── Delete All Conversations ─────────────────────────────────

@router.delete("/conversations/all")
async def delete_all_conversations(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete all conversations for the current user."""
    result = await db.execute(
        select(Conversation).where(Conversation.user_id == user.id)
    )
    convos = result.scalars().all()
    count = len(convos)
    for c in convos:
        await db.delete(c)
    await db.flush()
    return {"deleted": count, "message": f"{count} conversations deleted."}
