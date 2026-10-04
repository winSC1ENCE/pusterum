"""Application Settings and Configuration."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Only accepted in development/test. Production refuses to start with it (see _validate_production).
DEV_SECRET_KEY = "dev-only-insecure-secret-key-do-not-use-in-production"  # nosec B105
LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "0.0.0.0", "::1"})
DEFAULT_DB_PASSWORD = "atem_secure_password"  # nosec B105 - rejected in prod
MIN_SECRET_LENGTH = 32


class Settings(BaseSettings):
    """Strongly typed application configuration.

    Defaults are safe for production: ``ENVIRONMENT`` defaults to ``production`` and the
    application refuses to start there with development secrets or debug settings.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Environment
    ENVIRONMENT: Literal["development", "staging", "production", "test"] = "production"
    DEBUG: bool = False
    SECRET_KEY: str = Field(default=DEV_SECRET_KEY, min_length=MIN_SECRET_LENGTH)
    ALLOWED_HOSTS: list[str] = ["localhost", "127.0.0.1"]
    # Reverse proxies whose X-Forwarded-For header is trusted (CIDR notation).
    TRUSTED_PROXIES: list[str] = ["127.0.0.1/32", "172.16.0.0/12"]

    # Database
    DATABASE_URL: str = Field(
        default=f"postgresql+asyncpg://atem_user:{DEFAULT_DB_PASSWORD}@localhost:5432/atem_db",
    )
    DB_ECHO: bool = False
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 5

    # Email
    MAIL_ENABLED: bool = False
    MAIL_FROM: str = "kontakt@pusterum.be"
    MAIL_TO: str = "kontakt@pusterum.be"
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 1025
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_USE_TLS: bool = False
    SMTP_STARTTLS: bool = False
    SMTP_TIMEOUT_SECONDS: int = 15

    # Local admin: dev/test seeding only (production: `python -m atem.cli create-admin`).
    # The login is the e-mail address; generic mailboxes such as admin@… are refused.
    ADMIN_EMAIL: str = "entwicklung@pusterum.be"
    ADMIN_INITIAL_PASSWORD: str | None = None
    # Two-factor authentication for the admin. None = mandatory in production/staging only.
    ADMIN_REQUIRE_2FA: bool | None = None
    SESSION_MAX_AGE_HOURS: int = 12
    # Contact form abuse protection
    CONTACT_MAX_PER_IP_HOUR: int = 3
    CONTACT_MAX_PER_IP_DAY: int = 10
    CONTACT_FORM_MIN_SECONDS: int = 3
    ALTCHA_MAX_NUMBER: int = 100_000  # proof-of-work difficulty (≈ 0.1–0.5 s on a phone)
    ALTCHA_EXPIRES_MINUTES: int = 20
    MESSAGE_RETENTION_DAYS: int = 365  # contact messages are deleted automatically afterwards
    # Requests per minute and client IP on login / 2FA / contact (in-memory, per worker)
    RATE_LIMIT_SENSITIVE_PER_MINUTE: int = 10

    # Dynamic User Media Storage (Persistent Docker Volume)
    MEDIA_DIR: str = "storage/uploads"

    @property
    def media_storage_path(self) -> Path:
        """Return resolved Path to persistent media uploads directory."""
        return Path(self.MEDIA_DIR).resolve()

    @property
    def is_dev(self) -> bool:
        """Return True if running in development mode."""
        return self.ENVIRONMENT == "development"

    @property
    def is_production_like(self) -> bool:
        """Return True for environments that face the internet (production, staging)."""
        return self.ENVIRONMENT in ("production", "staging")

    @property
    def require_2fa(self) -> bool:
        """Return True if admins must enrol a second factor before using the admin area."""
        if self.ADMIN_REQUIRE_2FA is not None:
            return self.ADMIN_REQUIRE_2FA
        return self.is_production_like

    @property
    def session_secret(self) -> bytes:
        """Derive a dedicated 32-byte key for the encrypted session cookie."""
        return self.derive_key(b"atem-session-cookie")

    def derive_key(self, purpose: bytes, length: int = 32) -> bytes:
        """Derive a purpose-bound key from SECRET_KEY via HKDF-SHA256."""
        hkdf = HKDF(algorithm=hashes.SHA256(), length=length, salt=None, info=purpose)
        return hkdf.derive(self.SECRET_KEY.encode())

    @model_validator(mode="after")
    def _validate_production(self) -> "Settings":
        """Refuse insecure configuration in internet-facing environments."""
        if not self.is_production_like:
            return self

        problems: list[str] = []
        if self.SECRET_KEY == DEV_SECRET_KEY:
            problems.append(
                "SECRET_KEY ist der Entwicklungs-Standard – erzeugen mit: "
                "python -c 'import secrets; print(secrets.token_hex(32))'"
            )
        if self.DEBUG:
            problems.append("DEBUG muss in Produktion false sein")
        if not set(self.ALLOWED_HOSTS) - LOCAL_HOSTS:
            problems.append("ALLOWED_HOSTS muss die öffentliche Domain enthalten")
        placeholders = [
            name
            for name in ("SECRET_KEY", "DATABASE_URL", "SMTP_HOST", "SMTP_PASSWORD")
            if "CHANGE_ME" in str(getattr(self, name))
        ]
        if placeholders:
            problems.append(f"Platzhalter «CHANGE_ME» nicht ersetzt: {', '.join(placeholders)}")
        if DEFAULT_DB_PASSWORD in self.DATABASE_URL:
            problems.append("DATABASE_URL verwendet das Standard-Datenbankpasswort")
        if self.MAIL_ENABLED and not (self.SMTP_USE_TLS or self.SMTP_STARTTLS):
            problems.append("MAIL_ENABLED erfordert SMTP_USE_TLS oder SMTP_STARTTLS")

        if problems:
            details = "\n  - ".join(problems)
            raise ValueError(f"Unsichere Konfiguration für {self.ENVIRONMENT}:\n  - {details}")
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Singleton getter for application settings."""
    return Settings()
