"""Pytest Configuration and Test Fixtures."""

import base64
import io
import json
import os
import re
from collections.abc import AsyncGenerator
from typing import Any

import pytest
from altcha.v1 import solve_challenge
from litestar import Litestar
from litestar.testing import AsyncTestClient
from PIL import Image
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

# Set test environment
os.environ["ENVIRONMENT"] = "test"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret-key-at-least-32-chars-long-12345"
os.environ["ADMIN_INITIAL_PASSWORD"] = "admin-secure-init-pass-change-me"
os.environ["ALLOWED_HOSTS"] = '["testserver.local", "localhost"]'
os.environ["CONTACT_FORM_MIN_SECONDS"] = "0"
os.environ["ALTCHA_MAX_NUMBER"] = "2000"  # cheap proof-of-work in tests

from atem.application.services.auth_service import AuthService
from atem.application.services.contact_service import ContactService
from atem.application.services.content_service import ContentService
from atem.application.services.offering_service import OfferingService
from atem.application.services.theme_service import ThemeService
from atem.domain.interfaces.email_service import IEmailService
from atem.domain.interfaces.password_hasher import IPasswordHasher
from atem.infrastructure.config.settings import get_settings
from atem.infrastructure.database.base import Base
from atem.infrastructure.database.repositories.sqlalchemy_contact_repository import (
    SqlAlchemyContactRepository,
)
from atem.infrastructure.database.repositories.sqlalchemy_content_repository import (
    SqlAlchemyContentRepository,
)
from atem.infrastructure.database.repositories.sqlalchemy_offering_repository import (
    SqlAlchemyOfferingRepository,
)
from atem.infrastructure.database.repositories.sqlalchemy_theme_repository import (
    SqlAlchemyThemeRepository,
)
from atem.infrastructure.database.repositories.sqlalchemy_user_repository import (
    SqlAlchemyUserRepository,
)
from atem.infrastructure.email.mock_email_service import MockEmailService
from atem.infrastructure.security.argon2_password_hasher import Argon2PasswordHasher
from atem.infrastructure.security.pyotp_totp_provider import PyotpTotpProvider
from atem.presentation.app import create_app
from atem.presentation.bootstrap import build_contact_service, build_secret_cipher


def make_image_bytes(image_format: str = "PNG", size: tuple[int, int] = (8, 8)) -> bytes:
    """Create a real, decodable image for upload tests."""
    buffer = io.BytesIO()
    Image.new("RGB", size, (74, 108, 80)).save(buffer, image_format)
    return buffer.getvalue()


@pytest.fixture
def sample_png() -> bytes:
    """A valid 8×8 PNG."""
    return make_image_bytes("PNG")


@pytest.fixture
def password_hasher() -> IPasswordHasher:
    """Fixture providing Argon2 password hasher."""
    return Argon2PasswordHasher()


@pytest.fixture
def email_service() -> IEmailService:
    """Fixture providing Mock email service."""
    return MockEmailService()


# Fast in-memory SQLite by default; CI also runs the suite against PostgreSQL by setting
# TEST_DATABASE_URL (e.g. postgresql+asyncpg://…/atem_test).
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "sqlite+aiosqlite:///:memory:")


@pytest.fixture
async def async_engine() -> AsyncGenerator[AsyncEngine, None]:
    """Async engine with a fresh schema per test."""
    # The Litestar test client runs the app in its own event loop – pooled asyncpg
    # connections cannot be shared across loops, hence NullPool for PostgreSQL.
    pool = {} if TEST_DATABASE_URL.startswith("sqlite") else {"poolclass": NullPool}
    engine = create_async_engine(TEST_DATABASE_URL, echo=False, **pool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def db_session(async_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Async database session fixture."""
    session_maker = async_sessionmaker(async_engine, expire_on_commit=False)
    async with session_maker() as session:
        yield session
        await session.rollback()


@pytest.fixture
def offering_service(db_session: AsyncSession) -> OfferingService:
    """Offering service fixture."""
    return OfferingService(SqlAlchemyOfferingRepository(db_session))


@pytest.fixture
async def content_service(db_session: AsyncSession) -> ContentService:
    """Content service fixture with seeded default content."""
    service = ContentService(SqlAlchemyContentRepository(db_session))
    await service.seed_defaults()
    return service


@pytest.fixture
def contact_service(db_session: AsyncSession, email_service: IEmailService) -> ContactService:
    """Contact service fixture with the real ALTCHA captcha."""
    return build_contact_service(
        SqlAlchemyContactRepository(db_session), email_service, get_settings()
    )


async def contact_form_payload(client: AsyncTestClient[Litestar], **fields: str) -> dict[str, str]:
    """Build a contact submission like a browser: timing token from the page + solved captcha."""
    page = await client.get("/")
    match = re.search(r'name="form_token" value="([^"]+)"', page.text)
    assert match, "form token missing"
    challenge = (await client.get("/altcha/challenge")).json()
    return {"form_token": match.group(1), "altcha": solve_altcha(challenge), **fields}


def solve_altcha(challenge: dict[str, Any]) -> str:
    """Solve an ALTCHA challenge like the browser widget and return the form payload."""
    solution = solve_challenge(
        challenge["challenge"],
        challenge["salt"],
        challenge["algorithm"],
        challenge["maxNumber"],
    )
    assert solution is not None
    payload = {
        "algorithm": challenge["algorithm"],
        "challenge": challenge["challenge"],
        "number": solution.number,
        "salt": challenge["salt"],
        "signature": challenge["signature"],
    }
    return base64.b64encode(json.dumps(payload).encode()).decode()


@pytest.fixture
def theme_service(db_session: AsyncSession) -> ThemeService:
    """Theme service fixture."""
    repo = SqlAlchemyThemeRepository(db_session)
    return ThemeService(repo)


@pytest.fixture
def auth_service(db_session: AsyncSession, password_hasher: IPasswordHasher) -> AuthService:
    """Auth service fixture (real Fernet cipher + TOTP provider)."""
    return AuthService(
        SqlAlchemyUserRepository(db_session),
        password_hasher,
        build_secret_cipher(get_settings()),
        PyotpTotpProvider(),
    )


async def refresh_csrf(client: AsyncTestClient[Litestar]) -> None:
    """Obtain a CSRF cookie via a safe request and send it as header on all later requests."""
    await client.get("/")
    token = client.cookies.get("csrftoken")
    if token:
        client.headers["x-csrftoken"] = token


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
        await refresh_csrf(client)
        yield client
