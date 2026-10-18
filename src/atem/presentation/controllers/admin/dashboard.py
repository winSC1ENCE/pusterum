"""Admin dashboard: overview with the open contact messages."""

from typing import Any

from litestar import Controller, Request, get
from litestar.di import NamedDependency
from litestar.response import Template

from atem.application.services.contact_service import ContactService
from atem.application.services.offering_service import OfferingService
from atem.application.services.theme_service import ThemeService
from atem.domain.models.contact import OPEN_STATUSES, MessageQuery
from atem.presentation.controllers.admin.common import admin_page
from atem.presentation.security.admin_auth import require_admin

# Newest open messages on the dashboard; the full list is /admin/messages.
DASHBOARD_MESSAGES = 5


class AdminDashboardController(Controller):
    """Dashboard with the open inquiries."""

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
        """Overview: offerings and the newest open contact messages."""
        return await admin_page(
            request,
            theme_service,
            "admin/dashboard.html",
            services=await offering_service.list_services(),
            open_messages=await contact_service.search_messages(
                MessageQuery(statuses=OPEN_STATUSES, limit=DASHBOARD_MESSAGES)
            ),
            message_counts=await contact_service.message_counts(),
        )
