from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from litestar import Litestar
from litestar.contrib.jinja import JinjaTemplateEngine
from litestar.datastructures import State
from litestar.di import Provide
from litestar.middleware.session.client_side import CookieBackendConfig
from litestar.openapi.config import OpenAPIConfig
from litestar.openapi.spec import Contact
from litestar.static_files import create_static_files_router
from litestar.template.config import TemplateConfig
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from atem.application.services.auth_service import AuthService
from atem.application.services.contact_service import ContactService
from atem.application.services.content_service import ContentService
from atem.application.services.profile_service import ProfileService
from atem.application.services.theme_service import ThemeService
from atem.domain.interfaces.contact_repository import IContactRepository
from atem.domain.interfaces.content_repository import IContentRepository
from atem.domain.interfaces.email_service import IEmailService
from atem.domain.interfaces.password_hasher import IPasswordHasher
from atem.domain.interfaces.profile_repository import IProfileRepository
from atem.domain.interfaces.theme_repository import IThemeRepository
from atem.domain.interfaces.user_repository import IUserRepository
from atem.infrastructure.config.settings import Settings, get_settings
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
from atem.infrastructure.database.session import create_engine, create_session_factory
from atem.infrastructure.email.mock_email_service import MockEmailService
from atem.infrastructure.email.smtp_email_service import SmtpEmailService
from atem.infrastructure.logging.logger import get_logger, setup_logging
from atem.infrastructure.security.argon2_password_hasher import Argon2PasswordHasher
from atem.presentation.bootstrap import ensure_dev_admin, seed_content
from atem.presentation.controllers.admin_controller import AdminController
from atem.presentation.controllers.health_controller import HealthController
from atem.presentation.controllers.public_controller import PublicController

logger = get_logger(__name__)
BASE_DIR = Path(__file__).parent


# ------------------------------------------------------------------------------
# DEPENDENCY PROVIDERS
# ------------------------------------------------------------------------------
async def provide_db_session(state: State) -> AsyncGenerator[AsyncSession, None]:
    """Provide transactional async SQLAlchemy database session."""
    session_factory: async_sessionmaker[AsyncSession] = state.session_factory
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def provide_password_hasher() -> IPasswordHasher:
    """Provide password hasher instance."""
    return Argon2PasswordHasher()


async def provide_email_service(settings: Settings) -> IEmailService:
    """Provide email service based on configuration."""
    if settings.MAIL_ENABLED:
        return SmtpEmailService(settings=settings)
    return MockEmailService()


async def provide_profile_repository(db_session: AsyncSession) -> IProfileRepository:
    """Provide profile repository implementing IProfileRepository ABC."""
    return SqlAlchemyProfileRepository(session=db_session)


async def provide_contact_repository(db_session: AsyncSession) -> IContactRepository:
    """Provide contact repository implementing IContactRepository ABC."""
    return SqlAlchemyContactRepository(session=db_session)


async def provide_user_repository(db_session: AsyncSession) -> IUserRepository:
    """Provide user repository implementing IUserRepository ABC."""
    return SqlAlchemyUserRepository(session=db_session)


async def provide_theme_repository(db_session: AsyncSession) -> IThemeRepository:
    """Provide theme repository implementing IThemeRepository ABC."""
    return SqlAlchemyThemeRepository(session=db_session)


async def provide_content_repository(db_session: AsyncSession) -> IContentRepository:
    """Provide content repository implementing IContentRepository ABC."""
    return SqlAlchemyContentRepository(session=db_session)


async def provide_theme_service(theme_repository: IThemeRepository) -> ThemeService:
    """Provide ThemeService."""
    return ThemeService(theme_repository=theme_repository)


async def provide_content_service(content_repository: IContentRepository) -> ContentService:
    """Provide ContentService."""
    return ContentService(content_repository=content_repository)


async def provide_profile_service(profile_repository: IProfileRepository) -> ProfileService:
    """Provide ProfileService."""
    return ProfileService(profile_repository=profile_repository)


async def provide_contact_service(
    contact_repository: IContactRepository,
    email_service: IEmailService,
) -> ContactService:
    """Provide ContactService."""
    return ContactService(
        contact_repository=contact_repository,
        email_service=email_service,
    )


