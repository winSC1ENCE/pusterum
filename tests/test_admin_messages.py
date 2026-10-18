"""Contact message workflow: status model, history, list, detail, retention (TDR-0010)."""

import json
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import pytest
from litestar import Litestar
from litestar.testing import AsyncTestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from atem.application.services.auth_service import AuthService
from atem.application.services.contact_service import ContactService
from atem.domain.exceptions import ValidationException
from atem.domain.models.contact import (
    OPEN_STATUSES,
    ContactMessage,
    MessageQuery,
    MessageSort,
    MessageStatus,
    RetentionPolicy,
)
from atem.infrastructure.config.settings import get_settings
from atem.infrastructure.database.models.contact import ContactMessageEventModel
from atem.infrastructure.database.repositories.sqlalchemy_contact_repository import (
    SqlAlchemyContactRepository,
)
from atem.presentation.bootstrap import build_contact_repository

ADMIN = {"email": "entwicklung@pusterum.be", "password": "admin-secure-init-pass-change-me"}
NOW = datetime(2026, 10, 18, 12, 0, tzinfo=UTC)


def _message(**fields: Any) -> ContactMessage:
    values: dict[str, Any] = {
        "sender_name": "Maria Muster",
        "sender_email": "maria@muster.ch",
        "subject": "Terminanfrage",
        "message": "Seit Monaten Atemnot.",
    }
    return ContactMessage(**(values | fields))


@pytest.fixture
def repository(db_session: AsyncSession) -> SqlAlchemyContactRepository:
    return build_contact_repository(db_session, get_settings())


async def _admin_id(auth_service: AuthService) -> UUID:
    return (await auth_service.create_admin("stephanie@example.ch", "ein-sehr-sicheres-pw")).id


# ----------------------------------------------------------------------------- domain
def test_status_codes_labels_and_open_set() -> None:
    assert [s.value for s in MessageStatus] == ["NEW", "IN_PROGRESS", "REPLIED", "DONE", "SPAM"]
    assert [s.label for s in MessageStatus] == [
        "Neu",
        "In Bearbeitung",
        "Beantwortet",
        "Erledigt",
        "Spam",
    ]
    assert OPEN_STATUSES == (MessageStatus.NEW, MessageStatus.IN_PROGRESS, MessageStatus.REPLIED)


def test_closing_sets_and_reopening_clears_closed_at() -> None:
    message = _message()
    message.change_status(MessageStatus.DONE, NOW)
    assert message.closed_at == NOW
    message.change_status(MessageStatus.SPAM, NOW + timedelta(days=1))
    assert message.closed_at == NOW + timedelta(days=1)
    message.change_status(MessageStatus.IN_PROGRESS)
    assert message.closed_at is None


def test_retention_dates_per_status() -> None:
    policy = RetentionPolicy()
    open_message = _message(created_at=NOW)
    assert policy.delete_after(open_message) == NOW + timedelta(days=365)
    done = _message(created_at=NOW, status=MessageStatus.DONE, closed_at=NOW + timedelta(days=10))
    assert policy.delete_after(done) == NOW + timedelta(days=193)
    spam = _message(created_at=NOW, status=MessageStatus.SPAM, closed_at=NOW)
    assert policy.delete_after(spam) == NOW + timedelta(days=7)
    late = _message(created_at=NOW, status=MessageStatus.DONE, closed_at=NOW + timedelta(days=300))
    assert policy.delete_after(late) == NOW + timedelta(days=365)  # 12 months is the maximum


def test_first_name() -> None:
    assert _message(sender_name="  Maria  Luisa Muster ").first_name == "Maria"
    assert _message(sender_name="   ").first_name == ""


# ---------------------------------------------------------------------------- service
async def test_opening_moves_new_to_in_progress_once_with_history(
    contact_service: ContactService,
    repository: SqlAlchemyContactRepository,
    auth_service: AuthService,
) -> None:
    actor = await _admin_id(auth_service)
    saved = await repository.create_message(_message())

    detail = await contact_service.open_message(saved.id, actor)
    again = await contact_service.open_message(saved.id, actor)

    assert detail.message.status == again.message.status == MessageStatus.IN_PROGRESS
    assert [e.summary for e in again.events] == ["Status: Neu → In Bearbeitung"]
    assert again.events[0].actor_email == "stephanie@example.ch"


