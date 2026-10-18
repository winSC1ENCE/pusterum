"""Operator account management: password reset, deactivate/activate, delete (tech-debt #1/#2)."""

import asyncio
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from litestar import Litestar
from litestar.testing import AsyncTestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import create_async_engine

from atem.application.dto.auth import LoginRequestDTO
from atem.application.services.auth_service import AuthService
from atem.cli import main
from atem.domain.exceptions import (
    AuthenticationException,
    EntityNotFoundException,
    ValidationException,
)
from atem.domain.interfaces.email_service import IEmailService
from atem.infrastructure.config.settings import get_settings
from atem.infrastructure.database.base import Base
from atem.infrastructure.database.models.user import UserModel
from atem.infrastructure.email.mock_email_service import MockEmailService
from atem.presentation.templating import local_datetime

STEPHANIE = "stephanie@example.ch"
OPERATOR = "betreiber@example.ch"
PASSWORD = "ein-sehr-sicheres-passwort"
NEW_PASSWORD = "ein-neues-sicheres-passwort"
IP = "203.0.113.9"


async def _login(auth_service: AuthService, email: str, password: str) -> None:
    await auth_service.authenticate(LoginRequestDTO(email=email, password=password), IP)


async def _two_admins(auth_service: AuthService) -> None:
    await auth_service.create_admin(STEPHANIE, PASSWORD)
    await auth_service.create_admin(OPERATOR, PASSWORD)


# ------------------------------------------------------------------ service level
async def test_reset_password_ends_sessions_lifts_lock_and_notifies(
    auth_service: AuthService, email_service: IEmailService
) -> None:
    await _two_admins(auth_service)
    user = await auth_service.create_admin("dritte@example.ch", PASSWORD)
    for _ in range(6):  # lock the account from an unknown device
        with pytest.raises(AuthenticationException):
            await _login(auth_service, "dritte@example.ch", "falsch")

    await auth_service.reset_password("Dritte@Example.ch", NEW_PASSWORD)

    refreshed = await auth_service.get_user(user.id)
    assert refreshed.session_version == user.session_version + 1  # all sessions ended
    assert not refreshed.must_change_password
    await _login(auth_service, "dritte@example.ch", NEW_PASSWORD)  # lock lifted, new password
    with pytest.raises(AuthenticationException):
        await _login(auth_service, "dritte@example.ch", PASSWORD)
    assert isinstance(email_service, MockEmailService)
    assert email_service.password_reset_notices == ["dritte@example.ch"]


async def test_reset_password_rules(auth_service: AuthService) -> None:
    await auth_service.create_admin(STEPHANIE, PASSWORD)
    with pytest.raises(ValidationException, match="mindestens 12"):
        await auth_service.reset_password(STEPHANIE, "kurz")
    with pytest.raises(EntityNotFoundException):
        await auth_service.reset_password("ghost@example.ch", NEW_PASSWORD)
    await auth_service.reset_password(STEPHANIE, NEW_PASSWORD, require_change=True)
    user = await auth_service.authenticate(
        LoginRequestDTO(email=STEPHANIE, password=NEW_PASSWORD), IP
    )
    assert user.user.must_change_password  # temporary password: change forced at login


async def test_deactivated_account_cannot_log_in_until_reactivated(
    auth_service: AuthService,
) -> None:
    await _two_admins(auth_service)
    await auth_service.set_active(STEPHANIE, active=False)
    with pytest.raises(AuthenticationException):
        await _login(auth_service, STEPHANIE, PASSWORD)
    await auth_service.set_active(STEPHANIE, active=True)
    await _login(auth_service, STEPHANIE, PASSWORD)


async def test_last_active_admin_is_protected(auth_service: AuthService) -> None:
    await _two_admins(auth_service)
    await auth_service.set_active(OPERATOR, active=False)
    with pytest.raises(ValidationException, match="letzte aktive"):
        await auth_service.set_active(STEPHANIE, active=False)
    with pytest.raises(ValidationException, match="letzte aktive"):
        await auth_service.delete_admin(STEPHANIE)
    await auth_service.delete_admin(OPERATOR)  # inactive accounts can always be deleted
    with pytest.raises(EntityNotFoundException):
        await auth_service.delete_admin(OPERATOR)


