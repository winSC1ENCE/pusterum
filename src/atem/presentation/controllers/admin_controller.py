"""Admin Controller for Content Management and Contact Inquiries."""

from typing import Annotated, Any

import structlog
from litestar import Controller, Request, get, post
from litestar.enums import RequestEncodingType
from litestar.params import Body
from litestar.response import Redirect, Template

from atem.application.dto.auth import LoginRequestDTO
from atem.application.services.auth_service import AuthService
from atem.application.services.contact_service import ContactService
from atem.application.services.profile_service import ProfileService
from atem.domain.exceptions import AuthenticationException

logger = structlog.get_logger(__name__)


class AdminController(Controller):
    """Administration area for managing content and client messages."""

    path = "/admin"

    @get("/login")
    async def login_page(self, request: Request[Any, Any, Any]) -> Template | Redirect:
        """Render login form."""
        if request.session.get("user"):
            return Redirect(path="/admin")
        return Template(template_name="admin/login.html", context={"error": None})

    @post("/login")
    async def process_login(
        self,
        request: Request[Any, Any, Any],
        auth_service: AuthService,
        data: Annotated[dict[str, str], Body(media_type=RequestEncodingType.URL_ENCODED)],
    ) -> Template | Redirect:
        """Process login credentials."""
        username = data.get("username", "")
        password = data.get("password", "")

        try:
            dto = LoginRequestDTO(username=username, password=password)
            user = await auth_service.authenticate(dto)
            request.session["user"] = {
                "id": str(user.id),
                "username": user.username,
                "role": user.role.value,
            }
            return Redirect(path="/admin")
        except AuthenticationException as exc:
            return Template(
                template_name="admin/login.html",
                context={"error": exc.message, "username": username},
            )

    @get("/logout")
    async def logout(self, request: Request[Any, Any, Any]) -> Redirect:
        """Clear admin session."""
        request.session.clear()
        return Redirect(path="/admin/login")

    @get("")
    async def dashboard(
        self,
        request: Request[Any, Any, Any],
        profile_service: ProfileService,
        contact_service: ContactService,
    ) -> Template | Redirect:
        """Render main admin dashboard."""
        if not request.session.get("user"):
            return Redirect(path="/admin/login")

        profile = await profile_service.get_public_profile()
        messages = await contact_service.list_messages(limit=20)

        return Template(
            template_name="admin/dashboard.html",
            context={
                "user": request.session["user"],
                "profile": profile,
                "messages": messages,
            },
        )
