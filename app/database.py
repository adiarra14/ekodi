"""
Ekodi – Database setup (async SQLAlchemy).
Uses SQLite for local dev, PostgreSQL in production.
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    """FastAPI dependency: yields an async DB session."""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db():
    """Create all tables (for development). Use Alembic in production."""
    async with engine.begin() as conn:
        from app.models import user, conversation, api_key, feedback, token_usage, platform_setting  # noqa: F401
        await conn.run_sync(Base.metadata.create_all)