async def test_list_accounts_shows_security_state(auth_service: AuthService) -> None:
    await _two_admins(auth_service)
    await auth_service.set_active(OPERATOR, active=False)
    await _login(auth_service, STEPHANIE, PASSWORD)

    accounts = {a.email: a for a in await auth_service.list_accounts()}

    assert list(accounts) == [OPERATOR, STEPHANIE]  # ordered by e-mail
    assert accounts[STEPHANIE].is_active
    assert accounts[STEPHANIE].last_login_at is not None
    assert not accounts[STEPHANIE].totp_enabled
    assert not accounts[OPERATOR].is_active
    assert accounts[OPERATOR].last_login_at is None


def test_local_datetime_uses_swiss_time() -> None:
    assert local_datetime(datetime(2026, 7, 1, 12, 0, tzinfo=UTC)) == "01.07.2026 14:00"
    assert local_datetime(datetime(2026, 1, 1, 12, 0)) == "01.01.2026 13:00"  # naive = UTC
    assert local_datetime(None) == ""


# ------------------------------------------------------------------------ page level
async def test_accounts_page_is_read_only_overview(app_client: AsyncTestClient[Litestar]) -> None:
    assert (await app_client.get("/admin/accounts", follow_redirects=False)).status_code in (
        302,
        303,
        401,
    )
    await app_client.post(
        "/admin/login",
        data={"email": "entwicklung@pusterum.be", "password": "admin-secure-init-pass-change-me"},
    )
    page = await app_client.get("/admin/accounts")

    assert page.status_code == 200
    assert "entwicklung@pusterum.be" in page.text
    assert "(Sie)" in page.text
    assert "aktiv" in page.text
    assert "<form" not in page.text.split('data-testid="accounts-table"', 1)[1].split("</table>")[0]
    assert 'href="/admin/accounts"' in (await app_client.get("/admin")).text


# ----------------------------------------------------------------------- CLI level
@pytest.fixture
def cli_database(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    url = f"sqlite+aiosqlite:///{tmp_path / 'accounts.db'}"

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


def _count_users(url: str) -> int:
    async def run() -> int:
        engine = create_async_engine(url)
        async with engine.connect() as conn:
            value = await conn.scalar(select(func.count()).select_from(UserModel))
        await engine.dispose()
        return int(value or 0)

    return asyncio.run(run())


def test_cli_account_commands(
    cli_database: str, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("ATEM_ADMIN_PASSWORD", PASSWORD)
    assert main(["create-admin", "--email", STEPHANIE]) == 0
    assert main(["create-admin", "--email", OPERATOR]) == 0

    monkeypatch.setenv("ATEM_ADMIN_PASSWORD", NEW_PASSWORD)
    assert main(["reset-password", "--email", STEPHANIE, "--require-change"]) == 0
    assert main(["reset-password", "--email", "ghost@example.ch"]) == 1

    assert main(["deactivate-admin", "--email", OPERATOR]) == 0
    assert main(["deactivate-admin", "--email", STEPHANIE]) == 1  # last active admin
    assert main(["activate-admin", "--email", OPERATOR]) == 0

    monkeypatch.setattr("builtins.input", lambda _prompt: "nein")
    assert main(["delete-admin", "--email", OPERATOR]) == 1  # not confirmed
    assert _count_users(cli_database) == 2
    monkeypatch.setattr("builtins.input", lambda _prompt: "ja")
    assert main(["delete-admin", "--email", OPERATOR]) == 0
    assert _count_users(cli_database) == 1
    assert main(["delete-admin", "--email", STEPHANIE, "--yes"]) == 1  # last active admin

    out, err = capsys.readouterr()
    assert f"Passwort für «{STEPHANIE}» zurückgesetzt" in out
    assert "muss es geändert werden" in out
    assert f"Konto «{OPERATOR}» deaktiviert" in out
    assert "Abgebrochen, nichts gelöscht." in out
    assert f"Konto «{OPERATOR}» gelöscht." in out
    assert "letzte aktive Admin-Konto" in err
