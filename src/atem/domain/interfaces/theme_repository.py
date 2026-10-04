"""Theme Repository Interface (ABC)."""

from abc import ABC, abstractmethod

from atem.domain.models.theme import ThemeConfig


class IThemeRepository(ABC):
    """Storage of the single active corporate design configuration."""

    @abstractmethod
    async def get_active_theme(self) -> ThemeConfig:
        """Return the active theme (a default theme is created on first use)."""

    @abstractmethod
    async def save_theme(self, theme: ThemeConfig) -> ThemeConfig:
        """Persist the theme as the active one."""
