"""Live in-context content editing and version history (ADR-0002)."""

import re
from typing import Any

from litestar import Controller, Request, get, post
from litestar.di import NamedDependency
from litestar.params import FromPath
from litestar.response import Template

from atem.application.dto.content import SaveContentBlockRequestDTO
from atem.application.services.content_service import ContentService
from atem.presentation.controllers.admin.common import current_author, is_htmx
from atem.presentation.security.admin_auth import require_admin

# Render hints are echoed back by the inline editor; only safe values are accepted.
ALLOWED_TAGS = frozenset({"p", "span", "div", "h1", "h2", "h3", "h4", "blockquote", "figcaption"})
CSS_CLASS_RE = re.compile(r"^[A-Za-z0-9_:/\-\[\]\.%!#() ]{0,600}$")
MAX_ROWS = 20
MAX_ALT_LENGTH = 200


def render_hints(data: dict[str, Any], key: str) -> dict[str, Any]:
    """Sanitise the render hints (tag, classes, alt text, rows) posted by the inline editor."""
    tag = str(data.get("tag") or "p")
    css_class = str(data.get("css_class") or "")
    img_class = str(data.get("img_class") or "")
    try:
        rows = int(str(data.get("rows", 3)))
    except ValueError:
        rows = 3
    return {
        "tag": tag if tag in ALLOWED_TAGS else "p",
        "css_class": css_class if CSS_CLASS_RE.fullmatch(css_class) else "",
        "img_class": img_class if CSS_CLASS_RE.fullmatch(img_class) else "",
        "img_alt": str(data.get("img_alt") or f"{key} Bild")[:MAX_ALT_LENGTH],
        "rows": min(max(rows, 1), MAX_ROWS),
    }


async def _request_data(request: Request[Any, Any, Any]) -> dict[str, Any]:
    """Inline editor posts a form; the image picker posts multipart form data."""
    if "application/json" in request.headers.get("content-type", ""):
        payload = await request.json()
        return payload if isinstance(payload, dict) else {}
    return dict(await request.form())


class AdminContentController(Controller):
    """Save, inspect and restore content block versions."""

    path = "/admin/content"
    guards = [require_admin]  # noqa: RUF012 - Litestar controller attribute
    include_in_schema = False

    @post("/{key:str}/save")
    async def save_content_block(
        self,
        request: Request[Any, Any, Any],
        content_service: NamedDependency[ContentService],
        key: FromPath[str],
    ) -> Template:
        """Save a new version and return the re-rendered editable block."""
        data = await _request_data(request)
        author_id, author_name = current_author(request)
        block = await content_service.save_block_content(
            key=key,
            dto=SaveContentBlockRequestDTO(
                content=str(data.get("content", "")),
                change_summary=str(data.get("change_summary") or "In-Context Editierung")[:255],
            ),
            author_name=author_name,
            author_id=author_id,
        )
        return Template(
            template_name="admin/editable_block_single.html",
            context={
                **render_hints(data, key),
                "block": block,
                "content_blocks": await content_service.get_content_map(),
                "is_admin": True,
            },
        )

    @get("/{key:str}/history")
    async def get_content_history(
        self, content_service: NamedDependency[ContentService], key: FromPath[str]
    ) -> Template:
        """Version history (audit trail) for the history modal."""
        return Template(
            template_name="admin/version_history_modal_content.html",
            context={"history": await content_service.get_block_history(key)},
        )

    @post("/{key:str}/restore/{version_number:int}")
    async def restore_content_version(
        self,
        request: Request[Any, Any, Any],
        content_service: NamedDependency[ContentService],
        key: FromPath[str],
        version_number: FromPath[int],
    ) -> Template:
        """Restore an older version as the newest one.

        The page reloads afterwards (HX-Refresh) so the block is rendered with its original
        tag and classes – the history modal does not know the block's render hints.
        """
        author_id, author_name = current_author(request)
        block = await content_service.restore_block_version(
            key=key,
            target_version_number=version_number,
            author_name=author_name,
            author_id=author_id,
        )
        return Template(
            template_name="admin/editable_block_single.html",
            context={
                **render_hints({}, key),
                "block": block,
                "content_blocks": await content_service.get_content_map(),
                "is_admin": True,
            },
            headers={"HX-Refresh": "true"} if is_htmx(request) else None,
        )
