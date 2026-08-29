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
    PRESET_SHAPES,
    PRESET_THEMES,
    ColorPresetKey,
    ShapeType,
    ThemeConfig,
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
        """Switch to one of the 5 predefined pastel themes."""
        updated = await self._repository.apply_preset(preset_key)
        logger.info("Applied color preset theme", preset_key=preset_key)
        return self._to_dto(updated)

    async def set_shape(self, shape_type: ShapeType) -> ThemeConfigDTO:
        """Switch to one of the 5 geometric/organic shape presets."""
        updated = await self._repository.apply_shape(shape_type)
        logger.info("Applied organic shape preset", shape_type=shape_type)
        return self._to_dto(updated)

    async def update_theme(self, dto: UpdateThemeRequestDTO) -> ThemeConfigDTO:
        """Update full custom theme configuration."""
        name = (
            "Individuelles Design"
            if dto.preset_key == ColorPresetKey.CUSTOM
            else dto.preset_key.value
        )
        entity = ThemeConfig(
            preset_key=dto.preset_key,
            name=name,
            primary_color=dto.primary_color,
            primary_hover=dto.primary_hover or dto.primary_color,
            secondary_color=dto.secondary_color,
            accent_color=dto.accent_color,
            background_color=dto.background_color,
            surface_color=dto.surface_color,
            surface_muted=dto.surface_muted,
            text_main_color=dto.text_main_color,
            text_muted_color=dto.text_muted_color,
            border_color=dto.border_color,
            heading_font=dto.heading_font,
            body_font=dto.body_font,
            active_shape=dto.active_shape,
            motif_enabled=dto.motif_enabled,
            motif_animation_speed=dto.motif_animation_speed,
        )
        saved = await self._repository.save_theme(entity)
        logger.info("Saved custom theme configuration", preset_key=dto.preset_key)
        return self._to_dto(saved)

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
        """Generate inline CSS custom variables and shape classes for Jinja2 templates."""
        shape_def = PRESET_SHAPES.get(theme.active_shape, PRESET_SHAPES[ShapeType.DANDELION_SEED])

        return f"""
        :root {{
            --theme-primary: {theme.primary_color};
            --theme-primary-hover: {theme.primary_hover};
            --theme-secondary: {theme.secondary_color};
            --theme-accent: {theme.accent_color};
            --theme-bg: {theme.background_color};
            --theme-surface: {theme.surface_color};
            --theme-surface-muted: {theme.surface_muted};
            --theme-text-main: {theme.text_main_color};
            --theme-text-muted: {theme.text_muted_color};
            --theme-border: {theme.border_color};
            --theme-shape-radius: {shape_def.css_border_radius};
            --font-heading: '{theme.heading_font}', serif;
            --font-body: '{theme.body_font}', sans-serif;
        }}
        """

    @staticmethod
    def _to_dto(entity: ThemeConfig) -> ThemeConfigDTO:
        return ThemeConfigDTO(
            id=entity.id,
            preset_key=entity.preset_key,
            name=entity.name,
            primary_color=entity.primary_color,
            primary_hover=entity.primary_hover,
            secondary_color=entity.secondary_color,
            accent_color=entity.accent_color,
            background_color=entity.background_color,
            surface_color=entity.surface_color,
            surface_muted=entity.surface_muted,
            text_main_color=entity.text_main_color,
            text_muted_color=entity.text_muted_color,
            border_color=entity.border_color,
            heading_font=entity.heading_font,
            body_font=entity.body_font,
            active_shape=entity.active_shape,
            motif_enabled=entity.motif_enabled,
            motif_animation_speed=entity.motif_animation_speed,
        )
