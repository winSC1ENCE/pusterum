"""Application Settings and Configuration."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly typed application configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Environment
    ENVIRONMENT: Literal["development", "staging", "production", "test"] = "development"
    DEBUG: bool = False
    SECRET_KEY: str = Field(
        default="insecure-dev-secret-key-at-least-32-chars-long",
        min_length=32,
    )
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    ALLOWED_HOSTS: list[str] = ["localhost", "127.0.0.1", "0.0.0.0"]

    # Database
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://atem_user:atem_secure_password@localhost:5432/atem_db",
    )
    DB_ECHO: bool = False
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20

    # Email
    MAIL_ENABLED: bool = False
    MAIL_FROM: str = "kontakt@pusterum.be"
    MAIL_TO: str = "kontakt@pusterum.be"
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 1025
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_USE_TLS: bool = False

    # Initial Admin
    ADMIN_USERNAME: str = "admin"
    ADMIN_EMAIL: str = "admin@pusterum.be"
    ADMIN_INITIAL_PASSWORD: str = "admin-secure-init-pass-change-me"

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


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Singleton getter for application settings."""
    return Settings()
