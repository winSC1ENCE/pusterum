"""Erasure requests with deletion log, re-applied after a restore (tech-debt #4, ADR-0006)."""

import asyncio
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from litestar import Litestar
from litestar.testing import AsyncTestClient
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from atem.application.services.contact_service import ContactService
from atem.cli import main
from atem.domain.exceptions import EntityNotFoundException
from atem.domain.models.contact import ContactMessage, DeletionReason, MessageQuery
from atem.infrastructure.config.settings import get_settings
from atem.infrastructure.database.base import Base
from atem.infrastructure.database.models.contact import (
    ContactMessageEventModel,
    ContactMessageModel,
    DeletionLogModel,
)
from atem.infrastructure.database.repositories.sqlalchemy_contact_repository import (
    SqlAlchemyContactRepository,
)
from atem.presentation.bootstrap import build_contact_repository

ROOT = Path(__file__).resolve().parent.parent
ADMIN = {"email": "entwicklung@pusterum.be", "password": "admin-secure-init-pass-change-me"}


def _message(email: str = "maria@muster.ch", **fields: Any) -> ContactMessage:
    return ContactMessage(
        sender_name="Maria Muster", sender_email=email, message="Seit Monaten Atemnot.", **fields
    )


@pytest.fixture
def repository(db_session: AsyncSession) -> SqlAlchemyContactRepository:
    return build_contact_repository(db_session, get_settings())


async def _log(session: AsyncSession) -> list[DeletionLogModel]:
    return list((await session.execute(select(DeletionLogModel))).scalars().all())


async def _remaining(service: ContactService) -> list[str]:
    page = await service.search_messages(MessageQuery())
    return sorted(m.sender_email for m in page.items)


# ---------------------------------------------------------------------------- service
async def test_forget_person_deletes_all_messages_of_the_address_and_logs_them(
    contact_service: ContactService,
    repository: SqlAlchemyContactRepository,
    db_session: AsyncSession,
) -> None:
    first = await repository.create_message(_message())
    second = await repository.create_message(_message(email=" Maria@Muster.CH "))
    await repository.create_message(_message(email="andere@example.ch"))
    await contact_service.update_notes(first.id, "Rückruf", None)  # history goes too

    assert await contact_service.forget_person("MARIA@muster.ch") == 2
    assert await contact_service.forget_person("niemand@example.ch") == 0

    assert await _remaining(contact_service) == ["andere@example.ch"]
    log = await _log(db_session)
    assert {e.message_id for e in log} == {first.id, second.id}
    assert {e.reason for e in log} == {DeletionReason.PERSON}
    assert {e.email_hash for e in log} == {contact_service.hash_email("maria@muster.ch")}
    assert all("maria" not in str(vars(e)).lower() for e in log)  # no plain address
    count = select(func.count()).select_from(ContactMessageEventModel)
    assert await db_session.scalar(count) == 0


async def test_single_delete_is_logged_too(
    contact_service: ContactService,
    repository: SqlAlchemyContactRepository,
    db_session: AsyncSession,
) -> None:
    saved = await repository.create_message(_message())
    await contact_service.delete_message(saved.id)
    assert [(e.message_id, e.reason) for e in await _log(db_session)] == [
        (saved.id, DeletionReason.MESSAGE)
    ]
    with pytest.raises(EntityNotFoundException):
        await contact_service.delete_message(saved.id)


async def test_restored_messages_are_deleted_again_but_not_newer_ones(
    contact_service: ContactService, repository: SqlAlchemyContactRepository
) -> None:
    deleted = await repository.create_message(_message())
    await contact_service.forget_person("maria@muster.ch")
    assert await contact_service.reapply_deletions() == 0  # nothing to do normally

    # A restore brings the deleted message back; the same person writes again afterwards.
    await repository.create_message(_message(id=deleted.id))
    await repository.create_message(_message())

    assert await contact_service.reapply_deletions() == 1
    page = await contact_service.search_messages(MessageQuery())
    assert [m.id for m in page.items] != [deleted.id] and page.total == 1


