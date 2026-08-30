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
    DandelionEffectMode,
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

    async def set_dandelion_mode(self, mode: DandelionEffectMode) -> ThemeConfigDTO:
        """Switch to one of the 5 ambient dandelion effect modes (or disabled)."""
        updated = await self._repository.apply_dandelion_mode(mode)
        logger.info("Applied dandelion effect mode", mode=mode)
        return self._to_dto(updated)

    async def update_dandelion_settings(
        self,
        mode: DandelionEffectMode,
        seed_size: int,
        seed_opacity: int,
    ) -> ThemeConfigDTO:
        """Update dandelion ambient mode, seed size, and opacity settings."""
        active = await self._repository.get_active_theme()
        active.dandelion_mode = mode
        active.dandelion_seed_size = max(20, min(120, seed_size))
        active.dandelion_seed_opacity = max(10, min(100, seed_opacity))
        saved = await self._repository.save_theme(active)
        logger.info(
            "Updated dandelion settings",
            mode=mode,
            size=seed_size,
            opacity=seed_opacity,
        )
        return self._to_dto(saved)

    async def update_theme(self, dto: UpdateThemeRequestDTO) -> ThemeConfigDTO:
        """Update full custom theme configuration."""
        name = (
            "Individuelles Design"
            if dto.preset_key == ColorPresetKey.CUSTOM
            else dto.preset_key.value
        )
        dandelion_modes: list[DandelionEffectMode]
        if dto.dandelion_modes and dto.dandelion_modes != [DandelionEffectMode.DISABLED]:
            dandelion_modes = list(dto.dandelion_modes)
        elif dto.dandelion_mode != DandelionEffectMode.DISABLED:
            dandelion_modes = [dto.dandelion_mode]
        else:
            dandelion_modes = [DandelionEffectMode.DISABLED]
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
            dandelion_modes=dandelion_modes,
            dandelion_seed_size=dto.dandelion_seed_size,
            dandelion_seed_opacity=dto.dandelion_seed_opacity,
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
        opacity_dec = theme.dandelion_seed_opacity / 100.0

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
            --dandelion-seed-size: {theme.dandelion_seed_size}px;
            --dandelion-seed-opacity: {opacity_dec:.2f};
        }}
        """

    async def apply_dandelion_modes(
        self,
        modes: list[DandelionEffectMode],
        seed_size: int | None = None,
        seed_opacity: int | None = None,
    ) -> ThemeConfigDTO:
        """Apply multi-select ambient dandelion modes and optional slider settings."""
        active = await self._repository.get_active_theme()
        active.dandelion_modes = modes if modes else [DandelionEffectMode.DISABLED]
        if seed_size is not None:
            active.dandelion_seed_size = max(20, min(120, seed_size))
        if seed_opacity is not None:
            active.dandelion_seed_opacity = max(10, min(100, seed_opacity))
        saved = await self._repository.save_theme(active)
        logger.info(
            "Applied dandelion effect modes",
            modes=[m.value for m in active.dandelion_modes],
            size=active.dandelion_seed_size,
            opacity=active.dandelion_seed_opacity,
        )
        return self._to_dto(saved)

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
            dandelion_mode=entity.dandelion_mode,
            dandelion_modes=entity.dandelion_modes,
            dandelion_seed_size=entity.dandelion_seed_size,
            dandelion_seed_opacity=entity.dandelion_seed_opacity,
        )
