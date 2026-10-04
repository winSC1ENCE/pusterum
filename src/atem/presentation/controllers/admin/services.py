"""Admin management of offerings & prices (shown in the «Angebote & Tarife» section)."""

from typing import Any
from uuid import UUID

from litestar import Controller, Request, get, post
from litestar.response import Redirect, Template
from pydantic import ValidationError

from atem.application.dto.offering import ServiceFormDTO
from atem.application.services.offering_service import OfferingService
from atem.application.services.theme_service import ThemeService
from atem.presentation.controllers.admin.common import FormData
from atem.presentation.security.admin_auth import require_admin

FORM_ERROR = (
    "Bitte prüfen Sie die Angaben: Titel (mind. 2 Zeichen), Beschreibung (mind. 10 Zeichen), "
    "Dauer 15–300 Minuten und ein gültiger Preis sind erforderlich."
)


def _parse_form(data: dict[str, str]) -> ServiceFormDTO:
    """Validate the HTML form (pydantic coerces the numeric strings)."""
    price = data.get("price_chf", "0").replace("'", "").replace(",", ".").strip() or "0"
    return ServiceFormDTO.model_validate(
        {
            "title": data.get("title", "").strip(),
            "subtitle": data.get("subtitle", "").strip(),
            "description": data.get("description", "").strip(),
            "duration_minutes": data.get("duration_minutes") or "60",
            "price_chf": price,
            "sort_order": data.get("sort_order") or "0",
            "is_active": data.get("is_active") == "on",
        }
    )


class AdminServicesController(Controller):
    """CRUD for service offerings."""

    path = "/admin/services"
    guards = [require_admin]  # noqa: RUF012 - Litestar controller attribute
    include_in_schema = False

    async def _render(
        self,
        request: Request[Any, Any, Any],
        offering_service: OfferingService,
        theme_service: ThemeService,
        **context: Any,
    ) -> Template:
        theme = await theme_service.get_active_theme()
        return Template(
            template_name="admin/services.html",
            context={
                "user": request.session.get("user"),
                "services": await offering_service.list_services(include_inactive=True),
                "theme": theme,
                "theme_css": theme_service.generate_css_variables(theme),
                "error": None,
                "saved": request.query_params.get("saved"),
                **context,
            },
        )

    @get("")
    async def services_page(
        self,
        request: Request[Any, Any, Any],
        offering_service: OfferingService,
        theme_service: ThemeService,
    ) -> Template:
        """List all offerings with edit forms."""
        return await self._render(request, offering_service, theme_service)

    @post("")
    async def create_service(
        self,
        request: Request[Any, Any, Any],
        offering_service: OfferingService,
        theme_service: ThemeService,
        data: FormData,
    ) -> Template | Redirect:
        """Create a new offering."""
        try:
            await offering_service.create_service(_parse_form(data))
        except ValidationError:
            return await self._render(
                request, offering_service, theme_service, error=FORM_ERROR, form=data
            )
        return Redirect(path="/admin/services?saved=1")

    @post("/{service_id:uuid}")
    async def update_service(
        self,
        request: Request[Any, Any, Any],
        offering_service: OfferingService,
        theme_service: ThemeService,
        service_id: UUID,
        data: FormData,
    ) -> Template | Redirect:
        """Update an existing offering."""
        try:
            await offering_service.update_service(service_id, _parse_form(data))
        except ValidationError:
            return await self._render(request, offering_service, theme_service, error=FORM_ERROR)
        return Redirect(path="/admin/services?saved=1")

    @post("/{service_id:uuid}/delete")
    async def delete_service(self, offering_service: OfferingService, service_id: UUID) -> Redirect:
        """Delete an offering."""
        await offering_service.delete_service(service_id)
        return Redirect(path="/admin/services?saved=1")
