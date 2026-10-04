"""Litestar application factory: dependency injection, middleware, security and lifespan."""

import asyncio
import contextlib
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import structlog
from litestar import Litestar, Request
from litestar.config.csrf import CSRFConfig
from litestar.contrib.jinja import JinjaTemplateEngine
from litestar.datastructures import State
from litestar.di import Provide
from litestar.exceptions import NotAuthorizedException
from litestar.middleware import DefineMiddleware
from litestar.middleware.rate_limit import RateLimitConfig
from litestar.middleware.session.client_side import CookieBackendConfig
from litestar.openapi.config import OpenAPIConfig
from litestar.openapi.spec import Contact
from litestar.static_files import create_static_files_router
from litestar.template.config import TemplateConfig
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from atem.application.services.auth_service import AuthService
from atem.application.services.contact_service import ContactService
from atem.application.services.content_service import ContentService
from atem.application.services.media_service import MediaService
from atem.application.services.offering_service import OfferingService
from atem.application.services.theme_service import ThemeService
from atem.domain.interfaces.contact_repository import IContactRepository
from atem.domain.interfaces.content_repository import IContentRepository
from atem.domain.interfaces.email_service import IEmailService
from atem.domain.interfaces.offering_repository import IOfferingRepository
from atem.domain.interfaces.password_hasher import IPasswordHasher
from atem.domain.interfaces.theme_repository import IThemeRepository
from atem.domain.interfaces.user_repository import IUserRepository
from atem.infrastructure.config.settings import Settings, get_settings
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
from atem.infrastructure.database.session import create_engine, create_session_factory
from atem.infrastructure.email.mock_email_service import MockEmailService
from atem.infrastructure.email.smtp_email_service import SmtpEmailService
from atem.infrastructure.logging.logger import setup_logging
from atem.infrastructure.media.pillow_image_sanitizer import PillowImageSanitizer
from atem.infrastructure.security.argon2_password_hasher import Argon2PasswordHasher
from atem.infrastructure.security.pyotp_totp_provider import PyotpTotpProvider
from atem.presentation.bootstrap import (
    build_contact_service,
    build_secret_cipher,
    ensure_dev_admin,
    purge_expired_data,
    seed_content,
)
from atem.presentation.controllers.admin import ADMIN_CONTROLLERS
from atem.presentation.controllers.health_controller import HealthController
from atem.presentation.controllers.public_controller import PublicController
from atem.presentation.errors import EXCEPTION_HANDLERS
from atem.presentation.security.admin_auth import unauthorized_handler
from atem.presentation.security.host_validation import HostValidationMiddleware
from atem.presentation.security.proxy_headers import ProxyHeadersMiddleware
from atem.presentation.security.security_headers import SecurityHeadersMiddleware
from atem.presentation.templating import configure_jinja

logger = structlog.get_logger(__name__)
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


async def provide_offering_repository(db_session: AsyncSession) -> IOfferingRepository:
    """Provide the offering repository (IOfferingRepository)."""
    return SqlAlchemyOfferingRepository(session=db_session)


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


async def provide_offering_service(offering_repository: IOfferingRepository) -> OfferingService:
    """Provide OfferingService."""
    return OfferingService(repository=offering_repository)


async def provide_contact_service(
    contact_repository: IContactRepository,
    email_service: IEmailService,
    settings: Settings,
) -> ContactService:
    """Provide ContactService with ALTCHA captcha and configured abuse limits."""
    return build_contact_service(contact_repository, email_service, settings)


async def provide_media_service(settings: Settings) -> MediaService:
    """Provide MediaService (uploads into the persistent media volume)."""
    return MediaService(
        sanitizer=PillowImageSanitizer(),
        media_dir=settings.media_storage_path,
        static_images_dir=BASE_DIR / "static" / "images",
    )


async def provide_auth_service(
    user_repository: IUserRepository,
    password_hasher: IPasswordHasher,
    email_service: IEmailService,
    settings: Settings,
) -> AuthService:
    """Provide AuthService (TOTP seeds encrypted with a key derived from SECRET_KEY)."""
    return AuthService(
        user_repository=user_repository,
        password_hasher=password_hasher,
        secret_cipher=build_secret_cipher(settings),
        totp_provider=PyotpTotpProvider(),
        email_service=email_service,
    )


# ------------------------------------------------------------------------------
# LIFESPAN HOOKS
# ------------------------------------------------------------------------------
RETENTION_INTERVAL_SECONDS = 24 * 60 * 60
RETENTION_FIRST_RUN_DELAY_SECONDS = 60


