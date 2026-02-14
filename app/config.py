"""
Ekodi – Application configuration from environment variables.
"""

import os
from pathlib import Path
from functools import lru_cache

from pydantic import BaseModel


class Settings(BaseModel):
    """Application settings loaded from environment."""

    # App
    APP_NAME: str = "Ekodi"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    SECRET_KEY: str = "change-me-in-production-ekodi-2024"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./ekodi.db"

    # Redis (optional, for rate limiting)
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    JWT_SECRET: str = "ekodi-jwt-secret-change-me"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60  # 1 hour for access token

    # OpenAI
    OPENAI_API_KEY: str = ""

    # HuggingFace
    HF_TOKEN: str = ""

    # TTS config path
    TTS_CONFIG_PATH: str = str(
        Path(__file__).resolve().parent.parent / "tts" / "config" / "tts-port.yml"
    )

    # Server
    CORS_ORIGINS: list[str] = ["*"]

    # SMTP (email)
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "ekodi.ai <noreply@ekodi.ai>"

    # Base URL for email links
    BASE_URL: str = "https://ekodi.ai"

    # Data retention
    DATA_RETENTION_DAYS: int = 365


def _load_dotenv():
    """Load .env file from tts/ directory (legacy) and project root."""
    for env_path in [
        Path(__file__).resolve().parent.parent / ".env",
        Path(__file__).resolve().parent.parent / "tts" / ".env",
    ]:
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ.setdefault(key.strip(), val.strip())


_load_dotenv()


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance, populated from env vars."""
    return Settings(
        DEBUG=os.getenv("DEBUG", "false").lower() in ("1", "true", "yes"),
        SECRET_KEY=os.getenv("SECRET_KEY", Settings().SECRET_KEY),
        DATABASE_URL=os.getenv("DATABASE_URL", Settings().DATABASE_URL),
        REDIS_URL=os.getenv("REDIS_URL", Settings().REDIS_URL),
        JWT_SECRET=os.getenv("JWT_SECRET", Settings().JWT_SECRET),
        OPENAI_API_KEY=os.getenv("OPENAI_API_KEY", ""),
        HF_TOKEN=os.getenv("HF_TOKEN", ""),
        SMTP_HOST=os.getenv("SMTP_HOST", Settings().SMTP_HOST),
        SMTP_PORT=int(os.getenv("SMTP_PORT", str(Settings().SMTP_PORT))),
        SMTP_USER=os.getenv("SMTP_USER", ""),
        SMTP_PASSWORD=os.getenv("SMTP_PASSWORD", ""),
        SMTP_FROM=os.getenv("SMTP_FROM", Settings().SMTP_FROM),
        BASE_URL=os.getenv("BASE_URL", Settings().BASE_URL),
        DATA_RETENTION_DAYS=int(os.getenv("DATA_RETENTION_DAYS", str(Settings().DATA_RETENTION_DAYS))),
    )
