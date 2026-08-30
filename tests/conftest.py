"""Pytest Configuration and Test Fixtures."""

import os
from collections.abc import AsyncGenerator

import pytest
from litestar import Litestar
from litestar.testing import AsyncTestClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# Set test environment
os.environ["ENVIRONMENT"] = "test"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret-key-at-least-32-chars-long-12345"

from atem.application.services.auth_service import AuthService
from atem.application.services.contact_service import ContactService
from atem.application.services.content_service import ContentService
from atem.application.services.profile_service import ProfileService
from atem.application.services.theme_service import ThemeService
from atem.domain.interfaces.email_service import IEmailService
from atem.domain.interfaces.password_hasher import IPasswordHasher
from atem.infrastructure.database.base import Base
from atem.infrastructure.database.repositories.sqlalchemy_contact_repository import (
    SqlAlchemyContactRepository,
)
from atem.infrastructure.database.repositories.sqlalchemy_content_repository import (
    SqlAlchemyContentRepository,
)
from atem.infrastructure.database.repositories.sqlalchemy_profile_repository import (
    SqlAlchemyProfileRepository,
)
from atem.infrastructure.database.repositories.sqlalchemy_theme_repository import (
    SqlAlchemyThemeRepository,
)
from atem.infrastructure.database.repositories.sqlalchemy_user_repository import (
    SqlAlchemyUserRepository,
)
from atem.infrastructure.email.mock_email_service import MockEmailService
from atem.infrastructure.security.argon2_password_hasher import Argon2PasswordHasher
from atem.presentation.app import create_app


@pytest.fixture
def password_hasher() -> IPasswordHasher:
    """Fixture providing Argon2 password hasher."""
    return Argon2PasswordHasher()


@pytest.fixture
def email_service() -> IEmailService:
    """Fixture providing Mock email service."""
    return MockEmailService()


@pytest.fixture
async def async_engine() -> AsyncGenerator[AsyncEngine, None]:
    """In-memory SQLite async engine for fast tests."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(async_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Async database session fixture."""
    session_maker = async_sessionmaker(async_engine, expire_on_commit=False)
    async with session_maker() as session:
        yield session
        await session.rollback()


@pytest.fixture
def profile_service(db_session: AsyncSession) -> ProfileService:
    """Profile service fixture."""
    repo = SqlAlchemyProfileRepository(db_session)
    return ProfileService(repo)


@pytest.fixture
def content_service(db_session: AsyncSession) -> ContentService:
    """Content service fixture."""
    repo = SqlAlchemyContentRepository(db_session)
    return ContentService(repo)


@pytest.fixture
def contact_service(db_session: AsyncSession, email_service: IEmailService) -> ContactService:
    """Contact service fixture."""
    repo = SqlAlchemyContactRepository(db_session)
    return ContactService(repo, email_service)


@pytest.fixture
def theme_service(db_session: AsyncSession) -> ThemeService:
    """Theme service fixture."""
    repo = SqlAlchemyThemeRepository(db_session)
    return ThemeService(repo)


@pytest.fixture
def auth_service(db_session: AsyncSession, password_hasher: IPasswordHasher) -> AuthService:
    """Auth service fixture."""
    repo = SqlAlchemyUserRepository(db_session)
    return AuthService(repo, password_hasher)


@pytest.fixture
async def app_client(
    async_engine: AsyncEngine,
    email_service: IEmailService,
    password_hasher: IPasswordHasher,
) -> AsyncGenerator[AsyncTestClient[Litestar], None]:
    """TestClient fixture for testing Litestar endpoints."""
    app = create_app()
    session_maker = async_sessionmaker(async_engine, expire_on_commit=False)
    app.state.session_factory = session_maker
    app.state.engine = async_engine

    async with AsyncTestClient(app=app) as client:
        yield client
