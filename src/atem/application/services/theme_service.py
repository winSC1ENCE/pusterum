"""Theme Application Service."""

import structlog

from atem.application.dto.theme import (
    ColorPaletteDTO,
    ShapeDefinitionDTO,
    ThemeConfigDTO,
    UpdateThemeRequestDTO,
)
from atem.domain.interfaces.theme_repository import IThemeRepository
from atem.domain.models.theme import (
    DANDELION_MODE_DEFINITIONS,
    HEADER_OPACITY_MAX,
    HEADER_OPACITY_MIN,
    KIDS_PHOTO_OPACITY_MAX,
    KIDS_PHOTO_OPACITY_MIN,
    PRESET_SHAPES,
    PRESET_THEMES,
    SEED_OPACITY_MAX,
    SEED_OPACITY_MIN,
    SEED_SIZE_MAX,
    SEED_SIZE_MIN,
    ColorPresetKey,
    DandelionEffectMode,
    DandelionModeDefinition,
    FontFamily,
    ShapeType,
    ThemeConfig,
    hex_to_rgb_channels,
    is_hex_color,
)

logger = structlog.get_logger(__name__)


class ThemeService:
    """Application service for managing Corporate Design, Color Themes, and Organic Shapes."""

    def __init__(self, theme_repository: IThemeRepository) -> None:
        self._repository = theme_repository

    async def get_active_theme(self) -> ThemeConfigDTO:
        """Fetch active theme configuration as DTO."""
        entity = await self._repository.get_active_theme()
        return self._to_dto(entity)

    async def set_preset(self, preset_key: ColorPresetKey) -> ThemeConfigDTO:
        """Switch to one of the predefined pastel palettes."""
        theme = await self._repository.get_active_theme()
        theme.apply_palette(preset_key)
        logger.info("admin_action", action="theme_preset", preset=preset_key.value)
        return self._to_dto(await self._repository.save_theme(theme))

    async def set_shape(self, shape_type: ShapeType) -> ThemeConfigDTO:
        """Switch to one of the organic shape presets."""
        theme = await self._repository.get_active_theme()
        theme.active_shape = shape_type
        logger.info("admin_action", action="theme_shape", shape=shape_type.value)
        return self._to_dto(await self._repository.save_theme(theme))

    async def update_theme(self, dto: UpdateThemeRequestDTO) -> ThemeConfigDTO:
        """Save custom colours, typography, shape and ambient settings."""
        theme = await self._repository.get_active_theme()
        theme.preset_key = dto.preset_key
        theme.name = (
            "Individuelles Design"
            if dto.preset_key == ColorPresetKey.CUSTOM
            else PRESET_THEMES[dto.preset_key].name
        )
        theme.primary_color = dto.primary_color
        theme.primary_hover = dto.primary_hover or dto.primary_color
        theme.secondary_color = dto.secondary_color
        theme.accent_color = dto.accent_color
        theme.background_color = dto.background_color
        theme.surface_color = dto.surface_color
        theme.surface_muted = dto.surface_muted
        theme.text_main_color = dto.text_main_color
        theme.text_muted_color = dto.text_muted_color
        theme.border_color = dto.border_color
        theme.heading_font = dto.heading_font.value
        theme.body_font = dto.body_font.value
        theme.active_shape = dto.active_shape
        theme.dandelion_modes = DandelionEffectMode.parse_many(dto.dandelion_modes)
        theme.dandelion_seed_size = dto.dandelion_seed_size
        theme.dandelion_seed_opacity = dto.dandelion_seed_opacity
        theme.kids_photo_opacity = dto.kids_photo_opacity
        theme.header_opacity = dto.header_opacity
        theme.show_phone = dto.show_phone
        logger.info("admin_action", action="theme_custom", preset=dto.preset_key.value)
        return self._to_dto(await self._repository.save_theme(theme))

    def get_all_color_presets(self) -> list[ColorPaletteDTO]:
        """List all 5 preset pastel color themes."""
        return [
            ColorPaletteDTO(
                key=k,
                name=v.name,
                description=v.description,
                primary=v.primary,
                primary_hover=v.primary_hover,
                secondary=v.secondary,
                accent=v.accent,
                background=v.background,
                surface=v.surface,
                surface_muted=v.surface_muted,
                text_main=v.text_main,
                text_muted=v.text_muted,
                border_color=v.border_color,
            )
            for k, v in PRESET_THEMES.items()
        ]

    def get_all_shapes(self) -> list[ShapeDefinitionDTO]:
        """List all 5 geometric/organic shape presets."""
        return [
            ShapeDefinitionDTO(
                type=k,
                name=v.name,
                description=v.description,
                css_border_radius=v.css_border_radius,
            )
            for k, v in PRESET_SHAPES.items()
        ]

    def generate_css_variables(self, theme: ThemeConfigDTO) -> str:
        """Generate the CSS custom properties for all pages.

        Every value is re-validated here (defence in depth): invalid colours or fonts that
        might exist in the database fall back to the default theme instead of being emitted
        into the ``<style>`` block.
        """
        defaults = ThemeConfig()
        shape_def = PRESET_SHAPES.get(theme.active_shape, PRESET_SHAPES[ShapeType.DANDELION_SEED])
        size = min(max(theme.dandelion_seed_size, SEED_SIZE_MIN), SEED_SIZE_MAX)
        opacity = min(max(theme.dandelion_seed_opacity, SEED_OPACITY_MIN), SEED_OPACITY_MAX)
        photo_opacity = min(
            max(theme.kids_photo_opacity, KIDS_PHOTO_OPACITY_MIN), KIDS_PHOTO_OPACITY_MAX
        )
        header_opacity = min(max(theme.header_opacity, HEADER_OPACITY_MIN), HEADER_OPACITY_MAX)

        def color(name: str) -> str:
            value = str(getattr(theme, name))
            return value if is_hex_color(value) else str(getattr(defaults, name))

        def font(value: str, fallback: FontFamily) -> str:
            return value if value in FontFamily.__members__.values() else fallback.value

        return f"""
        :root {{
            --theme-primary: {color("primary_color")};
            --theme-primary-hover: {color("primary_hover")};
            --theme-secondary: {color("secondary_color")};
            --theme-accent: {color("accent_color")};
            --theme-bg: {color("background_color")};
            --theme-surface: {color("surface_color")};
            --theme-surface-muted: {color("surface_muted")};
            --theme-text-main: {color("text_main_color")};
            --theme-text-muted: {color("text_muted_color")};
            --theme-border: {color("border_color")};
            /* RGB channels for Tailwind opacity steps (bg-theme-primary/20 …) */
            --theme-primary-rgb: {hex_to_rgb_channels(color("primary_color"))};
            --theme-primary-hover-rgb: {hex_to_rgb_channels(color("primary_hover"))};
            --theme-secondary-rgb: {hex_to_rgb_channels(color("secondary_color"))};
            --theme-accent-rgb: {hex_to_rgb_channels(color("accent_color"))};
            --theme-bg-rgb: {hex_to_rgb_channels(color("background_color"))};
            --theme-surface-rgb: {hex_to_rgb_channels(color("surface_color"))};
            --theme-surface-muted-rgb: {hex_to_rgb_channels(color("surface_muted"))};
            --theme-text-main-rgb: {hex_to_rgb_channels(color("text_main_color"))};
            --theme-text-muted-rgb: {hex_to_rgb_channels(color("text_muted_color"))};
            --theme-border-rgb: {hex_to_rgb_channels(color("border_color"))};
            --theme-shape-radius: {shape_def.css_border_radius};
            --font-heading: '{font(theme.heading_font, FontFamily.LORA)}', serif;
            --font-body: '{font(theme.body_font, FontFamily.PLUS_JAKARTA_SANS)}', sans-serif;
            --dandelion-seed-size: {size}px;
            --dandelion-seed-opacity: {opacity / 100.0:.2f};
            --kids-photo-opacity: {photo_opacity / 100.0:.2f};
            --header-bg-opacity: {header_opacity / 100.0:.2f};
        }}
        """

    async def apply_dandelion_modes(
        self,
        modes: list[DandelionEffectMode],
        seed_size: int | None = None,
        seed_opacity: int | None = None,
        kids_photo_opacity: int | None = None,
    ) -> ThemeConfigDTO:
        """Apply multi-select ambient modes and (optionally) seed and photo sliders."""
        theme = await self._repository.get_active_theme()
        theme.dandelion_modes = DandelionEffectMode.parse_many(modes)
        if seed_size is not None:
            theme.dandelion_seed_size = min(max(seed_size, SEED_SIZE_MIN), SEED_SIZE_MAX)
        if seed_opacity is not None:
            theme.dandelion_seed_opacity = min(
                max(seed_opacity, SEED_OPACITY_MIN), SEED_OPACITY_MAX
            )
        if kids_photo_opacity is not None:
            theme.kids_photo_opacity = min(
                max(kids_photo_opacity, KIDS_PHOTO_OPACITY_MIN), KIDS_PHOTO_OPACITY_MAX
            )
        logger.info(
            "admin_action",
            action="theme_dandelion",
            modes=[m.value for m in theme.dandelion_modes],
        )
        return self._to_dto(await self._repository.save_theme(theme))

    @staticmethod
    def get_dandelion_modes() -> tuple[DandelionModeDefinition, ...]:
        """Labels and descriptions of all ambient effect modes (design studio)."""
        return DANDELION_MODE_DEFINITIONS

    @staticmethod
    def _to_dto(entity: ThemeConfig) -> ThemeConfigDTO:
        return ThemeConfigDTO.model_validate(entity, from_attributes=True)
