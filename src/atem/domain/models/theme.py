from dataclasses import dataclass, field
from enum import StrEnum

from atem.domain.models.base import BaseEntity


class ShapeType(StrEnum):
    """Geometric and organic background shape presets."""

    SOFT_PEBBLE = "soft_pebble"  # Sanfter Kiesel / Organische Blobs
    BREATH_WAVE = "breath_wave"  # Sanfte Atem-Welle
    ZEN_CIRCLE = "zen_circle"  # Konzentrische Zen-Atemringe
    FLUID_CAPSULE = "fluid_capsule"  # Fliessende Kapsel & Blattkurven
    DANDELION_SEED = "dandelion_seed"  # Schwebende Pusteblumen-Samen


class ColorPresetKey(StrEnum):
    """Predefined pastel color themes."""

    SALBEI_SAND = "salbei_sand"  # Salbei & Sand (Ausgleichend)
    LAVENDEL_NEBEL = "lavendel_nebel"  # Lavendel & Nebel (Beruhigend)
    TERRAKOTTA_PUDER = "terrakotta_puder"  # Terrakotta & Puder (Wärmend)
    OZEAN_KIESEL = "ozean_kiesel"  # Ozean & Kiesel (Erfrischend)
    SONNE_WEIZEN = "sonne_weizen"  # Sonne & Weizen (Vitalisierend)
    CUSTOM = "custom"


class DandelionEffectMode(StrEnum):
    """Ambient dandelion and floating seed effect modes across the webapp."""

    DISABLED = "disabled"  # 0. Deaktiviert (Aus)
    BREATHING_FLOW = "breathing_flow"  # 1. Der sanfte Atem-Drift (Ambient Flow)
    SCROLL_JOURNEY = "scroll_journey"  # 2. Die Reise des Samens (Scroll-Begleiter)
    WATERMARK_ACCENTS = "watermark_accents"  # 3. Wasserzeichen-Akzente (Statisch)
    BREATH_WIDGET = "breath_widget"  # 4. Die interaktive Atem-Pause (Zen-Widget)
    WHISPER_TRAIL = "whisper_trail"  # 5. Sanfter Hauch bei Mausbewegung (Seed Whisper)


@dataclass(kw_only=True)
class ColorPalette:
    """Color palette definition for corporate design."""

    name: str
    description: str
    primary: str  # Hauptfarbe (Buttons, Akzenttitel, Links)
    primary_hover: str  # Hover-Zustand für Buttons
    secondary: str  # Sekundäre Farbtöne (Subtiles Grün/Blau/Ocker)
    accent: str  # Schmuckfarbe für Icons & Badges
    background: str  # Seiten-Hintergrundfarbe (Pastell-Creme/Sand)
    surface: str  # Karten- und Container-Hintergrund
    surface_muted: str  # Leicht abgetönter Bereich
    text_main: str  # Haupttextfarbe
    text_muted: str  # Gedämpfter Text
    border_color: str  # Rahmenfarbe


@dataclass(kw_only=True)
class ThemeConfig(BaseEntity):
    """Corporate Design configuration entity."""

    preset_key: ColorPresetKey = ColorPresetKey.SALBEI_SAND
    name: str = "Salbei & Sand"
    primary_color: str = "#4A6C50"
    primary_hover: str = "#3C5641"
    secondary_color: str = "#CEDECF"
    accent_color: str = "#7FA485"
    background_color: str = "#FAF8F5"
    surface_color: str = "#FFFFFF"
    surface_muted: str = "#F3EFE8"
    text_main_color: str = "#1E293B"
    text_muted_color: str = "#64748B"
    border_color: str = "#E6DED1"

    # Typography
    heading_font: str = "Lora"
    body_font: str = "Plus Jakarta Sans"

    # Organic / Geometric Shapes
    active_shape: ShapeType = ShapeType.DANDELION_SEED
    motif_enabled: bool = True
    motif_animation_speed: str = "normal"  # "slow", "normal", "fast", "static"

    # Dandelion Ambient Effects Engine (Multi-Select Modes 1–5 or Disabled) & Sliders
    dandelion_modes: list[DandelionEffectMode] = field(
        default_factory=lambda: [DandelionEffectMode.DISABLED]
    )
    dandelion_seed_size: int = 48  # Pixel size (20 - 110px)
    dandelion_seed_opacity: int = 80  # Opacity percentage (10 - 100%)

    @property
    def dandelion_mode(self) -> DandelionEffectMode:
        """Backward-compatibility property returning the primary active mode."""
        for m in self.dandelion_modes:
            if m != DandelionEffectMode.DISABLED:
                return m
        return DandelionEffectMode.DISABLED

    @dandelion_mode.setter
    def dandelion_mode(self, val: DandelionEffectMode) -> None:
        """Backward-compatibility setter."""
        self.dandelion_modes = [val]

    @property
    def dandelion_modes_list(self) -> list[str]:
        """Return list of active mode string values for templates and JSON."""
        return [m.value for m in self.dandelion_modes]

    def has_dandelion_mode(self, mode: DandelionEffectMode | str) -> bool:
        """Check if a specific dandelion mode is active."""
        val = mode.value if isinstance(mode, DandelionEffectMode) else mode
        return any(m.value == val for m in self.dandelion_modes)


