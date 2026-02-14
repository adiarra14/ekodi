"""Token usage tracking for GPT API billing."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Integer, Float, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TokenUsage(Base):
    """Tracks every GPT API call: tokens consumed, model used, cost."""

    __tablename__ = "token_usage"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    conversation_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True
    )

    # ── Model info ────────────────────────────────────────
    model: Mapped[str] = mapped_column(String(50), default="gpt-4o")
    endpoint: Mapped[str] = mapped_column(String(50), default="chat")
    # endpoint: "chat", "voice-chat", "whisper" etc.

    # ── Token counts ──────────────────────────────────────
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)

    # ── Cost (in USD) ─────────────────────────────────────
    prompt_cost: Mapped[float] = mapped_column(Float, default=0.0)
    completion_cost: Mapped[float] = mapped_column(Float, default=0.0)
    total_cost: Mapped[float] = mapped_column(Float, default=0.0)

    # ── Timestamps ────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    user = relationship("User", back_populates="token_usages")

    __table_args__ = (
        Index("ix_token_usage_user_created", "user_id", "created_at"),
        Index("ix_token_usage_created", "created_at"),
    )
