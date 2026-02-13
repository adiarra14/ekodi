"""API Key model."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(12), nullable=False)  # e.g. "ek-abc123..."
    name: Mapped[str] = mapped_column(String(255), default="Default")
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    rate_limit: Mapped[int] = mapped_column(Integer, default=100)  # requests per minute
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    user = relationship("User", back_populates="api_keys")
