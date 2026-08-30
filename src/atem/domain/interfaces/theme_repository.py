"""Theme and Corporate Design Repository Interface (ABC)."""

from abc import ABC, abstractmethod

from atem.domain.models.theme import ColorPresetKey, DandelionEffectMode, ShapeType, ThemeConfig


class IThemeRepository(ABC):
    """Abstract interface defining operations for Corporate Design and Theme storage."""

    @abstractmethod
    async def get_active_theme(self) -> ThemeConfig:
        """Fetch the active theme configuration."""

    @abstractmethod
    async def save_theme(self, theme: ThemeConfig) -> ThemeConfig:
        """Save or update theme configuration."""

    @abstractmethod
    async def apply_preset(self, preset_key: ColorPresetKey) -> ThemeConfig:
        """Apply a predefined color palette preset."""

    @abstractmethod
    async def apply_shape(self, shape_type: ShapeType) -> ThemeConfig:
        """Apply an organic/geometric shape preset."""

    @abstractmethod
    async def apply_dandelion_mode(self, mode: DandelionEffectMode) -> ThemeConfig:
        """Apply a single ambient dandelion effect mode."""

    @abstractmethod
    async def apply_dandelion_modes(self, modes: list[DandelionEffectMode]) -> ThemeConfig:
        """Apply multi-select ambient dandelion effect modes."""
