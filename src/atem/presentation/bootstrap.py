"""Composition-root helpers for one-off initialisation tasks.

Shared by the application lifespan (development/test) and the CLI (`python -m atem.cli`),
which the production container entrypoint runs once before the web workers start.
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from atem.application.services.auth_service import AuthService
from atem.application.services.content_service import ContentService
from atem.infrastructure.config.settings import Settings
from atem.infrastructure.database.repositories.sqlalchemy_content_repository import (
    SqlAlchemyContentRepository,
)
from atem.infrastructure.database.repositories.sqlalchemy_user_repository import (
    SqlAlchemyUserRepository,
)
from atem.infrastructure.logging.logger import get_logger
from atem.infrastructure.security.argon2_password_hasher import Argon2PasswordHasher

logger = get_logger(__name__)


async def seed_content(session_factory: async_sessionmaker[AsyncSession]) -> int:
    """Insert missing default content blocks (idempotent)."""
    async with session_factory() as session:
        service = ContentService(SqlAlchemyContentRepository(session))
        inserted = await service.seed_defaults()
        await session.commit()
    return inserted


def build_auth_service(session: AsyncSession) -> AuthService:
    """Create an AuthService bound to the given session."""
    return AuthService(SqlAlchemyUserRepository(session), Argon2PasswordHasher())


async def ensure_dev_admin(
    session_factory: async_sessionmaker[AsyncSession], settings: Settings
) -> None:
    """Seed the local admin account in development/test (never in production)."""
    if settings.is_production_like:
        return
    if not settings.ADMIN_INITIAL_PASSWORD:
        logger.warning(
            "dev_admin_not_seeded",
            reason="ADMIN_INITIAL_PASSWORD fehlt – `python -m atem.cli create-admin` nutzen",
        )
        return
    async with session_factory() as session:
        await build_auth_service(session).ensure_initial_admin(
            username=settings.ADMIN_USERNAME,
            email=settings.ADMIN_EMAIL,
            initial_password=settings.ADMIN_INITIAL_PASSWORD,
        )
        await session.commit()
