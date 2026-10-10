"""Alembic Environment Configuration for Async Migrations."""

import asyncio
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import pool, text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from atem.infrastructure.config.settings import get_settings
from atem.infrastructure.database.base import Base

# Import all models so Alembic autogenerate detects tables
from atem.infrastructure.database.models.contact import ContactMessageModel  # noqa: F401
from atem.infrastructure.database.models.content import (  # noqa: F401
    ContentBlockModel,
    ContentBlockVersionModel,
)
from atem.infrastructure.database.models.offering import ServiceOfferingModel  # noqa: F401
from atem.infrastructure.database.models.theme import ThemeConfigModel  # noqa: F401
from atem.infrastructure.database.models.user import UserModel  # noqa: F401

# Data migrations import shared helpers from migrations/_helpers.py
sys.path.insert(0, str(Path(__file__).resolve().parent))

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Override sqlalchemy.url with runtime settings
settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Synchronous runner for migrations."""
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        if connection.dialect.name == "postgresql":
            # Serialise concurrent container starts: only one process migrates at a time.
            connection.execute(text("SELECT pg_advisory_xact_lock(:lock_id)"), {"lock_id": 4711})
        context.run_migrations()


async def run_async_migrations() -> None:
    """Asynchronous runner for migrations."""
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = settings.DATABASE_URL

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