# ------------------------------------------------------------------------------
# 5 PASTEL COLOR PRESETS (Analog psychotherapie-aarberg.ch)
# ------------------------------------------------------------------------------
PRESET_THEMES: dict[ColorPresetKey, ColorPalette] = {
    ColorPresetKey.SALBEI_SAND: ColorPalette(
        name="Salbei & Sand",
        description=(
            "Ausgleichend, organisch und naturverbunden - inspiriert von Kräutern "
            "und warmem Quarzsand."
        ),
        primary="#4A6C50",
        primary_hover="#3C5641",
        secondary="#CEDECF",
        accent="#7FA485",
        background="#FAF8F5",
        surface="#FFFFFF",
        surface_muted="#F3EFE8",
        text_main="#1E293B",
        text_muted="#64748B",
        border_color="#E6DED1",
    ),
    ColorPresetKey.LAVENDEL_NEBEL: ColorPalette(
        name="Lavendel & Nebel",
        description=(
            "Beruhigend und geistig klärend - zartes Lavendelblau kombiniert mit weichem Nebelgrau."
        ),
        primary="#5E5B7E",
        primary_hover="#4A4767",
        secondary="#D7D5E8",
        accent="#9B97C2",
        background="#F8F7FB",
        surface="#FFFFFF",
        surface_muted="#EDEAF4",
        text_main="#1E2238",
        text_muted="#616782",
        border_color="#DFDCED",
    ),
    ColorPresetKey.TERRAKOTTA_PUDER: ColorPalette(
        name="Terrakotta & Puder",
        description=(
            "Wärmend, nährend und geborgen - erdige Terrakotta-Nuancen und pudriges Rosenquarz."
        ),
        primary="#965646",
        primary_hover="#7C4436",
        secondary="#EED4CD",
        accent="#C88574",
        background="#FAF6F4",
        surface="#FFFFFF",
        surface_muted="#F5ECE8",
        text_main="#2D1C19",
        text_muted="#78615D",
        border_color="#EADCD7",
    ),
    ColorPresetKey.OZEAN_KIESEL: ColorPalette(
        name="Ozean & Kiesel",
        description=(
            "Erfrischend und tief durchatmend - klares skandinavisches Wasserblau "
            "mit feinen Kieselgrautönen."
        ),
        primary="#3D6473",
        primary_hover="#2E4F5D",
        secondary="#CBE0E7",
        accent="#6F9CAE",
        background="#F6F9FA",
        surface="#FFFFFF",
        surface_muted="#EBF2F5",
        text_main="#17242B",
        text_muted="#566973",
        border_color="#D8E5EB",
    ),
    ColorPresetKey.SONNE_WEIZEN: ColorPalette(
        name="Sonne & Weizen",
        description=(
            "Vitalisierend und lichtvoll - sanfter warmer Bernsteinton, kombiniert "
            "mit weichem Elfenbein."
        ),
        primary="#8C6838",
        primary_hover="#70522B",
        secondary="#EEDBBE",
        accent="#BA975E",
        background="#FBF9F3",
        surface="#FFFFFF",
        surface_muted="#F6F0E4",
        text_main="#2C2317",
        text_muted="#756754",
        border_color="#ECE2D0",
    ),
}


# ------------------------------------------------------------------------------
# 5 GEOMETRIC & ORGANIC SHAPES DESCRIPTIONS
# ------------------------------------------------------------------------------
@dataclass(kw_only=True)
class ShapeDefinition:
    """Definition and CSS properties for an organic shape preset."""

    shape_type: ShapeType
    name: str
    description: str
    css_border_radius: str
    css_clip_path: str = ""


PRESET_SHAPES: dict[ShapeType, ShapeDefinition] = {
    ShapeType.DANDELION_SEED: ShapeDefinition(
        shape_type=ShapeType.DANDELION_SEED,
        name="Pusteblumen-Samen (Floating Seeds)",
        description=(
            "Filigrane, schwebende Schirmchen und sanfte Atem-Partikel, die "
            "Leichtigkeit vermitteln."
        ),
        css_border_radius="42% 58% 70% 30% / 45% 45% 55% 55%",
    ),
    ShapeType.SOFT_PEBBLE: ShapeDefinition(
        shape_type=ShapeType.SOFT_PEBBLE,
        name="Sanfter Kiesel (Soft Pebble)",
        description="Asymmetrisch abgerundete Stein- und Flusskieselformen für geerdete Ruhe.",
        css_border_radius="60% 40% 30% 70% / 60% 30% 70% 40%",
    ),
    ShapeType.BREATH_WAVE: ShapeDefinition(
        shape_type=ShapeType.BREATH_WAVE,
        name="Atem-Welle (Breath Wave)",
        description=(
            "Sanft geschwungene Wellenlinien, die den Ein- und Ausatemrhythmus symbolisieren."
        ),
        css_border_radius="50% 50% 30% 70% / 50% 30% 70% 50%",
    ),
    ShapeType.ZEN_CIRCLE: ShapeDefinition(
        shape_type=ShapeType.ZEN_CIRCLE,
        name="Zen-Atemringe (Concentric Rings)",
        description=(
            "Konzentrische, harmonisch pulsierende Kreisstrukturen für zentrierte Achtsamkeit."
        ),
        css_border_radius="50%",
    ),
    ShapeType.FLUID_CAPSULE: ShapeDefinition(
        shape_type=ShapeType.FLUID_CAPSULE,
        name="Flüssige Kapsel (Fluid Capsule & Leaf)",
        description="Fließende ovale Kapselformen mit dezenten Blattkonturen.",
        css_border_radius="2rem 6rem 2rem 6rem",
    ),
}