async def _retention_loop(
    session_factory: async_sessionmaker[AsyncSession], settings: Settings
) -> None:
    """Daily data-retention job (idempotent – safe to run in every worker)."""
    await asyncio.sleep(RETENTION_FIRST_RUN_DELAY_SECONDS)
    while True:
        try:
            await purge_expired_data(session_factory, settings)
        except Exception:
            logger.exception("retention_job_failed")
        await asyncio.sleep(RETENTION_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(app: Litestar) -> AsyncGenerator[None, None]:
    """Application lifespan managing DB connection and initialization."""
    settings = get_settings()
    setup_logging(is_dev=settings.is_dev)
    logger.info("Starting PUSTERUM application", environment=settings.ENVIRONMENT)

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

    retention_task = (
        None
        if settings.ENVIRONMENT == "test"
        else asyncio.create_task(_retention_loop(session_factory, settings))
    )

    yield

    if retention_task is not None:
        retention_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await retention_task

    logger.info("Shutting down Atemtherapie Application")
    await engine.dispose()


# ------------------------------------------------------------------------------
# APPLICATION FACTORY
# ------------------------------------------------------------------------------
SENSITIVE_POST_PATHS = frozenset({"/admin/login", "/admin/login/verify", "/contact"})


def _is_sensitive_post(request: Request[Any, Any, Any]) -> bool:
    """Throttle only abuse-prone endpoints (login, second factor, contact form)."""
    return request.method == "POST" and request.url.path in SENSITIVE_POST_PATHS


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
        engine_callback=configure_jinja,
    )

    # Session Middleware (encrypted cookie, key derived from SECRET_KEY via HKDF).
    # Revocation happens server-side via User.session_version (see security/admin_auth.py).
    secure_cookies = settings.is_production_like
    session_config = CookieBackendConfig(
        secret=settings.session_secret,
        key="atem_session",
        max_age=3600 * settings.SESSION_MAX_AGE_HOURS,
        secure=secure_cookies,
        httponly=True,
        samesite="strict",
    )

    # CSRF: double-submit cookie; HTMX/fetch send the token in the `x-csrftoken` header
    # (see layouts/base.html), classic forms in the hidden `_csrf_token` field.
    csrf_config = CSRFConfig(
        secret=settings.derive_key(b"atem-csrf").hex(),
        cookie_secure=secure_cookies,
        cookie_samesite="strict",
        exclude=["/health"],
    )

    # First line of abuse protection (per worker, in-memory). The authoritative limits for
    # login attempts live in the database (AuthService) and apply across all workers.
    rate_limit_config = RateLimitConfig(
        rate_limit=("minute", settings.RATE_LIMIT_SENSITIVE_PER_MINUTE),
        check_throttle_handler=_is_sensitive_post,
    )

    # OpenAPI Config (disabled in production – it would list every admin route)
    openapi_config = (
        None
        if settings.is_production_like
        else OpenAPIConfig(
            title="PUSTERUM API",
            version="0.1.0",
            description="Clean Architecture API für PUSTERUM – Praxis für Atem- und Körpertherapie",
            contact=Contact(
                name="PUSTERUM", email="kontakt@pusterum.be", url="https://www.pusterum.be"
            ),
        )
    )

    return Litestar(
        route_handlers=[
            HealthController,
            PublicController,
            *ADMIN_CONTROLLERS,
            static_router,
            media_router,
        ],
        dependencies={
            "settings": Provide(get_settings, sync_to_thread=False),
            "db_session": Provide(provide_db_session),
            "password_hasher": Provide(provide_password_hasher),
            "email_service": Provide(provide_email_service),
            "theme_repository": Provide(provide_theme_repository),
            "theme_service": Provide(provide_theme_service),
            "content_repository": Provide(provide_content_repository),
            "content_service": Provide(provide_content_service),
            "offering_repository": Provide(provide_offering_repository),
            "contact_repository": Provide(provide_contact_repository),
            "user_repository": Provide(provide_user_repository),
            "offering_service": Provide(provide_offering_service),
            "contact_service": Provide(provide_contact_service),
            "auth_service": Provide(provide_auth_service),
            "media_service": Provide(provide_media_service),
        },
        template_config=template_config,
        middleware=[
            DefineMiddleware(SecurityHeadersMiddleware, production=settings.is_production_like),
            DefineMiddleware(HostValidationMiddleware, allowed_hosts=settings.ALLOWED_HOSTS),
            DefineMiddleware(ProxyHeadersMiddleware, trusted_proxies=settings.TRUSTED_PROXIES),
            rate_limit_config.middleware,
            session_config.middleware,
        ],
        csrf_config=csrf_config,
        exception_handlers={**EXCEPTION_HANDLERS, NotAuthorizedException: unauthorized_handler},
        lifespan=[lifespan],
        openapi_config=openapi_config,
        debug=settings.DEBUG,
        request_max_body_size=12 * 1024 * 1024,  # uploads are capped at 10 MB by MediaService
    )
