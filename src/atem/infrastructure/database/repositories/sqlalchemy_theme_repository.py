"""SQLAlchemy implementation of IThemeRepository."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from atem.domain.interfaces.theme_repository import IThemeRepository
from atem.domain.models.theme import (
    PRESET_THEMES,
    ColorPresetKey,
    ShapeType,
    ThemeConfig,
)
from atem.infrastructure.database.models.theme import ThemeConfigModel


class SqlAlchemyThemeRepository(IThemeRepository):
    """SQLAlchemy 2.0 Async repository for Theme & Corporate Design."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_active_theme(self) -> ThemeConfig:
        """Fetch active theme or create default."""
        stmt = select(ThemeConfigModel).where(ThemeConfigModel.is_active.is_(True)).limit(1)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            default = ThemeConfig()
            model = ThemeConfigModel(
                id=default.id,
                preset_key=default.preset_key,
                name=default.name,
                primary_color=default.primary_color,
                primary_hover=default.primary_hover,
                secondary_color=default.secondary_color,
                accent_color=default.accent_color,
                background_color=default.background_color,
                surface_color=default.surface_color,
                surface_muted=default.surface_muted,
                text_main_color=default.text_main_color,
                text_muted_color=default.text_muted_color,
                border_color=default.border_color,
                heading_font=default.heading_font,
                body_font=default.body_font,
                active_shape=default.active_shape,
                motif_enabled=default.motif_enabled,
                motif_animation_speed=default.motif_animation_speed,
                is_active=True,
            )
            self._session.add(model)
            await self._session.flush()

        return self._to_entity(model)

    async def save_theme(self, theme: ThemeConfig) -> ThemeConfig:
        """Save or update theme configuration."""
        stmt = select(ThemeConfigModel).where(ThemeConfigModel.is_active.is_(True)).limit(1)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            model = ThemeConfigModel(id=theme.id)
            self._session.add(model)

        model.preset_key = theme.preset_key
        model.name = theme.name
        model.primary_color = theme.primary_color
        model.primary_hover = theme.primary_hover
        model.secondary_color = theme.secondary_color
        model.accent_color = theme.accent_color
        model.background_color = theme.background_color
        model.surface_color = theme.surface_color
        model.surface_muted = theme.surface_muted
        model.text_main_color = theme.text_main_color
        model.text_muted_color = theme.text_muted_color
        model.border_color = theme.border_color
        model.heading_font = theme.heading_font
        model.body_font = theme.body_font
        model.active_shape = theme.active_shape
        model.motif_enabled = theme.motif_enabled
        model.motif_animation_speed = theme.motif_animation_speed
        model.is_active = True

        await self._session.flush()
        theme.id = model.id
        return theme

    async def apply_preset(self, preset_key: ColorPresetKey) -> ThemeConfig:
        """Apply one of the 5 preset pastel themes."""
        palette = PRESET_THEMES.get(preset_key, PRESET_THEMES[ColorPresetKey.SALBEI_SAND])
        active = await self.get_active_theme()

        active.preset_key = preset_key
        active.name = palette.name
        active.primary_color = palette.primary
        active.primary_hover = palette.primary_hover
        active.secondary_color = palette.secondary
        active.accent_color = palette.accent
        active.background_color = palette.background
        active.surface_color = palette.surface
        active.surface_muted = palette.surface_muted
        active.text_main_color = palette.text_main
        active.text_muted_color = palette.text_muted
        active.border_color = palette.border_color

        return await self.save_theme(active)

    async def apply_shape(self, shape_type: ShapeType) -> ThemeConfig:
        """Apply one of the 5 geometric/organic shapes."""
        active = await self.get_active_theme()
        active.active_shape = shape_type
        return await self.save_theme(active)

    @staticmethod
    def _to_entity(m: ThemeConfigModel) -> ThemeConfig:
        return ThemeConfig(
            id=m.id,
            created_at=m.created_at,
            updated_at=m.updated_at,
            preset_key=m.preset_key,
            name=m.name,
            primary_color=m.primary_color,
            primary_hover=m.primary_hover,
            secondary_color=m.secondary_color,
            accent_color=m.accent_color,
            background_color=m.background_color,
            surface_color=m.surface_color,
            surface_muted=m.surface_muted,
            text_main_color=m.text_main_color,
            text_muted_color=m.text_muted_color,
            border_color=m.border_color,
            heading_font=m.heading_font,
            body_font=m.body_font,
            active_shape=m.active_shape,
            motif_enabled=m.motif_enabled,
            motif_animation_speed=m.motif_animation_speed,
        )
