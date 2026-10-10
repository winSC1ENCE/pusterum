"""Database Connection and Async Session Factory."""

from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from atem.infrastructure.config.settings import get_settings


def create_engine() -> AsyncEngine:
    """Create async SQLAlchemy engine."""
    settings = get_settings()
    kwargs: dict[str, Any] = {"echo": settings.DB_ECHO, "future": True}
    if not settings.DATABASE_URL.startswith("sqlite"):
        kwargs["pool_size"] = settings.DB_POOL_SIZE
        kwargs["max_overflow"] = settings.DB_MAX_OVERFLOW

    return create_async_engine(settings.DATABASE_URL, **kwargs)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Create async session maker bound to engine."""
    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )
