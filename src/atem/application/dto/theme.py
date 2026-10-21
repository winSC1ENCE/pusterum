"""Theme and Corporate Design Data Transfer Objects (DTOs)."""

from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field

from atem.domain.models.theme import (
    HEADER_OPACITY_DEFAULT,
    HEADER_OPACITY_MAX,
    HEADER_OPACITY_MIN,
    HEX_COLOR_PATTERN,
    KIDS_PHOTO_OPACITY_DEFAULT,
    KIDS_PHOTO_OPACITY_MAX,
    KIDS_PHOTO_OPACITY_MIN,
    SEED_OPACITY_MAX,
    SEED_OPACITY_MIN,
    SEED_SIZE_MAX,
    SEED_SIZE_MIN,
    ColorPresetKey,
    DandelionEffectMode,
    FontFamily,
    PageSection,
    ShapeType,
)

HexColor = Annotated[str, Field(pattern=HEX_COLOR_PATTERN, max_length=9)]
SeedSize = Annotated[int, Field(ge=SEED_SIZE_MIN, le=SEED_SIZE_MAX)]
SeedOpacity = Annotated[int, Field(ge=SEED_OPACITY_MIN, le=SEED_OPACITY_MAX)]
KidsPhotoOpacity = Annotated[int, Field(ge=KIDS_PHOTO_OPACITY_MIN, le=KIDS_PHOTO_OPACITY_MAX)]
HeaderOpacity = Annotated[int, Field(ge=HEADER_OPACITY_MIN, le=HEADER_OPACITY_MAX)]


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
    dandelion_modes: list[DandelionEffectMode] = Field(
        default_factory=lambda: [DandelionEffectMode.DISABLED]
    )
    dandelion_seed_size: int = Field(default=48, ge=20, le=120)
    dandelion_seed_opacity: int = Field(default=80, ge=10, le=100)
    kids_photo_opacity: KidsPhotoOpacity = KIDS_PHOTO_OPACITY_DEFAULT
    header_opacity: HeaderOpacity = HEADER_OPACITY_DEFAULT
    show_phone: bool = True
    section_order: list[PageSection] = Field(default_factory=lambda: list(PageSection))

    def has_dandelion_mode(self, mode: DandelionEffectMode | str) -> bool:
        """Check if a specific dandelion mode is active (used by templates)."""
        return DandelionEffectMode(mode) in self.dandelion_modes

    @property
    def kids_enabled(self) -> bool:
        """The children's offer (section, links, card) follows the «Atmende Blume» switch."""
        return self.has_dandelion_mode(DandelionEffectMode.KIDS_FLOWER)

    @property
    def dandelion_modes_list(self) -> list[str]:
        """Return list of active mode string values for templates and JSON."""
        return [m.value for m in self.dandelion_modes]


class UpdateThemeRequestDTO(BaseModel):
    """Request payload to update custom theme colors and typography (strictly validated)."""

    preset_key: ColorPresetKey = ColorPresetKey.CUSTOM
    primary_color: HexColor
    primary_hover: HexColor | None = None
    secondary_color: HexColor
    accent_color: HexColor
    background_color: HexColor
    surface_color: HexColor
    surface_muted: HexColor
    text_main_color: HexColor
    text_muted_color: HexColor
    border_color: HexColor
    heading_font: FontFamily = FontFamily.LORA
    body_font: FontFamily = FontFamily.PLUS_JAKARTA_SANS
    active_shape: ShapeType = ShapeType.DANDELION_SEED
    dandelion_modes: list[DandelionEffectMode] = Field(
        default_factory=lambda: [DandelionEffectMode.DISABLED]
    )
    dandelion_seed_size: SeedSize = 48
    dandelion_seed_opacity: SeedOpacity = 80
    kids_photo_opacity: KidsPhotoOpacity = KIDS_PHOTO_OPACITY_DEFAULT
    header_opacity: HeaderOpacity = HEADER_OPACITY_DEFAULT
    show_phone: bool = True
