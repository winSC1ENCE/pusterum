"""Composition-root helpers for one-off initialisation tasks.

Shared by the application lifespan (development/test) and the CLI (`python -m atem.cli`),
which the production container entrypoint runs once before the web workers start.
"""

from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from atem.application.services.auth_service import AuthService
from atem.application.services.contact_service import ContactLimits, ContactService
from atem.application.services.content_service import ContentService
from atem.domain.exceptions import ValidationException
from atem.domain.interfaces.contact_repository import IContactRepository
from atem.domain.interfaces.email_service import IEmailService
from atem.domain.models.contact import RetentionPolicy
from atem.infrastructure.captcha.altcha_captcha import AltchaCaptcha
from atem.infrastructure.config.settings import Settings, get_settings
from atem.infrastructure.database.repositories.sqlalchemy_contact_repository import (
    SqlAlchemyContactRepository,
)
from atem.infrastructure.database.repositories.sqlalchemy_content_repository import (
    SqlAlchemyContentRepository,
)
from atem.infrastructure.database.repositories.sqlalchemy_user_repository import (
    SqlAlchemyUserRepository,
)
from atem.infrastructure.email.mock_email_service import MockEmailService
from atem.infrastructure.security.argon2_password_hasher import Argon2PasswordHasher
from atem.infrastructure.security.fernet_secret_cipher import FernetSecretCipher
from atem.infrastructure.security.pyotp_totp_provider import PyotpTotpProvider

logger = structlog.get_logger(__name__)

LOGIN_ATTEMPT_RETENTION = timedelta(days=30)
RETENTION_LOCK_KEY = 0x50555354  # arbitrary constant ("PUST") for pg_try_advisory_xact_lock


async def seed_content(session_factory: async_sessionmaker[AsyncSession]) -> int:
    """Insert missing default content blocks (idempotent)."""
    async with session_factory() as session:
        service = ContentService(SqlAlchemyContentRepository(session))
        inserted = await service.seed_defaults()
        await session.commit()
    return inserted


def build_secret_cipher(settings: Settings) -> FernetSecretCipher:
    """Cipher for secrets at rest (TOTP seeds), keyed from SECRET_KEY via HKDF."""
    return FernetSecretCipher(settings.derive_key(b"atem-secret-cipher"))


def build_contact_cipher(settings: Settings) -> FernetSecretCipher:
    """Cipher for contact free text (message, phone, notes), keyed from SECRET_KEY via HKDF."""
    return FernetSecretCipher(settings.derive_key(b"atem-contact-cipher"))


def build_contact_repository(
    session: AsyncSession, settings: Settings
) -> SqlAlchemyContactRepository:
    """Contact repository that encrypts free text at rest (TDR-0012)."""
    return SqlAlchemyContactRepository(session, build_contact_cipher(settings))


def build_contact_service(
    repository: IContactRepository, email_service: IEmailService, settings: Settings
) -> ContactService:
    """ContactService with self-hosted ALTCHA captcha and the configured abuse limits."""
    captcha = AltchaCaptcha(
        hmac_key=settings.derive_key(b"atem-altcha").hex(),
        max_number=settings.ALTCHA_MAX_NUMBER,
        expires_after=timedelta(minutes=settings.ALTCHA_EXPIRES_MINUTES),
    )
    return ContactService(
        repository,
        email_service,
        captcha,
        email_hash_key=settings.derive_key(b"atem-email-hash"),
        limits=ContactLimits(
            per_ip_hour=settings.CONTACT_MAX_PER_IP_HOUR,
            per_ip_day=settings.CONTACT_MAX_PER_IP_DAY,
        ),
        retention=retention_policy(settings),
    )


def retention_policy(settings: Settings) -> RetentionPolicy:
    """Retention periods of contact messages from the settings."""
    return RetentionPolicy(
        done=timedelta(days=settings.MESSAGE_RETENTION_DONE_DAYS),
        spam=timedelta(days=settings.MESSAGE_RETENTION_SPAM_DAYS),
        max_age=timedelta(days=settings.MESSAGE_RETENTION_DAYS),
    )


async def purge_expired_data(
    session_factory: async_sessionmaker[AsyncSession], settings: Settings
) -> int:
    """Data retention: delete expired contact messages, captcha and login-attempt records.

    On PostgreSQL a transaction-scoped advisory lock keeps the workers from running it at the
    same time (each granian worker has its own daily loop); a worker that does not get the
    lock skips this round.
    """
    async with session_factory() as session:
        if session.get_bind().dialect.name == "postgresql":
            got_lock = await session.scalar(
                text("SELECT pg_try_advisory_xact_lock(:key)"), {"key": RETENTION_LOCK_KEY}
            )
            if not got_lock:
                logger.info("retention_skipped_locked")
                return 0
        service = build_contact_service(
            build_contact_repository(session, settings), MockEmailService(), settings
        )
        deleted = await service.purge_expired()
        await SqlAlchemyUserRepository(session).delete_login_attempts_older_than(
            datetime.now(UTC) - LOGIN_ATTEMPT_RETENTION
        )
        await session.commit()
    return deleted


def build_auth_service(session: AsyncSession) -> AuthService:
    """Create an AuthService bound to the given session."""
    return AuthService(
        SqlAlchemyUserRepository(session),
        Argon2PasswordHasher(),
        build_secret_cipher(get_settings()),
        PyotpTotpProvider(),
    )


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
        try:
            await build_auth_service(session).ensure_initial_admin(
                email=settings.ADMIN_EMAIL,
                initial_password=settings.ADMIN_INITIAL_PASSWORD,
            )
        except ValidationException as exc:
            logger.warning("dev_admin_not_seeded", reason=exc.message)
            return
        await session.commit()