async def test_status_changes_and_notes_are_recorded_without_content(
    contact_service: ContactService,
    repository: SqlAlchemyContactRepository,
    db_session: AsyncSession,
    auth_service: AuthService,
) -> None:
    actor = await _admin_id(auth_service)
    saved = await repository.create_message(_message())

    done = await contact_service.change_status(saved.id, MessageStatus.DONE, actor)
    assert done.closed_at is not None and not done.status.is_open
    await contact_service.change_status(saved.id, MessageStatus.DONE, actor)  # no-op
    await contact_service.change_status(saved.id, MessageStatus.IN_PROGRESS, None)
    await contact_service.update_notes(saved.id, "  Rückruf am Montag  ", actor)
    await contact_service.update_notes(saved.id, "Rückruf am Montag", actor)  # unchanged

    detail = await contact_service.open_message(saved.id, actor)
    assert detail.message.closed_at is None
    assert detail.message.notes == "Rückruf am Montag"
    assert [(e.summary, e.actor_email) for e in detail.events] == [
        ("Status: Neu → Erledigt", "stephanie@example.ch"),
        ("Status: Erledigt → In Bearbeitung", None),
        ("Notizen geändert", "stephanie@example.ch"),
    ]
    stored = (await db_session.execute(select(ContactMessageEventModel))).scalars().all()
    assert all("Rückruf" not in str((e.old_value, e.new_value)) for e in stored)

    with pytest.raises(ValidationException):
        await contact_service.update_notes(saved.id, "x" * 5001, actor)


async def test_deleting_a_message_removes_its_history(
    contact_service: ContactService,
    repository: SqlAlchemyContactRepository,
    db_session: AsyncSession,
) -> None:
    saved = await repository.create_message(_message())
    await contact_service.change_status(saved.id, MessageStatus.SPAM, None)
    await contact_service.delete_message(saved.id)
    assert await db_session.scalar(select(func.count()).select_from(ContactMessageEventModel)) == 0


async def test_overdue_hint_after_two_days_new(
    contact_service: ContactService, repository: SqlAlchemyContactRepository
) -> None:
    await repository.create_message(_message(created_at=datetime.now(UTC) - timedelta(days=3)))
    await repository.create_message(_message(created_at=datetime.now(UTC) - timedelta(days=1)))
    page = await contact_service.search_messages(MessageQuery(sort=MessageSort.OLDEST))
    assert [m.overdue for m in page.items] == [True, False]
    assert all(m.delete_after is not None for m in page.items)


# ------------------------------------------------------------------------------ list
async def test_search_filters_sorts_and_pages(
    contact_service: ContactService, repository: SqlAlchemyContactRepository
) -> None:
    base = datetime.now(UTC) - timedelta(days=30)
    data = [
        ("Zora Weber", "zora@example.ch", "Frage zu Kosten", MessageStatus.NEW),
        ("anna 100% Meier", "anna@example.ch", "Terminanfrage", MessageStatus.DONE),
        ("Bruno Keller", "bruno@praxis.ch", "Terminanfrage: Atemkurs", MessageStatus.REPLIED),
        ("Carla Roth", "carla@example.ch", "Sonstiges", MessageStatus.SPAM),
    ]
    for day, (name, email, subject, status) in enumerate(data):
        await repository.create_message(
            _message(
                sender_name=name,
                sender_email=email,
                subject=subject,
                status=status,
                created_at=base + timedelta(days=day),
            )
        )

    async def names(**query: Any) -> list[str]:
        page = await contact_service.search_messages(MessageQuery(**query))
        return [m.sender_name for m in page.items]

    # Default: open first, then newest
    assert await names() == ["Bruno Keller", "Zora Weber", "Carla Roth", "anna 100% Meier"]
    assert await names(statuses=OPEN_STATUSES) == ["Bruno Keller", "Zora Weber"]
    assert await names(text="TERMIN") == ["Bruno Keller", "anna 100% Meier"]
    assert await names(text="praxis.ch") == ["Bruno Keller"]
    assert await names(text="100%") == ["anna 100% Meier"]  # wildcard escaped
    assert await names(text="%") == ["anna 100% Meier"]
    assert await names(sort=MessageSort.NAME) == [
        "anna 100% Meier",
        "Bruno Keller",
        "Carla Roth",
        "Zora Weber",
    ]
    assert await names(sort=MessageSort.STATUS) == [
        "Zora Weber",
        "Bruno Keller",
        "anna 100% Meier",
        "Carla Roth",
    ]
    assert await names(
        received_from=base + timedelta(days=1), received_before=base + timedelta(days=3)
    ) == ["Bruno Keller", "anna 100% Meier"]

    page = await contact_service.search_messages(
        MessageQuery(sort=MessageSort.OLDEST, limit=3, offset=3)
    )
    assert (page.total, page.page, page.pages) == (4, 2, 2)
    assert [m.sender_name for m in page.items] == ["Carla Roth"]


