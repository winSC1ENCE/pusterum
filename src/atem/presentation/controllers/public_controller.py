"""Public Website Controller serving Landing Page, Content, and HTMX Contact Form."""

from typing import Annotated, Any

import structlog
from litestar import Controller, Request, get, post
from litestar.enums import RequestEncodingType
from litestar.params import Body
from litestar.response import Response, Template
from pydantic import ValidationError

from atem.application.dto.contact import CreateContactMessageDTO
from atem.application.services.contact_service import ContactService
from atem.application.services.content_service import ContentService
from atem.application.services.profile_service import ProfileService
from atem.application.services.theme_service import ThemeService
from atem.domain.exceptions import RateLimitedException, ValidationException
from atem.infrastructure.config.settings import Settings
from atem.presentation.security.admin_auth import load_session_user
from atem.presentation.security.form_token import issue_form_token, verify_form_token

logger = structlog.get_logger(__name__)

INVALID_INPUT = (
    "Bitte überprüfen Sie Ihre Eingaben (Name, gültige E-Mail und eine Nachricht mit "
    "mindestens 10 Zeichen sind erforderlich)."
)
FORM_TOO_FAST_OR_EXPIRED = (
    "Das Formular wurde zu schnell abgeschickt oder ist abgelaufen. Bitte erneut senden."
)
FORM_ECHO_FIELDS = frozenset({"sender_name", "sender_email", "sender_phone", "subject", "message"})


def form_token_key(settings: Settings) -> bytes:
    """Key for the signed form timing token."""
    return settings.derive_key(b"atem-contact-form-token")


class PublicController(Controller):
    """Public web pages and HTMX components."""

    path = ""

    @get("/")
    async def index(
        self,
        request: Request[Any, Any, Any],
        profile_service: ProfileService,
        theme_service: ThemeService,
        content_service: ContentService,
        settings: Settings,
    ) -> Template:
        """Render single-page breath therapy website with in-context inline editing for admins."""
        profile = await profile_service.get_public_profile()
        theme = await theme_service.get_active_theme()
        theme_css = theme_service.generate_css_variables(theme)
        content_blocks = await content_service.get_content_map()
        is_admin = await load_session_user(request) is not None

        return Template(
            template_name="pages/index.html",
            context={
                "profile": profile,
                "theme": theme,
                "theme_css": theme_css,
                "content_blocks": content_blocks,
                "is_admin": is_admin,
                "form_token": issue_form_token(form_token_key(settings)),
            },
        )

    @get("/altcha/challenge", cache=False)
    async def altcha_challenge(self, contact_service: ContactService) -> Response[dict[str, Any]]:
        """Issue a proof-of-work challenge for the contact form widget."""
        return Response(
            content=contact_service.create_captcha_challenge(),
            headers={"Cache-Control": "no-store"},
        )

    @post("/contact")
    async def handle_contact_form(
        self,
        request: Request[Any, Any, Any],
        contact_service: ContactService,
        settings: Settings,
        data: Annotated[dict[str, str], Body(media_type=RequestEncodingType.URL_ENCODED)],
    ) -> Template:
        """Handle the HTMX contact form; answers with the form card partial only."""
        error: str | None = None
        if not verify_form_token(
            form_token_key(settings),
            data.get("form_token", ""),
            min_age=settings.CONTACT_FORM_MIN_SECONDS,
        ):
            error = FORM_TOO_FAST_OR_EXPIRED
        else:
            try:
                dto = CreateContactMessageDTO(
                    sender_name=data.get("sender_name", ""),
                    sender_email=data.get("sender_email", ""),
                    sender_phone=data.get("sender_phone") or None,
                    subject=data.get("subject", "Kontaktanfrage via Website"),
                    message=data.get("message", ""),
                    honeypot=data.get("website_url") or None,
                )
                saved = await contact_service.submit_contact_form(
                    dto,
                    client_ip=request.client.host if request.client else None,
                    captcha_payload=data.get("altcha", ""),
                )
            except ValidationError:
                error = INVALID_INPUT
            except (ValidationException, RateLimitedException) as exc:
                error = exc.message
            else:
                return Template(
                    template_name="components/contact_success.html",
                    context={"contact": saved},
                )
        return Template(
            template_name="components/contact_form_card.html",
            context={
                "error": error,
                "form_data": {k: v[:5000] for k, v in data.items() if k in FORM_ECHO_FIELDS},
                "form_token": issue_form_token(form_token_key(settings)),
            },
        )

    @get("/impressum")
    async def impressum(
        self,
        request: Request[Any, Any, Any],
        profile_service: ProfileService,
        theme_service: ThemeService,
        content_service: ContentService,
    ) -> Template:
        """Render Impressum (Legal Notice)."""
        profile = await profile_service.get_public_profile()
        theme = await theme_service.get_active_theme()
        theme_css = theme_service.generate_css_variables(theme)
        content_blocks = await content_service.get_content_map()
        is_admin = await load_session_user(request) is not None

        return Template(
            template_name="pages/impressum.html",
            context={
                "profile": profile,
                "theme": theme,
                "theme_css": theme_css,
                "content_blocks": content_blocks,
                "is_admin": is_admin,
            },
        )

    @get("/datenschutz")
    async def datenschutz(
        self,
        request: Request[Any, Any, Any],
        profile_service: ProfileService,
        theme_service: ThemeService,
        content_service: ContentService,
    ) -> Template:
        """Render Privacy Policy."""
        profile = await profile_service.get_public_profile()
        theme = await theme_service.get_active_theme()
        theme_css = theme_service.generate_css_variables(theme)
        content_blocks = await content_service.get_content_map()
        is_admin = await load_session_user(request) is not None

        return Template(
            template_name="pages/datenschutz.html",
            context={
                "profile": profile,
                "theme": theme,
                "theme_css": theme_css,
                "content_blocks": content_blocks,
                "is_admin": is_admin,
            },
        )