async def provide_auth_service(
    user_repository: IUserRepository,
    password_hasher: IPasswordHasher,
) -> AuthService:
    """Provide AuthService."""
    return AuthService(
        user_repository=user_repository,
        password_hasher=password_hasher,
    )


# ------------------------------------------------------------------------------
# LIFESPAN HOOKS
# ------------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: Litestar) -> AsyncGenerator[None, None]:
    """Application lifespan managing DB connection and initialization."""
    settings = get_settings()
    setup_logging(is_dev=settings.is_dev)
    logger.info("Starting Atemtherapie Application", environment=settings.ENVIRONMENT)

    # Initialize Async Engine and Sessionmaker if not already provided (e.g. in test fixture)
    if not hasattr(app.state, "engine") or app.state.engine is None:
        engine: AsyncEngine = create_engine()
        session_factory = create_session_factory(engine)
        app.state.engine = engine
        app.state.session_factory = session_factory
    else:
        engine = app.state.engine
        session_factory = app.state.session_factory

    # The schema is owned by Alembic (`alembic upgrade head`). In production the container
    # entrypoint migrates and seeds once before the workers start (see docker/entrypoint.sh).
    if not settings.is_production_like:
        await seed_content(session_factory)
        await ensure_dev_admin(session_factory, settings)

    yield

    logger.info("Shutting down Atemtherapie Application")
    await engine.dispose()


# ------------------------------------------------------------------------------
# APPLICATION FACTORY
# ------------------------------------------------------------------------------
def create_app() -> Litestar:
    """Build and configure the Litestar Application."""
    settings = get_settings()

    # Static Files Router (UI Theme, CSS, JS, Botanical Stock Assets)
    static_dir = BASE_DIR / "static"
    static_dir.mkdir(parents=True, exist_ok=True)
    static_router = create_static_files_router(
        path="/static",
        directories=[static_dir],
        name="static",
    )

    # Media Files Router (Persistent User Uploads, .gitignored, Docker Volume)
    media_dir = settings.media_storage_path
    media_dir.mkdir(parents=True, exist_ok=True)
    media_router = create_static_files_router(
        path="/media",
        directories=[media_dir],
        name="media",
    )

    # Template Engine
    templates_dir = BASE_DIR / "templates"
    templates_dir.mkdir(parents=True, exist_ok=True)
    template_config = TemplateConfig(
        directory=templates_dir,
        engine=JinjaTemplateEngine,
    )

    # Session Middleware (encrypted cookie, key derived from SECRET_KEY via HKDF)
    session_config = CookieBackendConfig(
        secret=settings.session_secret,
        key="atem_session",
        max_age=3600 * 24 * 7,  # 7 days
    )

    # OpenAPI Config
    openapi_config = OpenAPIConfig(
        title="PUSTERUM API",
        version="0.1.0",
        description="Clean Architecture API für PUSTERUM – Praxis für Atem- und Körpertherapie",
        contact=Contact(
            name="PUSTERUM", email="kontakt@pusterum.be", url="https://www.pusterum.be"
        ),
    )

    return Litestar(
        route_handlers=[
            HealthController,
            PublicController,
            AdminController,
            static_router,
            media_router,
        ],
        dependencies={
            "settings": Provide(get_settings, sync_to_thread=False),
            "db_session": Provide(provide_db_session),
            "password_hasher": Provide(provide_password_hasher, sync_to_thread=False),
            "email_service": Provide(provide_email_service),
            "theme_repository": Provide(provide_theme_repository),
            "theme_service": Provide(provide_theme_service),
            "content_repository": Provide(provide_content_repository),
            "content_service": Provide(provide_content_service),
            "profile_repository": Provide(provide_profile_repository),
            "contact_repository": Provide(provide_contact_repository),
            "user_repository": Provide(provide_user_repository),
            "profile_service": Provide(provide_profile_service),
            "contact_service": Provide(provide_contact_service),
            "auth_service": Provide(provide_auth_service),
        },
        template_config=template_config,
        middleware=[session_config.middleware],
        lifespan=[lifespan],
        openapi_config=openapi_config,
        debug=settings.DEBUG,
    )
