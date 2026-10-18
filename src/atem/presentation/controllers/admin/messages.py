"""Contact messages: list with filters, detail view with notes and history (TDR-0010)."""

import json
from datetime import date, datetime, timedelta
from typing import Any
from uuid import UUID

from litestar import Controller, Request, get, post
from litestar.datastructures import MultiDict
from litestar.di import NamedDependency
from litestar.params import FromPath
from litestar.response import Redirect, Response, Template

from atem.application.services.contact_service import ContactService
from atem.application.services.theme_service import ThemeService
from atem.domain.exceptions import ValidationException
from atem.domain.models.contact import (
    OPEN_STATUSES,
    STATUS_LABELS,
    MessageQuery,
    MessageSort,
    MessageStatus,
)
from atem.presentation.controllers.admin.common import FormData, admin_page, current_author
from atem.presentation.security.admin_auth import require_admin
from atem.presentation.templating import PRACTICE_TIMEZONE

PAGE_SIZE = 25
OPEN_FILTER = "open"
ALL_FILTER = "all"
SORT_LABELS: dict[MessageSort, str] = {
    MessageSort.OPEN_FIRST: "Offene zuerst",
    MessageSort.NEWEST: "Neueste zuerst",
    MessageSort.OLDEST: "Älteste zuerst",
    MessageSort.NAME: "Name",
    MessageSort.STATUS: "Status",
}


def _local_day_start(raw: str) -> datetime | None:
    """Start of a calendar day (YYYY-MM-DD) in Swiss local time; None if empty or invalid."""
    try:
        day = date.fromisoformat(raw)
    except ValueError:
        return None
    return datetime(day.year, day.month, day.day, tzinfo=PRACTICE_TIMEZONE)


def _parse_filters(params: MultiDict[str]) -> tuple[MessageQuery, dict[str, str]]:
    """Query for the repository and the cleaned filter values (for links and the form)."""
    status = params.get("status") or OPEN_FILTER
    if status == ALL_FILTER:
        statuses: tuple[MessageStatus, ...] = ()
    elif status in MessageStatus.__members__:
        statuses = (MessageStatus(status),)
    else:
        status, statuses = OPEN_FILTER, OPEN_STATUSES
    try:
        sort = MessageSort(params.get("sort") or MessageSort.OPEN_FIRST)
    except ValueError:
        sort = MessageSort.OPEN_FIRST
    try:
        page = max(1, int(params.get("page") or 1))
    except ValueError:
        page = 1
    text = (params.get("q") or "").strip()[:100]
    received_from = _local_day_start(params.get("from") or "")
    until = _local_day_start(params.get("to") or "")
    query = MessageQuery(
        statuses=statuses,
        text=text,
        received_from=received_from,
        received_before=until + timedelta(days=1) if until else None,
        sort=sort,
        limit=PAGE_SIZE,
        offset=(page - 1) * PAGE_SIZE,
    )
    filters = {
        "status": status,
        "q": text,
        "from": received_from.date().isoformat() if received_from else "",
        "to": until.date().isoformat() if until else "",
        "sort": sort.value,
    }
    return query, filters


class AdminMessagesController(Controller):
    """All contact messages; opening one moves it from «Neu» to «In Bearbeitung»."""

    path = "/admin/messages"
    guards = [require_admin]  # noqa: RUF012 - Litestar controller attribute
    include_in_schema = False

    @get("")
    async def list_page(
        self,
        request: Request[Any, Any, Any],
        contact_service: NamedDependency[ContactService],
        theme_service: NamedDependency[ThemeService],
    ) -> Template:
        """Filtered, sorted and paged list; filters are query parameters (shareable links)."""
        query, filters = _parse_filters(request.query_params)
        return await admin_page(
            request,
            theme_service,
            "admin/messages.html",
            result=await contact_service.search_messages(query),
            counts=await contact_service.message_counts(),
            filters=filters,
            status_labels={s.value: label for s, label in STATUS_LABELS.items()},
            sort_labels={s.value: label for s, label in SORT_LABELS.items()},
        )

    @get("/{message_id:uuid}")
    async def detail_page(
        self,
        request: Request[Any, Any, Any],
        contact_service: NamedDependency[ContactService],
        theme_service: NamedDependency[ThemeService],
        message_id: FromPath[UUID],
    ) -> Template:
        """Full message, contact details, notes, history and actions."""
        actor_id, _ = current_author(request)
        detail = await contact_service.open_message(message_id, actor_id)
        return await admin_page(
            request,
            theme_service,
            "admin/message_detail.html",
            msg=detail.message,
            events=detail.events,
            # «Neu» is only the state of an unopened message, never a manual target.
            statuses=[s for s in MessageStatus if s != MessageStatus.NEW],
        )

    @post("/{message_id:uuid}/status")
    async def update_status(
        self,
        request: Request[Any, Any, Any],
        contact_service: NamedDependency[ContactService],
        message_id: FromPath[UUID],
        data: FormData,
    ) -> Redirect:
        """Set the processing status (recorded in the history)."""
        try:
            status = MessageStatus(data.get("status", ""))
        except ValueError as exc:
            raise ValidationException("Ungültiger Status.") from exc
        actor_id, _ = current_author(request)
        await contact_service.change_status(message_id, status, actor_id)
        return Redirect(path=f"/admin/messages/{message_id}", status_code=303)

    @post("/{message_id:uuid}/notes")
    async def update_notes(
        self,
        request: Request[Any, Any, Any],
        contact_service: NamedDependency[ContactService],
        message_id: FromPath[UUID],
        data: FormData,
    ) -> Redirect:
        """Save the internal notes (stored encrypted, TDR-0012)."""
        actor_id, _ = current_author(request)
        await contact_service.update_notes(message_id, data.get("notes", ""), actor_id)
        return Redirect(path=f"/admin/messages/{message_id}", status_code=303)

    @post("/{message_id:uuid}/delete")
    async def delete_message(
        self,
        contact_service: NamedDependency[ContactService],
        message_id: FromPath[UUID],
        data: FormData,
    ) -> Redirect:
        """Permanently delete the message with its history (confirmation checkbox required)."""
        if data.get("confirm") != "yes":
            raise ValidationException("Bitte das Löschen bestätigen.")
        await contact_service.delete_message(message_id)
        return Redirect(path="/admin/messages", status_code=303)

    @get("/{message_id:uuid}/export")
    async def export_sender(
        self, contact_service: NamedDependency[ContactService], message_id: FromPath[UUID]
    ) -> Response[bytes]:
        """All messages of this sender as JSON download (access request, Art. 25 DSG)."""
        exported = await contact_service.export_sender_of(message_id)
        return Response(
            content=json.dumps(exported, ensure_ascii=False, indent=2).encode(),
            media_type="application/json",
            headers={
                "Content-Disposition": 'attachment; filename="auskunft.json"',
                "Cache-Control": "no-store",
            },
        )
