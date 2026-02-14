"""User model with RBAC roles and subscription tiers."""

import uuid
from datetime import datetime, date, timezone

from sqlalchemy import String, Boolean, Integer, Float, Date, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    # ── RBAC ──────────────────────────────────────────────
    role: Mapped[str] = mapped_column(String(20), default="user")
    # Internal roles: superadmin, admin, support, marketing, finance, moderator, developer
    # External roles: user

    tier: Mapped[str] = mapped_column(String(20), default="free")
    # Tiers: free, standard, pro, business

    is_staff: Mapped[bool] = mapped_column(Boolean, default=False)
    department: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # Departments: support, marketing, finance, engineering, management

    # ── Status ────────────────────────────────────────────
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # ── Email verification ────────────────────────────────
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verification_token: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # ── Password reset ────────────────────────────────────
    password_reset_token: Mapped[str | None] = mapped_column(String(128), nullable=True)
    password_reset_expires: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # ── Consent / GDPR ────────────────────────────────────
    consent_given: Mapped[bool] = mapped_column(Boolean, default=False)
    consent_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # ── Usage tracking ────────────────────────────────────
    daily_prompt_count: Mapped[int] = mapped_column(Integer, default=0)
    prompt_reset_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # ── Billing / Credits ─────────────────────────────────
    credits_balance: Mapped[float] = mapped_column(Float, default=0.0)
    # Credits in USD; negative = overage, 0 = no credits, >0 = available
    total_tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    total_cost: Mapped[float] = mapped_column(Float, default=0.0)
    monthly_budget: Mapped[float] = mapped_column(Float, default=0.0)
    # 0 = no budget limit

    # ── Timestamps ────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    api_keys = relationship("ApiKey", back_populates="user", cascade="all, delete-orphan")
    feedbacks = relationship("Feedback", back_populates="user", cascade="all, delete-orphan")
    token_usages = relationship("TokenUsage", back_populates="user", cascade="all, delete-orphan")