# ------------------------------------------------------------------------- retention
async def test_retention_per_status(
    contact_service: ContactService,
    repository: SqlAlchemyContactRepository,
    db_session: AsyncSession,
) -> None:
    now = datetime.now(UTC)
    cases = {
        "done-old": (MessageStatus.DONE, now - timedelta(days=200), now - timedelta(days=184)),
        "done-recent": (MessageStatus.DONE, now - timedelta(days=200), now - timedelta(days=10)),
        "spam-old": (MessageStatus.SPAM, now - timedelta(days=9), now - timedelta(days=8)),
        "spam-recent": (MessageStatus.SPAM, now - timedelta(days=9), now - timedelta(days=2)),
        "open-old": (MessageStatus.REPLIED, now - timedelta(days=366), None),
        "open-recent": (MessageStatus.NEW, now - timedelta(days=364), None),
    }
    for name, (status, created_at, closed_at) in cases.items():
        saved = await repository.create_message(
            _message(sender_name=name, status=status, created_at=created_at, closed_at=closed_at)
        )
        await contact_service.update_notes(saved.id, "Notiz", None)  # adds a history entry

    assert await contact_service.purge_expired() == 3

    page = await contact_service.search_messages(MessageQuery(sort=MessageSort.NAME))
    assert [m.sender_name for m in page.items] == ["done-recent", "open-recent", "spam-recent"]
    assert await db_session.scalar(select(func.count()).select_from(ContactMessageEventModel)) == 3


# ------------------------------------------------------------------------------ HTTP
async def _submit_and_login(client: AsyncTestClient[Litestar], engine: AsyncEngine) -> UUID:
    async with async_sessionmaker(engine, expire_on_commit=False)() as session:
        saved = await build_contact_repository(session, get_settings()).create_message(
            _message(sender_phone="+41 31 123 45 67")
        )
        await session.commit()
    await client.post("/admin/login", data=ADMIN)
    return saved.id


async def test_list_page_with_tabs_filters_and_paging(
    app_client: AsyncTestClient[Litestar], async_engine: AsyncEngine
) -> None:
    message_id = await _submit_and_login(app_client, async_engine)

    page = await app_client.get("/admin/messages")
    assert page.status_code == 200
    assert f'href="/admin/messages/{message_id}"' in page.text
    assert 'data-status="NEW"' in page.text
    assert "wird gelöscht am" in page.text

    done = await app_client.get("/admin/messages?status=DONE")
    assert "Keine Anfragen für diese Auswahl." in done.text
    search = await app_client.get(
        "/admin/messages?status=all&q=muster&from=2000-01-01&to=2099-12-31"
    )
    assert f"/admin/messages/{message_id}" in search.text
    assert 'value="2099-12-31"' in search.text
    invalid = await app_client.get("/admin/messages?status=X&sort=X&page=X&from=X&to=13.13.2026")
    assert invalid.status_code == 200  # falls back to defaults
    assert 'aria-current="page"' in invalid.text


async def test_detail_page_actions(
    app_client: AsyncTestClient[Litestar], async_engine: AsyncEngine
) -> None:
    message_id = await _submit_and_login(app_client, async_engine)
    url = f"/admin/messages/{message_id}"

    detail = await app_client.get(url)
    assert detail.status_code == 200
    assert "Seit Monaten Atemnot." in detail.text
    assert 'data-status="IN_PROGRESS"' in detail.text  # opened → in progress
    assert "mailto:maria@muster.ch?subject=Re%3A%20Terminanfrage" in detail.text
    assert 'href="tel:+41311234567"' in detail.text
    assert "Status: Neu → In Bearbeitung" in detail.text
    assert "(entwicklung@pusterum.be)" in detail.text

    replied = await app_client.post(f"{url}/status", data={"status": "REPLIED"})
    assert replied.status_code == 200 and 'data-status="REPLIED"' in replied.text
    assert (await app_client.post(f"{url}/status", data={"status": "READ"})).status_code == 400

    notes = await app_client.post(f"{url}/notes", data={"notes": "Rückruf Montag"})
    assert "Rückruf Montag</textarea>" in notes.text
    assert "Notizen geändert" in notes.text

    export = await app_client.get(f"{url}/export")
    assert export.headers["content-disposition"] == 'attachment; filename="auskunft.json"'
    assert export.headers["cache-control"] == "no-store"
    assert [m["status"] for m in json.loads(export.content)] == ["REPLIED"]

    unconfirmed = await app_client.post(f"{url}/delete", data={})
    assert unconfirmed.status_code == 400
    deleted = await app_client.post(f"{url}/delete", data={"confirm": "yes"})
    assert deleted.status_code == 200 and str(message_id) not in deleted.text
    assert (await app_client.get(url)).status_code == 404


async def test_dashboard_lists_open_messages(
    app_client: AsyncTestClient[Litestar], async_engine: AsyncEngine
) -> None:
    message_id = await _submit_and_login(app_client, async_engine)
    dashboard = await app_client.get("/admin")
    assert f'href="/admin/messages/{message_id}"' in dashboard.text
    assert 'data-testid="all-messages-link"' in dashboard.text
