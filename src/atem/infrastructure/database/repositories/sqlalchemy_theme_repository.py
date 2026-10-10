"""SQLAlchemy implementation of IThemeRepository (pure persistence, no business rules)."""

from sqlalchemy import select

from atem.domain.interfaces.theme_repository import IThemeRepository
from atem.domain.models.theme import DandelionEffectMode, ThemeConfig
from atem.infrastructure.database.models.theme import ThemeConfigModel
from atem.infrastructure.database.repositories.base import SqlAlchemyRepository

# Stored as a comma separated string in ``theme_configs.dandelion_mode``
_MODES_COLUMN = "dandelion_mode"


class SqlAlchemyThemeRepository(
    SqlAlchemyRepository[ThemeConfigModel, ThemeConfig], IThemeRepository
):
    """Single active theme row."""

    model = ThemeConfigModel
    entity = ThemeConfig

    async def get_active_theme(self) -> ThemeConfig:
        model = await self._active_model()
        if model is None:
            return await self.save_theme(ThemeConfig())
        return self._to_entity(model)

    async def save_theme(self, theme: ThemeConfig) -> ThemeConfig:
        model = await self._active_model()
        if model is None:
            model = ThemeConfigModel(id=theme.id, is_active=True)
            self._session.add(model)
        self._apply(model, theme)
        model.is_active = True
        await self._session.flush()
        return self._to_entity(model)

    async def _active_model(self) -> ThemeConfigModel | None:
        stmt = select(ThemeConfigModel).where(ThemeConfigModel.is_active.is_(True)).limit(1)
        model: ThemeConfigModel | None = await self._session.scalar(stmt)
        return model

    # The modes list is stored as text – everything else maps 1:1 by field name.
    def _to_entity(self, model: ThemeConfigModel) -> ThemeConfig:
        values = {
            name: getattr(model, name) for name in self._field_names() if name != "dandelion_modes"
        }
        modes = DandelionEffectMode.parse_many(getattr(model, _MODES_COLUMN))
        return ThemeConfig(**values, dandelion_modes=modes)

    def _apply(self, model: ThemeConfigModel, entity: ThemeConfig) -> None:
        for name in self._field_names():
            if name not in {"id", "created_at", "updated_at", "dandelion_modes"}:
                setattr(model, name, getattr(entity, name))
        setattr(model, _MODES_COLUMN, ",".join(m.value for m in entity.dandelion_modes))
