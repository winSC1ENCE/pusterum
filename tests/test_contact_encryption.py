"""Contact free text is encrypted at rest (tech-debt #15, TDR-0012) and exportable (Art. 25 DSG)."""

import asyncio
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from atem.application.dto.contact import CreateContactMessageDTO
from atem.application.services.contact_service import ContactService
from atem.cli import main
from atem.domain.models.contact import ContactMessage, MessageQuery, MessageStatus
from atem.infrastructure.config.settings import get_settings
from atem.infrastructure.database.base import Base
from atem.infrastructure.database.models.contact import ContactMessageModel
from atem.infrastructure.database.repositories.sqlalchemy_contact_repository import (
    UNREADABLE,
    SqlAlchemyContactRepository,
)
from atem.infrastructure.security.fernet_secret_cipher import FernetSecretCipher
from atem.presentation.bootstrap import build_contact_repository
from tests.conftest import solve_altcha

HEALTH_TEXT = "Seit Monaten Atemnot und Panikattacken."
PHONE = "+41 31 123 45 67"


async def _submit(service: ContactService, email: str = "maria@muster.ch") -> Any:
    dto = CreateContactMessageDTO(
        sender_name="Maria Muster",
        sender_email=email,
        sender_phone=PHONE,
        subject="Terminanfrage",
        message=HEALTH_TEXT,
    )
    return await service.submit_contact_form(
        dto,
        client_ip="198.51.100.5",
        captcha_payload=solve_altcha(service.create_captcha_challenge()),
    )


async def test_free_text_is_stored_encrypted_and_read_in_clear(
    contact_service: ContactService, db_session: AsyncSession
) -> None:
    saved = await _submit(contact_service)
    repository = build_contact_repository(db_session, get_settings())
    message = await repository.get_message_by_id(saved.id)
    assert message is not None
    message.notes = "Rückruf vereinbart"
    await repository.update_message(message)

    row = (
        await db_session.execute(
            select(
                ContactMessageModel.message,
                ContactMessageModel.sender_phone,
                ContactMessageModel.notes,
                ContactMessageModel.subject,
            )
        )
    ).one()
    assert HEALTH_TEXT not in row.message
    assert PHONE not in row.sender_phone
    assert "Rückruf" not in row.notes
    assert row.subject == "Terminanfrage"  # stays searchable

    listed = (await contact_service.search_messages(MessageQuery())).items[0]
    assert (listed.message, listed.sender_phone, listed.notes) == (
        HEALTH_TEXT,
        PHONE,
        "Rückruf vereinbart",
    )


async def test_wrong_key_shows_placeholder_and_keeps_ciphertext(
    contact_service: ContactService, db_session: AsyncSession
) -> None:
    saved = await _submit(contact_service)
    other_key = SqlAlchemyContactRepository(db_session, FernetSecretCipher(b"x" * 32))

    unreadable = await other_key.get_message_by_id(saved.id)
    assert unreadable is not None
    assert unreadable.message == UNREADABLE
    unreadable.status = MessageStatus.IN_PROGRESS
    await other_key.update_message(unreadable)  # status change must not destroy the text

    readable = await build_contact_repository(db_session, get_settings()).get_message_by_id(
        saved.id
    )
    assert readable is not None
    assert (readable.message, readable.status) == (HEALTH_TEXT, MessageStatus.IN_PROGRESS)


async def test_export_person_finds_all_messages_of_one_address(
    contact_service: ContactService,
) -> None:
    await _submit(contact_service)
    await _submit(contact_service, email="andere@example.ch")

    exported = await contact_service.export_person("  Maria@Muster.CH ")

    assert len(exported) == 1
    assert exported[0]["nachricht"] == HEALTH_TEXT
    assert exported[0]["telefon"] == PHONE
    assert exported[0]["status"] == "NEW"
    assert await contact_service.export_person("niemand@example.ch") == []


# ----------------------------------------------------------------------------- CLI
@pytest.fixture
def cli_database(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    url = f"sqlite+aiosqlite:///{tmp_path / 'contacts.db'}"

    async def create_schema_with_message() -> None:
        engine = create_async_engine(url)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with async_sessionmaker(engine)() as session:
            await build_contact_repository(session, get_settings()).create_message(
                ContactMessage(sender_name="Maria", sender_email="maria@muster.ch", message="Hallo")
            )
            await session.commit()
        await engine.dispose()

    get_settings.cache_clear()
    asyncio.run(create_schema_with_message())
    monkeypatch.setenv("DATABASE_URL", url)
    get_settings.cache_clear()
    yield url
    get_settings.cache_clear()


def test_cli_export_person_prints_json(
    cli_database: str, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["export-person", "--email", "MARIA@muster.ch"]) == 0
    out, err = capsys.readouterr()
    assert [entry["nachricht"] for entry in json.loads(out)] == ["Hallo"]
    assert "1 Anfragen exportiert." in err
