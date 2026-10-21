"""Corporate Design Studio: colour presets, shapes, ambient effects, custom theme."""

from typing import Any

import structlog
from litestar import Controller, Request, get, post
from litestar.di import NamedDependency
from litestar.response import Redirect, Response, Template

from atem.application.dto.theme import UpdateThemeRequestDTO
from atem.application.services.theme_service import ThemeService
from atem.domain.models.theme import (
    HEADER_OPACITY_MAX,
    HEADER_OPACITY_MIN,
    ColorPresetKey,
    DandelionEffectMode,
    PageSection,
    ShapeType,
    find_matching_preset,
)
from atem.presentation.controllers.admin.common import (
    FormData,
    admin_page,
    htmx_or_redirect,
    is_htmx,
    parse_int,
)
from atem.presentation.security.admin_auth import require_admin

logger = structlog.get_logger(__name__)
DESIGN_PATH = "/admin/design"
SECTION_MOVES = {"up": -1, "down": 1}
CUSTOM_COLOR_FIELDS = (
    "primary_color",
    "secondary_color",
    "accent_color",
    "background_color",
    "surface_color",
    "surface_muted",
    "text_main_color",
    "text_muted_color",
    "border_color",
)


class AdminDesignController(Controller):
    """Design studio – changes are saved immediately (HTMX autosave)."""

    path = DESIGN_PATH
    guards = [require_admin]  # noqa: RUF012 - Litestar controller attribute
    include_in_schema = False

    @get("")
    async def design_studio(
        self, request: Request[Any, Any, Any], theme_service: NamedDependency[ThemeService]
    ) -> Template:
        """Render the design studio."""
        return await admin_page(
            request,
            theme_service,
            "admin/design.html",
            presets=theme_service.get_all_color_presets(),
            shapes=theme_service.get_all_shapes(),
            dandelion_modes=theme_service.get_dandelion_modes(),
        )

    @post("/sections")
    async def move_section(
        self,
        request: Request[Any, Any, Any],
        theme_service: NamedDependency[ThemeService],
        data: FormData,
    ) -> Template | Redirect:
        """Move one start-page section up or down (order of the public page and navigation).

        HTMX gets only the re-rendered card, so the page neither reloads nor scrolls.
        """
        try:
            section = PageSection(data.get("section", ""))
            offset = SECTION_MOVES[data.get("direction", "")]
        except (ValueError, KeyError):
            logger.warning("invalid_section_move")
        else:
            await theme_service.move_section(section, offset)
        if is_htmx(request):
            theme = await theme_service.get_active_theme()
            return Template(template_name="admin/section_order_card.html", context={"theme": theme})
        return Redirect(path=f"{DESIGN_PATH}#section-order")

    @post("/preset")
    async def apply_preset(
        self,
        request: Request[Any, Any, Any],
        theme_service: NamedDependency[ThemeService],
        data: FormData,
    ) -> Response[bytes] | Redirect:
        """Apply one of the pastel colour presets."""
        try:
            await theme_service.set_preset(ColorPresetKey(data.get("preset_key", "")))
        except ValueError:
            logger.warning("invalid_preset_key")
        return htmx_or_redirect(request, DESIGN_PATH)

    @post("/shape")
    async def apply_shape(
        self,
        request: Request[Any, Any, Any],
        theme_service: NamedDependency[ThemeService],
        data: FormData,
    ) -> Response[bytes] | Redirect:
        """Apply one of the organic shapes."""
        try:
            await theme_service.set_shape(ShapeType(data.get("shape_type", "")))
        except ValueError:
            logger.warning("invalid_shape_type")
        return htmx_or_redirect(request, DESIGN_PATH)

    @post("/dandelion")
    async def apply_dandelion_modes(
        self,
        request: Request[Any, Any, Any],
        theme_service: NamedDependency[ThemeService],
        data: FormData,
    ) -> Response[bytes] | Redirect:
        """Apply the multi-select ambient modes and the seed sliders."""
        current = await theme_service.get_active_theme()
        await theme_service.apply_dandelion_modes(
            modes=DandelionEffectMode.parse_many(
                data.get("dandelion_modes") or data.get("dandelion_mode")
            ),
            seed_size=parse_int(data, "dandelion_seed_size", current.dandelion_seed_size),
            seed_opacity=parse_int(data, "dandelion_seed_opacity", current.dandelion_seed_opacity),
            kids_photo_opacity=parse_int(data, "kids_photo_opacity", current.kids_photo_opacity),
        )
        return htmx_or_redirect(request, DESIGN_PATH)

    @post("/custom")
    async def apply_custom_theme(
        self,
        request: Request[Any, Any, Any],
        theme_service: NamedDependency[ThemeService],
        data: FormData,
    ) -> Response[bytes] | Redirect:
        """Save custom colours and typography; shape and ambient modes are preserved."""
        current = await theme_service.get_active_theme()
        colors = {name: data.get(name) or getattr(current, name) for name in CUSTOM_COLOR_FIELDS}
        try:
            shape = ShapeType(data.get("active_shape", current.active_shape.value))
        except ValueError:
            shape = current.active_shape
        dto = UpdateThemeRequestDTO.model_validate(
            {
                **colors,
                "preset_key": find_matching_preset(colors, current.preset_key),
                "primary_hover": data.get("primary_hover") or current.primary_hover,
                "heading_font": data.get("heading_font", current.heading_font),
                "body_font": data.get("body_font", current.body_font),
                "active_shape": shape,
                # BUG-02: keep every selected ambient mode
                "dandelion_modes": DandelionEffectMode.parse_many(data.get("dandelion_mode"))
                if data.get("dandelion_mode")
                else current.dandelion_modes,
                "dandelion_seed_size": parse_int(
                    data, "dandelion_seed_size", current.dandelion_seed_size
                ),
                "dandelion_seed_opacity": parse_int(
                    data, "dandelion_seed_opacity", current.dandelion_seed_opacity
                ),
                "kids_photo_opacity": parse_int(
                    data, "kids_photo_opacity", current.kids_photo_opacity
                ),
                # Unchecked boxes are not submitted; the marker says the field was in the form
                "show_phone": data.get("show_phone") == "1"
                if data.get("show_phone_field")
                else current.show_phone,
                "header_opacity": min(
                    max(
                        parse_int(data, "header_opacity", current.header_opacity),
                        HEADER_OPACITY_MIN,
                    ),
                    HEADER_OPACITY_MAX,
                ),
            }
        )
        await theme_service.update_theme(dto)
        return htmx_or_redirect(request, DESIGN_PATH)
