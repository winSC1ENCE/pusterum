"""Admin Controller for Content Management, Corporate Design, and Contact Inquiries."""

import contextlib
import re
from dataclasses import asdict
from typing import Annotated, Any
from uuid import UUID

import structlog
from litestar import Controller, Request, get, post
from litestar.datastructures import UploadFile
from litestar.enums import RequestEncodingType
from litestar.params import Body
from litestar.response import Redirect, Response, Template

from atem.application.dto.content import SaveContentBlockRequestDTO
from atem.application.dto.theme import UpdateThemeRequestDTO
from atem.application.services.contact_service import ContactService
from atem.application.services.content_service import ContentService
from atem.application.services.media_service import MediaService
from atem.application.services.profile_service import ProfileService
from atem.application.services.theme_service import ThemeService
from atem.domain.models.theme import (
    PRESET_THEMES,
    ColorPresetKey,
    DandelionEffectMode,
    ShapeType,
)
from atem.presentation.security.admin_auth import require_admin

logger = structlog.get_logger(__name__)


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


class AdminController(Controller):
    """Administration area for managing content, corporate design, and client messages."""

    path = "/admin"
    guards = [require_admin]  # noqa: RUF012 - Litestar controller attribute
    include_in_schema = False

    @get("")
    async def dashboard(
        self,
        request: Request[Any, Any, Any],
        profile_service: ProfileService,
        contact_service: ContactService,
        theme_service: ThemeService,
    ) -> Template | Redirect:
        """Render main admin dashboard."""
        profile = await profile_service.get_public_profile()
        messages = await contact_service.list_messages(limit=20)
        theme = await theme_service.get_active_theme()
        theme_css = theme_service.generate_css_variables(theme)

        return Template(
            template_name="admin/dashboard.html",
            context={
                "user": request.session["user"],
                "profile": profile,
                "messages": messages,
                "theme": theme,
                "theme_css": theme_css,
            },
        )

    @get("/design")
    async def design_studio(
        self,
        request: Request[Any, Any, Any],
        theme_service: ThemeService,
    ) -> Template | Redirect:
        """Render Corporate Design Studio in Admin Console."""
        theme = await theme_service.get_active_theme()
        theme_css = theme_service.generate_css_variables(theme)
        presets = theme_service.get_all_color_presets()
        shapes = theme_service.get_all_shapes()
        dandelion_modes = [
            {
                "key": DandelionEffectMode.DISABLED.value,
                "number": "0",
                "name": "Deaktiviert",
                "badge": "Standard / Aus",
                "description": (
                    "Vollständig statische Seite ohne Hintergrund-Partikel oder Widgets."
                ),
            },
            {
                "key": DandelionEffectMode.BREATHING_FLOW.value,
                "number": "1",
                "name": "Sanfter Atem-Drift",
                "badge": "Ambient Flow",
                "description": (
                    "5–6 zarte Vektor-Samen schweben mit 3–5% Deckkraft im 4s/6s-Atemrhythmus."
                ),
            },
            {
                "key": DandelionEffectMode.SCROLL_JOURNEY.value,
                "number": "2",
                "name": "Die Reise des Samens",
                "badge": "Scroll-Begleiter",
                "description": (
                    "Ein einzelner Samen begleitet den Besucher beim Scrollen bis zum Kontakt."
                ),
            },
            {
                "key": DandelionEffectMode.WATERMARK_ACCENTS.value,
                "number": "3",
                "name": "Wasserzeichen-Akzente",
                "badge": "Statisch & Edel",
                "description": (
                    "100% statische, feine Vektor-Wasserzeichen an Sektionsrändern & beim Zitat."
                ),
            },
            {
                "key": DandelionEffectMode.BREATH_WIDGET.value,
                "number": "4",
                "name": "Interaktive Atem-Pause",
                "badge": "Zen-Widget",
                "description": (
                    "Schwebendes Zen-Widget unten rechts zum geführten 4-4-6 Durchatmen."
                ),
            },
            {
                "key": DandelionEffectMode.WHISPER_TRAIL.value,
                "number": "5",
                "name": "Sanfter Hauch bei Bewegung",
                "badge": "Seed Whisper",
                "description": (
                    "Ephemere Samenpartikel entstehen bei sanfter Mausbewegung und verfliegen nach"
                    " 1.2s."
                ),
            },
        ]

        return Template(
            template_name="admin/design.html",
            context={
                "user": request.session["user"],
                "theme": theme,
                "theme_css": theme_css,
                "presets": presets,
                "shapes": shapes,
                "dandelion_modes": dandelion_modes,
            },
        )

    @post("/design/preset")
    async def apply_preset(
        self,
        request: Request[Any, Any, Any],
        theme_service: ThemeService,
        data: Annotated[dict[str, str], Body(media_type=RequestEncodingType.URL_ENCODED)],
    ) -> Response[bytes] | Redirect:
        """Apply one of the 5 pastel color presets."""
        preset_str = data.get("preset_key", ColorPresetKey.SALBEI_SAND.value)
        try:
            preset_key = ColorPresetKey(preset_str)
            await theme_service.set_preset(preset_key)
        except ValueError:
            logger.warning("Invalid preset key provided", key=preset_str)

        if request.headers.get("hx-request") == "true":
            return Response(content=b"", status_code=204)
        return Redirect(path="/admin/design")

    @post("/design/shape")
    async def apply_shape(
        self,
        request: Request[Any, Any, Any],
        theme_service: ThemeService,
        data: Annotated[dict[str, str], Body(media_type=RequestEncodingType.URL_ENCODED)],
    ) -> Response[bytes] | Redirect:
        """Apply one of the 5 geometric/organic shapes."""
        shape_str = data.get("shape_type", ShapeType.DANDELION_SEED.value)
        try:
            shape_type = ShapeType(shape_str)
            await theme_service.set_shape(shape_type)
        except ValueError:
            logger.warning("Invalid shape type provided", shape=shape_str)

        if request.headers.get("hx-request") == "true":
            return Response(content=b"", status_code=204)
        return Redirect(path="/admin/design")

    @staticmethod
    def _extract_dandelion_modes(data: dict[str, Any]) -> list[DandelionEffectMode]:
        modes_input = data.get("dandelion_modes") or data.get("dandelion_mode")
        raw_list: list[str] = []
        if isinstance(modes_input, list):
            raw_list = [str(item) for item in modes_input]
        elif isinstance(modes_input, str):
            raw_list = [p.strip() for p in modes_input.split(",") if p.strip()]

        parsed: list[DandelionEffectMode] = []
        for m_str in raw_list:
            with contextlib.suppress(ValueError):
                parsed.append(DandelionEffectMode(m_str))

        if not parsed or (DandelionEffectMode.DISABLED in parsed and len(parsed) == 1):
            return [DandelionEffectMode.DISABLED]
        return [m for m in parsed if m != DandelionEffectMode.DISABLED]

    @post("/design/dandelion")
    async def apply_dandelion_mode(
        self,
        request: Request[Any, Any, Any],
        theme_service: ThemeService,
        data: Annotated[dict[str, Any], Body(media_type=RequestEncodingType.URL_ENCODED)],
    ) -> Response[bytes] | Redirect:
        """Apply ambient dandelion effect multi-select modes and slider settings."""
        current_theme = await theme_service.get_active_theme()
        parsed_modes = self._extract_dandelion_modes(data)

        try:
            seed_size = int(data.get("dandelion_seed_size", str(current_theme.dandelion_seed_size)))
        except ValueError:
            seed_size = current_theme.dandelion_seed_size

        try:
            seed_opacity = int(
                data.get("dandelion_seed_opacity", str(current_theme.dandelion_seed_opacity))
            )
        except ValueError:
            seed_opacity = current_theme.dandelion_seed_opacity

        await theme_service.apply_dandelion_modes(
            modes=parsed_modes,
            seed_size=seed_size,
            seed_opacity=seed_opacity,
        )

        if request.headers.get("hx-request") == "true":
            return Response(content=b"", status_code=204)
        return Redirect(path="/admin/design")

    @post("/design/custom")
    async def apply_custom_theme(
        self,
        request: Request[Any, Any, Any],
        theme_service: ThemeService,
        data: Annotated[dict[str, str], Body(media_type=RequestEncodingType.URL_ENCODED)],
    ) -> Response[bytes] | Redirect:
        """Save custom colors and typography while preserving active shapes and modes."""
        current_theme = await theme_service.get_active_theme()

        active_shape_str = data.get("active_shape", current_theme.active_shape.value)
        try:
            shape_type = ShapeType(active_shape_str)
        except ValueError:
            shape_type = current_theme.active_shape

        dandelion_mode_str = data.get("dandelion_mode", current_theme.dandelion_mode.value)
        try:
            dandelion_mode = DandelionEffectMode(dandelion_mode_str)
        except ValueError:
            dandelion_mode = current_theme.dandelion_mode

        try:
            seed_size = int(data.get("dandelion_seed_size", str(current_theme.dandelion_seed_size)))
        except ValueError:
            seed_size = current_theme.dandelion_seed_size

        try:
            seed_opacity = int(
                data.get("dandelion_seed_opacity", str(current_theme.dandelion_seed_opacity))
            )
        except ValueError:
            seed_opacity = current_theme.dandelion_seed_opacity

        primary = data.get("primary_color", current_theme.primary_color)
        secondary = data.get("secondary_color", current_theme.secondary_color)
        accent = data.get("accent_color", current_theme.accent_color)
        background = data.get("background_color", current_theme.background_color)
        surface = data.get("surface_color", current_theme.surface_color)
        border = data.get("border_color", current_theme.border_color)

        # Detect if colors match current preset or any predefined pastel preset
        active_palette = PRESET_THEMES.get(current_theme.preset_key)
        if active_palette and (
            primary.lower() == active_palette.primary.lower()
            and secondary.lower() == active_palette.secondary.lower()
            and accent.lower() == active_palette.accent.lower()
            and background.lower() == active_palette.background.lower()
            and surface.lower() == active_palette.surface.lower()
            and border.lower() == active_palette.border_color.lower()
        ):
            determined_preset = current_theme.preset_key
        else:
            matched_preset = None
            for p_key, p_val in PRESET_THEMES.items():
                if (
                    primary.lower() == p_val.primary.lower()
                    and secondary.lower() == p_val.secondary.lower()
                    and accent.lower() == p_val.accent.lower()
                    and background.lower() == p_val.background.lower()
                    and surface.lower() == p_val.surface.lower()
                    and border.lower() == p_val.border_color.lower()
                ):
                    matched_preset = p_key
                    break
            determined_preset = matched_preset if matched_preset else ColorPresetKey.CUSTOM

        dto = UpdateThemeRequestDTO(
            preset_key=determined_preset,
            primary_color=primary,
            primary_hover=data.get("primary_hover") or current_theme.primary_hover,
            secondary_color=secondary,
            accent_color=accent,
            background_color=background,
            surface_color=surface,
            surface_muted=data.get("surface_muted", current_theme.surface_muted),
            text_main_color=data.get("text_main_color", current_theme.text_main_color),
            text_muted_color=data.get("text_muted_color", current_theme.text_muted_color),
            border_color=border,
            heading_font=data.get("heading_font", current_theme.heading_font),
            body_font=data.get("body_font", current_theme.body_font),
            active_shape=shape_type,
            motif_enabled=current_theme.motif_enabled,
            motif_animation_speed=current_theme.motif_animation_speed,
            dandelion_mode=dandelion_mode,
            dandelion_seed_size=seed_size,
            dandelion_seed_opacity=seed_opacity,
        )
        await theme_service.update_theme(dto)

        if request.headers.get("hx-request") == "true":
            return Response(content=b"", status_code=204)
        return Redirect(path="/admin/design")

    # =========================================================================
    # LIVE IN-CONTEXT CONTENT EDITING & VERSIONING (ADR-0002)
    # =========================================================================
    @post("/content/{key:str}/save")
    async def save_content_block(
        self,
        request: Request[Any, Any, Any],
        content_service: ContentService,
        key: str,
    ) -> Template:
        """Save a new content block version from inline editor or media manager."""
        user = request.session["user"]
        content_type = request.headers.get("content-type", "")
        data: dict[str, Any] = {}
        if "application/json" in content_type:
            data = await request.json()
        else:
            try:
                form_data = await request.form()
                data = dict(form_data)
            except Exception:
                try:
                    data = await request.json()
                except Exception:
                    data = {}

        user_id_str = user.get("id")
        user_id = UUID(user_id_str) if user_id_str else None
        username = user.get("username", "Admin")

        content_val = str(data.get("content", "")).strip()
        change_summary = str(data.get("change_summary") or "In-Context Editierung")

        dto = SaveContentBlockRequestDTO(
            content=content_val,
            change_summary=change_summary,
        )
        updated_block = await content_service.save_block_content(
            key=key,
            dto=dto,
            author_name=username,
            author_id=user_id,
        )
        content_blocks = await content_service.get_content_map()

        return Template(
            template_name="admin/editable_block_single.html",
            context={
                **render_hints(data, key),
                "block": updated_block,
                "content_blocks": content_blocks,
                "is_admin": True,
            },
        )

    @get("/content/{key:str}/history")
    async def get_content_history(
        self,
        content_service: ContentService,
        key: str,
    ) -> Template:
        """Fetch audit trail and history modal content for a content block."""
        history = await content_service.get_block_history(key)
        return Template(
            template_name="admin/version_history_modal_content.html",
            context={
                "history": history,
            },
        )

    @post("/content/{key:str}/restore/{version_number:int}")
    async def restore_content_version(
        self,
        request: Request[Any, Any, Any],
        content_service: ContentService,
        key: str,
        version_number: int,
    ) -> Template:
        """Restore an older version as the next version number and return updated fragment."""
        user = request.session["user"]
        user_id_str = user.get("id")
        user_id = UUID(user_id_str) if user_id_str else None
        username = user.get("username", "Admin")

        updated_block = await content_service.restore_block_version(
            key=key,
            target_version_number=version_number,
            author_name=username,
            author_id=user_id,
        )
        content_blocks = await content_service.get_content_map()

        return Template(
            template_name="admin/editable_block_single.html",
            context={
                "block": updated_block,
                "content_blocks": content_blocks,
                "is_admin": True,
                "tag": "p",
                "css_class": "",
                "img_alt": "",
                "img_class": "",
                "rows": 3,
            },
        )

    @get("/images/list")
    async def list_images(self, media_service: MediaService) -> list[dict[str, Any]]:
        """List uploaded images and bundled theme images for the image picker."""
        return [asdict(item) for item in media_service.list_images()]

    @post("/images/upload")
    async def upload_image(
        self,
        media_service: MediaService,
        data: Annotated[UploadFile, Body(media_type=RequestEncodingType.MULTI_PART)],
    ) -> dict[str, Any]:
        """Upload an image: content is verified and re-encoded (no SVG, no metadata)."""
        raw = await data.read()
        return asdict(media_service.store_upload(raw))
