"""Shared helpers for admin controllers."""

from typing import Annotated, Any
from uuid import UUID

from litestar import Request
from litestar.enums import RequestEncodingType
from litestar.params import Body
from litestar.response import Redirect, Response, Template

from atem.application.services.theme_service import ThemeService

FormData = Annotated[dict[str, str], Body(media_type=RequestEncodingType.URL_ENCODED)]


def is_htmx(request: Request[Any, Any, Any]) -> bool:
    """True for requests sent by HTMX."""
    return request.headers.get("hx-request") == "true"


def htmx_or_redirect(request: Request[Any, Any, Any], path: str) -> Response[bytes] | Redirect:
    """HTMX autosave → 204 (no swap); classic form post → redirect back."""
    if is_htmx(request):
        return Response(content=b"", status_code=204)
    return Redirect(path=path)


def parse_int(data: dict[str, Any], key: str, default: int) -> int:
    """Integer form field with fallback for missing/invalid input."""
    try:
        return int(str(data.get(key, default)))
    except ValueError:
        return default


def current_author(request: Request[Any, Any, Any]) -> tuple[UUID | None, str]:
    """(user id, display name) of the logged-in admin for audit/version records."""
    user = request.session.get("user") or {}
    raw_id = user.get("id")
    return (UUID(raw_id) if raw_id else None, str(user.get("email") or "Admin"))


async def admin_page(
    request: Request[Any, Any, Any],
    theme_service: ThemeService,
    template_name: str,
    **context: Any,
) -> Template:
    """Render an admin page with the active theme and the session user."""
    theme = await theme_service.get_active_theme()
    return Template(
        template_name=template_name,
        context={
            "user": request.session.get("user"),
            "theme": theme,
            "theme_css": theme_service.generate_css_variables(theme),
            **context,
        },
    )
