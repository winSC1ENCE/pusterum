"""Integration tests for the operations CLI (python -m atem.cli) on a temporary database."""

import asyncio
from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import create_async_engine

from atem.cli import main
from atem.infrastructure.config.settings import get_settings
from atem.infrastructure.database.base import Base
from atem.infrastructure.database.models.content import ContentBlockModel
from atem.infrastructure.database.models.user import UserModel


@pytest.fixture
def cli_database(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    url = f"sqlite+aiosqlite:///{tmp_path / 'cli.db'}"

    async def create_schema() -> None:
        engine = create_async_engine(url)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await engine.dispose()

    asyncio.run(create_schema())
    monkeypatch.setenv("DATABASE_URL", url)
    get_settings.cache_clear()
    yield url
    get_settings.cache_clear()


def _scalar(url: str, statement: object) -> object:
    async def run() -> object:
        engine = create_async_engine(url)
        async with engine.connect() as conn:
            value = await conn.scalar(statement)  # type: ignore[call-overload]
        await engine.dispose()
        return value

    return asyncio.run(run())


def test_seed_content_is_idempotent(cli_database: str, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["seed-content"]) == 0
    first = _scalar(cli_database, select(func.count()).select_from(ContentBlockModel))
    assert main(["seed-content"]) == 0
    assert _scalar(cli_database, select(func.count()).select_from(ContentBlockModel)) == first
    assert "0 Standard-Inhalte ergänzt" in capsys.readouterr().out


def test_create_admin_reset_2fa_and_purge(
    cli_database: str, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("ATEM_ADMIN_PASSWORD", "ein-sehr-sicheres-passwort")
    assert main(["create-admin", "--username", "stephanie", "--email", "s@pusterum.be"]) == 0
    assert _scalar(cli_database, select(UserModel.username)) == "stephanie"

    # duplicates and weak passwords are rejected with exit code 1
    assert main(["create-admin", "--username", "stephanie", "--email", "s@pusterum.be"]) == 1
    monkeypatch.setenv("ATEM_ADMIN_PASSWORD", "kurz")
    assert main(["create-admin", "--username", "anna", "--email", "a@pusterum.be"]) == 1

    assert main(["reset-2fa", "--username", "stephanie"]) == 0
    assert main(["reset-2fa", "--username", "ghost"]) == 1
    assert main(["purge-messages"]) == 0
    output = capsys.readouterr()
    assert "Admin «stephanie» angelegt" in output.out
    assert "existiert bereits" in output.err


def test_interactive_password_confirmation(
    cli_database: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("ATEM_ADMIN_PASSWORD", raising=False)
    answers = iter(["ein-sehr-sicheres-passwort", "anderes-passwort-123"])
    monkeypatch.setattr("getpass.getpass", lambda _prompt: next(answers))
    assert main(["create-admin", "--username", "x", "--email", "x@pusterum.be"]) == 1
