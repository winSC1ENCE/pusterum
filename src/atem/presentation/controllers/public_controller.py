"""Public Website Controller serving Landing Page, Content, and HTMX Contact Form."""

from typing import Annotated, Any

import structlog
from litestar import Controller, Request, get, post
from litestar.enums import RequestEncodingType
from litestar.params import Body
from litestar.response import Template
from pydantic import ValidationError

from atem.application.dto.contact import CreateContactMessageDTO
from atem.application.services.contact_service import ContactService
from atem.application.services.profile_service import ProfileService
from atem.domain.exceptions import ValidationException

logger = structlog.get_logger(__name__)


class PublicController(Controller):
    """Public web pages and HTMX components."""

    path = ""

    @get("/")
    async def index(self, profile_service: ProfileService) -> Template:
        """Render single-page breath therapy website."""
        profile = await profile_service.get_public_profile()
        return Template(
            template_name="pages/index.html",
            context={"profile": profile},
        )

    @post("/contact")
    async def handle_contact_form(
        self,
        request: Request[Any, Any, Any],
        contact_service: ContactService,
        data: Annotated[dict[str, str], Body(media_type=RequestEncodingType.URL_ENCODED)],
    ) -> Template:
        """Handle HTMX / HTML contact form submission."""
        client_ip = request.client.host if request.client else None

        try:
            dto = CreateContactMessageDTO(
                sender_name=data.get("sender_name", ""),
                sender_email=data.get("sender_email", ""),
                sender_phone=data.get("sender_phone") or None,
                subject=data.get("subject", "Kontaktanfrage via Website"),
                message=data.get("message", ""),
                honeypot=data.get("website_url") or None,  # Honeypot input
            )
            saved = await contact_service.submit_contact_form(dto, client_ip=client_ip)
            return Template(
                template_name="components/contact_success.html",
                context={"contact": saved},
            )
        except (ValidationError, ValidationException) as exc:
            error_msg = (
                "Bitte überprüfen Sie Ihre Eingaben (Name, gültige E-Mail und Nachricht "
                "sind erforderlich)."
            )
            if isinstance(exc, ValidationException):
                error_msg = exc.message
            return Template(
                template_name="components/contact_form.html",
                context={
                    "error": error_msg,
                    "form_data": data,
                },
            )

    @get("/impressum")
    async def impressum(self, profile_service: ProfileService) -> Template:
        """Render Impressum (Legal Notice)."""
        profile = await profile_service.get_public_profile()
        return Template(
            template_name="pages/impressum.html",
            context={"profile": profile},
        )

    @get("/datenschutz")
    async def datenschutz(self, profile_service: ProfileService) -> Template:
        """Render Privacy Policy."""
        profile = await profile_service.get_public_profile()
        return Template(
            template_name="pages/datenschutz.html",
            context={"profile": profile},
        )
