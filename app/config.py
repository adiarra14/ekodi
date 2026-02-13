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
    JWT_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # OpenAI
    OPENAI_API_KEY: str = ""

    # HuggingFace
    HF_TOKEN: str = ""

    # TTS config path
    TTS_CONFIG_PATH: str = str(
        Path(__file__).resolve().parent.parent / "tts" / "config" / "ekodi-port.yml"
    )

    # Server
    CORS_ORIGINS: list[str] = ["*"]


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
    )