async def test_log_entries_expire_after_seven_months(
    contact_service: ContactService,
    repository: SqlAlchemyContactRepository,
    db_session: AsyncSession,
) -> None:
    for _ in range(2):
        await contact_service.delete_message((await repository.create_message(_message())).id)
    oldest = (await _log(db_session))[0]
    await db_session.execute(
        update(DeletionLogModel)
        .where(DeletionLogModel.id == oldest.id)
        .values(created_at=datetime.now(UTC) - timedelta(days=214))
    )
    await contact_service.purge_expired()
    assert len(await _log(db_session)) == 1


# ------------------------------------------------------------------------------ HTTP
async def test_detail_view_forgets_the_sender(
    app_client: AsyncTestClient[Litestar], async_engine: AsyncEngine
) -> None:
    async with async_sessionmaker(async_engine, expire_on_commit=False)() as session:
        repo = build_contact_repository(session, get_settings())
        saved = await repo.create_message(_message())
        await repo.create_message(_message())
        await repo.create_message(_message(email="andere@example.ch"))
        await session.commit()
    await app_client.post("/admin/login", data=ADMIN)
    url = f"/admin/messages/{saved.id}"

    detail = await app_client.get(url)
    assert "Alle 2 Anfragen dieser Adresse endgültig löschen" in detail.text
    assert (await app_client.post(f"{url}/forget", data={})).status_code == 400
    listing = await app_client.post(f"{url}/forget", data={"confirm": "yes"})
    assert listing.status_code == 200
    assert "1 Anfrage" in listing.text  # only the other address is left

    async with async_sessionmaker(async_engine)() as session:
        assert await session.scalar(select(func.count()).select_from(DeletionLogModel)) == 2


# ------------------------------------------------------------------------------- CLI
@pytest.fixture
def cli_database(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    url = f"sqlite+aiosqlite:///{tmp_path / 'forget.db'}"

    async def create_schema_with_messages() -> None:
        engine = create_async_engine(url)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with async_sessionmaker(engine)() as session:
            repo = build_contact_repository(session, get_settings())
            for email in ("maria@muster.ch", "maria@muster.ch", "andere@example.ch"):
                await repo.create_message(_message(email=email))
            await session.commit()
        await engine.dispose()

    get_settings.cache_clear()
    asyncio.run(create_schema_with_messages())
    monkeypatch.setenv("DATABASE_URL", url)
    get_settings.cache_clear()
    yield url
    get_settings.cache_clear()


def _message_count(url: str) -> int:
    async def run() -> int:
        engine = create_async_engine(url)
        async with engine.connect() as conn:
            count = await conn.scalar(select(func.count()).select_from(ContactMessageModel))
        await engine.dispose()
        return int(count or 0)

    return asyncio.run(run())


def test_cli_forget_person_asks_first(
    cli_database: str, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("builtins.input", lambda _: "nein")
    assert main(["forget-person", "--email", "maria@muster.ch"]) == 1
    assert _message_count(cli_database) == 3

    monkeypatch.setattr("builtins.input", lambda _: "ja")
    assert main(["forget-person", "--email", "maria@muster.ch"]) == 0
    assert "2 Anfragen gelöscht" in capsys.readouterr().out
    assert _message_count(cli_database) == 1


def test_cli_forget_person_yes_and_reapply(
    cli_database: str, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["forget-person", "--email", "andere@example.ch", "--yes"]) == 0
    assert main(["reapply-deletions"]) == 0
    assert "0 Anfragen aus dem Löschprotokoll erneut gelöscht." in capsys.readouterr().out


# ------------------------------------------------------------------------------- ops
def test_restore_keeps_the_deletion_log_and_the_app_reapplies_it() -> None:
    restore = (ROOT / "docker/backup/restore.sh").read_text()
    save, restore_db, merge = (
        restore.index("\\copy (SELECT $COLUMNS FROM deletion_log) TO"),
        restore.index("pg_restore"),
        restore.index("INSERT INTO deletion_log"),
    )
    assert save < restore_db < merge
    assert "ON CONFLICT (id) DO NOTHING" in restore
    entrypoint = (ROOT / "docker/entrypoint.sh").read_text()
    assert entrypoint.index("alembic upgrade head") < entrypoint.index("reapply-deletions")
    assert entrypoint.index("reapply-deletions") < entrypoint.index('exec "$@"')
