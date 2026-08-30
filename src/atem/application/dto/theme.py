"""Theme and Corporate Design Data Transfer Objects (DTOs)."""

from uuid import UUID

from pydantic import BaseModel, Field

from atem.domain.models.theme import ColorPresetKey, DandelionEffectMode, ShapeType


class ColorPaletteDTO(BaseModel):
    """DTO representing a color preset."""

    key: ColorPresetKey
    name: str
    description: str
    primary: str
    primary_hover: str
    secondary: str
    accent: str
    background: str
    surface: str
    surface_muted: str
    text_main: str
    text_muted: str
    border_color: str


class ShapeDefinitionDTO(BaseModel):
    """DTO representing an organic shape preset."""

    type: ShapeType
    name: str
    description: str
    css_border_radius: str


class ThemeConfigDTO(BaseModel):
    """DTO for theme configuration."""

    id: UUID | None = None
    preset_key: ColorPresetKey = ColorPresetKey.SALBEI_SAND
    name: str = Field(default="Salbei & Sand", min_length=2, max_length=100)
    primary_color: str = Field(default="#4A6C50", min_length=4, max_length=20)
    primary_hover: str = Field(default="#3C5641", min_length=4, max_length=20)
    secondary_color: str = Field(default="#CEDECF", min_length=4, max_length=20)
    accent_color: str = Field(default="#7FA485", min_length=4, max_length=20)
    background_color: str = Field(default="#FAF8F5", min_length=4, max_length=20)
    surface_color: str = Field(default="#FFFFFF", min_length=4, max_length=20)
    surface_muted: str = Field(default="#F3EFE8", min_length=4, max_length=20)
    text_main_color: str = Field(default="#1E293B", min_length=4, max_length=20)
    text_muted_color: str = Field(default="#64748B", min_length=4, max_length=20)
    border_color: str = Field(default="#E6DED1", min_length=4, max_length=20)

    heading_font: str = Field(default="Lora", max_length=50)
    body_font: str = Field(default="Plus Jakarta Sans", max_length=50)

    active_shape: ShapeType = ShapeType.DANDELION_SEED
    motif_enabled: bool = True
    motif_animation_speed: str = Field(default="normal", max_length=20)
    dandelion_mode: DandelionEffectMode = DandelionEffectMode.DISABLED
    dandelion_modes: list[DandelionEffectMode] = Field(
        default_factory=lambda: [DandelionEffectMode.DISABLED]
    )
    dandelion_seed_size: int = Field(default=48, ge=20, le=120)
    dandelion_seed_opacity: int = Field(default=80, ge=10, le=100)

    def has_dandelion_mode(self, mode: DandelionEffectMode | str) -> bool:
        """Check if a specific dandelion mode is active."""
        val = mode.value if isinstance(mode, DandelionEffectMode) else mode
        return any(m.value == val for m in self.dandelion_modes)

    @property
    def dandelion_modes_list(self) -> list[str]:
        """Return list of active mode string values for templates and JSON."""
        return [m.value for m in self.dandelion_modes]


class UpdateThemeRequestDTO(BaseModel):
    """Request payload to update custom theme colors and typography."""

    preset_key: ColorPresetKey = ColorPresetKey.CUSTOM
    primary_color: str = Field(..., min_length=4, max_length=20)
    primary_hover: str | None = None
    secondary_color: str = Field(..., min_length=4, max_length=20)
    accent_color: str = Field(..., min_length=4, max_length=20)
    background_color: str = Field(..., min_length=4, max_length=20)
    surface_color: str = Field(..., min_length=4, max_length=20)
    surface_muted: str = Field(..., min_length=4, max_length=20)
    text_main_color: str = Field(..., min_length=4, max_length=20)
    text_muted_color: str = Field(..., min_length=4, max_length=20)
    border_color: str = Field(..., min_length=4, max_length=20)
    heading_font: str = Field(default="Lora", max_length=50)
    body_font: str = Field(default="Plus Jakarta Sans", max_length=50)
    active_shape: ShapeType = ShapeType.DANDELION_SEED
    motif_enabled: bool = True
    motif_animation_speed: str = Field(default="normal", max_length=20)
    dandelion_mode: DandelionEffectMode = DandelionEffectMode.DISABLED
    dandelion_modes: list[DandelionEffectMode] = Field(
        default_factory=lambda: [DandelionEffectMode.DISABLED]
    )
    dandelion_seed_size: int = Field(default=48, ge=20, le=120)
    dandelion_seed_opacity: int = Field(default=80, ge=10, le=100)


class UpdateDandelionModeRequestDTO(BaseModel):
    """Request payload to update ambient dandelion effect mode and sliders."""

    dandelion_mode: DandelionEffectMode = DandelionEffectMode.DISABLED
    dandelion_modes: list[DandelionEffectMode] = Field(
        default_factory=lambda: [DandelionEffectMode.DISABLED]
    )
    dandelion_seed_size: int = Field(default=48, ge=20, le=120)
    dandelion_seed_opacity: int = Field(default=80, ge=10, le=100)
