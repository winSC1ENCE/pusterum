"""Admin dashboard: overview and contact message management."""

from typing import Any
from uuid import UUID

from litestar import Controller, Request, get, post
from litestar.di import NamedDependency
from litestar.params import FromPath
from litestar.response import Response, Template

from atem.application.services.contact_service import ContactService
from atem.application.services.offering_service import OfferingService
from atem.application.services.theme_service import ThemeService
from atem.domain.exceptions import ValidationException
from atem.domain.models.contact import MessageStatus
from atem.presentation.controllers.admin.common import FormData, admin_page
from atem.presentation.security.admin_auth import require_admin


class AdminDashboardController(Controller):
    """Dashboard with the latest inquiries."""

    path = "/admin"
    guards = [require_admin]  # noqa: RUF012 - Litestar controller attribute
    include_in_schema = False

    @get("")
    async def dashboard(
        self,
        request: Request[Any, Any, Any],
        offering_service: NamedDependency[OfferingService],
        contact_service: NamedDependency[ContactService],
        theme_service: NamedDependency[ThemeService],
    ) -> Template:
        """Overview: offerings and the latest contact messages."""
        return await admin_page(
            request,
            theme_service,
            "admin/dashboard.html",
            services=await offering_service.list_services(),
            messages=await contact_service.list_messages(limit=50),
            # Counted in the database: the table shows only the newest 50
            message_counts=await contact_service.message_counts(),
        )

    @post("/messages/{message_id:uuid}/status")
    async def update_message_status(
        self,
        contact_service: NamedDependency[ContactService],
        message_id: FromPath[UUID],
        data: FormData,
    ) -> Template:
        """Change the processing status of an inquiry (HTMX, returns the table row)."""
        try:
            status = MessageStatus(data.get("status", ""))
        except ValueError as exc:
            raise ValidationException("Ungültiger Status.") from exc
        message = await contact_service.update_message_status(message_id, status)
        return Template(template_name="admin/message_row.html", context={"msg": message})

    @post("/messages/{message_id:uuid}/delete")
    async def delete_message(
        self, contact_service: NamedDependency[ContactService], message_id: FromPath[UUID]
    ) -> Response[bytes]:
        """Permanently delete an inquiry (HTMX removes the row)."""
        await contact_service.delete_message(message_id)
        return Response(content=b"", status_code=200)
