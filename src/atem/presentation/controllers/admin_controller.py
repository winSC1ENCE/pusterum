"""Admin Controller for Content Management, Corporate Design, and Contact Inquiries."""

import contextlib
import re
import time
from pathlib import Path
from typing import Annotated, Any
from uuid import UUID

import structlog
from litestar import Controller, Request, get, post
from litestar.datastructures import UploadFile
from litestar.enums import RequestEncodingType
from litestar.exceptions import NotAuthorizedException, ValidationException
from litestar.params import Body
from litestar.response import Redirect, Response, Template

from atem.application.dto.auth import LoginRequestDTO
from atem.application.dto.content import SaveContentBlockRequestDTO
from atem.application.dto.theme import UpdateThemeRequestDTO
from atem.application.services.auth_service import AuthService
from atem.application.services.contact_service import ContactService
from atem.application.services.content_service import ContentService
from atem.application.services.profile_service import ProfileService
from atem.application.services.theme_service import ThemeService
from atem.domain.exceptions import AuthenticationException
from atem.domain.models.theme import (
    PRESET_THEMES,
    ColorPresetKey,
    DandelionEffectMode,
    ShapeType,
)

logger = structlog.get_logger(__name__)

STATIC_IMAGES_DIR = Path(__file__).resolve().parent.parent / "static" / "images"
ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".svg"}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


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
        if not request.session.get("user"):
            return Redirect(path="/admin/login")

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
        if not request.session.get("user"):
            return Redirect(path="/admin/login")

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
        if not request.session.get("user"):
            return Redirect(path="/admin/login")

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
        if not request.session.get("user"):
            return Redirect(path="/admin/login")

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
        user = request.session.get("user")
        if not user:
            raise NotAuthorizedException("Anmeldung erforderlich.")

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

        default_img_classes = {
            "about.portrait": "w-full h-full aspect-square object-cover shape-organic shadow-inner",
            "practice.interior_image": (
                "w-full h-full aspect-square object-cover shape-organic shadow-inner"
            ),
            "hero.image": (
                "relative z-10 w-64 h-64 sm:w-80 sm:h-80 md:w-96 md:h-96 object-contain"
                " filter drop-shadow-md hover:scale-105 transition-transform duration-500"
            ),
        }
        img_class = str(data.get("img_class") or default_img_classes.get(key, ""))
        img_alt = str(data.get("img_alt") or f"{key} Bild")
        tag = str(data.get("tag") or "p")
        css_class = str(data.get("css_class") or "")
        rows = int(data.get("rows", 3))

        return Template(
            template_name="admin/editable_block_single.html",
            context={
                "block": updated_block,
                "content_blocks": content_blocks,
                "is_admin": True,
                "tag": tag,
                "css_class": css_class,
                "img_alt": img_alt,
                "img_class": img_class,
                "rows": rows,
            },
        )

    @get("/content/{key:str}/history")
    async def get_content_history(
        self,
        request: Request[Any, Any, Any],
        content_service: ContentService,
        key: str,
    ) -> Template:
        """Fetch audit trail and history modal content for a content block."""
        user = request.session.get("user")
        if not user:
            raise NotAuthorizedException("Anmeldung erforderlich.")

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
        user = request.session.get("user")
        if not user:
            raise NotAuthorizedException("Anmeldung erforderlich.")

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
    async def list_images(
        self,
        request: Request[Any, Any, Any],
    ) -> list[dict[str, Any]]:
        """List all available image files in static/images directory."""
        if not request.session.get("user"):
            raise NotAuthorizedException("Anmeldung erforderlich.")

        STATIC_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
        images = []
        for file in sorted(
            STATIC_IMAGES_DIR.iterdir(),
            key=lambda p: p.stat().st_mtime if p.exists() else 0,
            reverse=True,
        ):
            if file.is_file() and file.suffix.lower() in ALLOWED_IMAGE_EXTENSIONS:
                images.append(
                    {
                        "filename": file.name,
                        "url": f"/static/images/{file.name}",
                        "size_kb": round(file.stat().st_size / 1024, 1),
                    }
                )
        return images

    @post("/images/upload")
    async def upload_image(
        self,
        request: Request[Any, Any, Any],
        data: Annotated[UploadFile, Body(media_type=RequestEncodingType.MULTI_PART)],
    ) -> dict[str, Any]:
        """Upload an image directly into the static/images directory."""
        if not request.session.get("user"):
            raise NotAuthorizedException("Anmeldung erforderlich.")

        STATIC_IMAGES_DIR.mkdir(parents=True, exist_ok=True)

        filename = data.filename or "uploaded_image.png"
        ext = Path(filename).suffix.lower()
        if ext not in ALLOWED_IMAGE_EXTENSIONS:
            raise ValidationException(
                "Ungültiges Dateiformat. Erlaubt sind: PNG, JPG, JPEG, WEBP, SVG."
            )

        content = await data.read()
        if len(content) > MAX_FILE_SIZE_BYTES:
            raise ValidationException("Die Datei überschreitet die maximale Größe von 10 MB.")

        # Sanitize base filename
        base_name = Path(filename).stem
        safe_base = re.sub(r"[^a-zA-Z0-9_-]", "_", base_name).strip("_") or "image"
        final_filename = f"{safe_base}{ext}"
        target_path = STATIC_IMAGES_DIR / final_filename

        # If file exists, append timestamp to prevent overwriting existing files
        if target_path.exists():
            final_filename = f"{safe_base}_{int(time.time())}{ext}"
            target_path = STATIC_IMAGES_DIR / final_filename

        target_path.write_bytes(content)
        logger.info("Uploaded image to static directory", filename=final_filename)

        return {
            "filename": final_filename,
            "url": f"/static/images/{final_filename}",
            "size_kb": round(len(content) / 1024, 1),
        }
