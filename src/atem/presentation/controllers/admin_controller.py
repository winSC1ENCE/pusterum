"""Admin Controller for Content Management, Corporate Design, and Contact Inquiries."""

from typing import Annotated, Any

import structlog
from litestar import Controller, Request, get, post
from litestar.enums import RequestEncodingType
from litestar.params import Body
from litestar.response import Redirect, Template

from atem.application.dto.auth import LoginRequestDTO
from atem.application.dto.theme import UpdateThemeRequestDTO
from atem.application.services.auth_service import AuthService
from atem.application.services.contact_service import ContactService
from atem.application.services.profile_service import ProfileService
from atem.application.services.theme_service import ThemeService
from atem.domain.exceptions import AuthenticationException
from atem.domain.models.theme import ColorPresetKey, ShapeType

logger = structlog.get_logger(__name__)


class AdminController(Controller):
    """Administration area for managing content, corporate design, and client messages."""

    path = "/admin"

    @get("/login")
    async def login_page(
        self,
        request: Request[Any, Any, Any],
        theme_service: ThemeService,
    ) -> Template | Redirect:
        """Render login form."""
        if request.session.get("user"):
            return Redirect(path="/admin")
        theme = await theme_service.get_active_theme()
        theme_css = theme_service.generate_css_variables(theme)
        return Template(
            template_name="admin/login.html",
            context={"error": None, "theme": theme, "theme_css": theme_css},
        )

    @post("/login")
    async def process_login(
        self,
        request: Request[Any, Any, Any],
        auth_service: AuthService,
        theme_service: ThemeService,
        data: Annotated[dict[str, str], Body(media_type=RequestEncodingType.URL_ENCODED)],
    ) -> Template | Redirect:
        """Process login credentials."""
        username = data.get("username", "")
        password = data.get("password", "")
        theme = await theme_service.get_active_theme()
        theme_css = theme_service.generate_css_variables(theme)

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
                context={
                    "error": exc.message,
                    "username": username,
                    "theme": theme,
                    "theme_css": theme_css,
                },
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
        theme_service: ThemeService,
    ) -> Template | Redirect:
        """Render main admin dashboard."""
        if not request.session.get("user"):
            return Redirect(path="/admin/login")

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
        if not request.session.get("user"):
            return Redirect(path="/admin/login")

        theme = await theme_service.get_active_theme()
        theme_css = theme_service.generate_css_variables(theme)
        presets = theme_service.get_all_color_presets()
        shapes = theme_service.get_all_shapes()

        return Template(
            template_name="admin/design.html",
            context={
                "user": request.session["user"],
                "theme": theme,
                "theme_css": theme_css,
                "presets": presets,
                "shapes": shapes,
            },
        )

    @post("/design/preset")
    async def apply_preset(
        self,
        request: Request[Any, Any, Any],
        theme_service: ThemeService,
        data: Annotated[dict[str, str], Body(media_type=RequestEncodingType.URL_ENCODED)],
    ) -> Redirect:
        """Apply one of the 5 pastel color presets."""
        if not request.session.get("user"):
            return Redirect(path="/admin/login")

        preset_str = data.get("preset_key", ColorPresetKey.SALBEI_SAND.value)
        try:
            preset_key = ColorPresetKey(preset_str)
            await theme_service.set_preset(preset_key)
        except ValueError:
            logger.warning("Invalid preset key provided", key=preset_str)

        return Redirect(path="/admin/design")

    @post("/design/shape")
    async def apply_shape(
        self,
        request: Request[Any, Any, Any],
        theme_service: ThemeService,
        data: Annotated[dict[str, str], Body(media_type=RequestEncodingType.URL_ENCODED)],
    ) -> Redirect:
        """Apply one of the 5 geometric/organic shapes."""
        if not request.session.get("user"):
            return Redirect(path="/admin/login")

        shape_str = data.get("shape_type", ShapeType.DANDELION_SEED.value)
        try:
            shape_type = ShapeType(shape_str)
            await theme_service.set_shape(shape_type)
        except ValueError:
            logger.warning("Invalid shape type provided", shape=shape_str)

        return Redirect(path="/admin/design")

    @post("/design/custom")
    async def apply_custom_theme(
        self,
        request: Request[Any, Any, Any],
        theme_service: ThemeService,
        data: Annotated[dict[str, str], Body(media_type=RequestEncodingType.URL_ENCODED)],
    ) -> Redirect:
        """Save custom colors and typography."""
        if not request.session.get("user"):
            return Redirect(path="/admin/login")

        active_shape_str = data.get("active_shape", ShapeType.DANDELION_SEED.value)
        try:
            shape_type = ShapeType(active_shape_str)
        except ValueError:
            shape_type = ShapeType.DANDELION_SEED

        dto = UpdateThemeRequestDTO(
            preset_key=ColorPresetKey.CUSTOM,
            primary_color=data.get("primary_color", "#4A6C50"),
            primary_hover=data.get("primary_hover") or None,
            secondary_color=data.get("secondary_color", "#CEDECF"),
            accent_color=data.get("accent_color", "#7FA485"),
            background_color=data.get("background_color", "#FAF8F5"),
            surface_color=data.get("surface_color", "#FFFFFF"),
            surface_muted=data.get("surface_muted", "#F3EFE8"),
            text_main_color=data.get("text_main_color", "#1E293B"),
            text_muted_color=data.get("text_muted_color", "#64748B"),
            border_color=data.get("border_color", "#E6DED1"),
            heading_font=data.get("heading_font", "Lora"),
            body_font=data.get("body_font", "Plus Jakarta Sans"),
            active_shape=shape_type,
            motif_enabled=data.get("motif_enabled") == "true" or data.get("motif_enabled") == "on",
            motif_animation_speed=data.get("motif_animation_speed", "normal"),
        )
        await theme_service.update_theme(dto)
        return Redirect(path="/admin/design")
