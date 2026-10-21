import contextlib
import re
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING

from atem.domain.models.base import BaseEntity

if TYPE_CHECKING:
    from collections.abc import Iterable

# Only CSS hex colours (#rgb, #rgba, #rrggbb, #rrggbbaa) are accepted anywhere in the theme.
HEX_COLOR_PATTERN = r"^#(?:[0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$"
_HEX_COLOR_RE = re.compile(HEX_COLOR_PATTERN)

SEED_SIZE_MIN, SEED_SIZE_MAX, SEED_SIZE_DEFAULT = 20, 120, 48
SEED_OPACITY_MIN, SEED_OPACITY_MAX, SEED_OPACITY_DEFAULT = 10, 100, 80
# Background photos of the «Atmende Blume» exercise (subtle: never fully opaque)
KIDS_PHOTO_OPACITY_MIN, KIDS_PHOTO_OPACITY_MAX, KIDS_PHOTO_OPACITY_DEFAULT = 0, 80, 30
# Sticky header background: 0 = pure glass (blur only), 100 = opaque
HEADER_OPACITY_MIN, HEADER_OPACITY_MAX, HEADER_OPACITY_DEFAULT = 0, 100, 60


def is_hex_color(value: str) -> bool:
    """Return True for a valid CSS hex colour."""
    return bool(_HEX_COLOR_RE.fullmatch(value))


def hex_to_rgb_channels(value: str) -> str:
    """``#4A6C50`` → ``74 108 80`` – the form Tailwind needs for opacity steps
    (``rgb(var(--x) / <alpha-value>)``). An alpha part of the hex colour is dropped."""
    if not is_hex_color(value):
        raise ValueError(f"not a hex colour: {value!r}")
    digits = value[1:]
    if len(digits) in (3, 4):
        digits = "".join(c * 2 for c in digits)
    return " ".join(str(int(digits[i : i + 2], 16)) for i in (0, 2, 4))


class FontFamily(StrEnum):
    """Allowlist of self-hosted font families selectable in the design studio."""

    LORA = "Lora"
    PLAYFAIR_DISPLAY = "Playfair Display"
    PLUS_JAKARTA_SANS = "Plus Jakarta Sans"
    RUBIK = "Rubik"


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
    KIDS_FLOWER = "kids_flower"  # 6. Atmende Blume für Kinder (Widget, teilt Button mit 4)

    @classmethod
    def parse_many(cls, raw: "str | Iterable[str] | None") -> list["DandelionEffectMode"]:
        """Parse a comma separated string or iterable; invalid values are ignored.

        ``disabled`` only survives on its own – combined with visual modes it is dropped.
        """
        parts = raw.split(",") if isinstance(raw, str) else list(raw or [])
        modes: list[DandelionEffectMode] = []
        for part in parts:
            with contextlib.suppress(ValueError):
                mode = cls(str(part).strip())
                if mode not in modes:
                    modes.append(mode)
        visual: list[DandelionEffectMode] = [m for m in modes if m != cls.DISABLED]
        return visual or [cls.DISABLED]


class PageSection(StrEnum):
    """Reorderable sections of the start page (hero stays first, contact last).

    The declaration order is the default order of the page.
    """

    COMPETENCIES = "competencies"
    SERVICES = "services"
    KIDS = "kids"
    ABOUT = "about"
    QUOTES = "quotes"
    PRACTICE = "practice"

    @property
    def label(self) -> str:
        """German name shown in the design studio."""
        return _SECTION_LABELS[self]

    @classmethod
    def parse_order(cls, raw: "str | Iterable[str] | None") -> list["PageSection"]:
        """Parse a comma separated string or iterable into a complete section order.

        Unknown values and duplicates are dropped; missing sections are appended in the
        default order, so the result always contains every section exactly once.
        """
        parts = raw.split(",") if isinstance(raw, str) else list(raw or [])
        order: list[PageSection] = []
        for part in parts:
            with contextlib.suppress(ValueError):
                section = cls(str(part).strip())
                if section not in order:
                    order.append(section)
        return order + [s for s in cls if s not in order]

    @classmethod
    def move(
        cls, order: "Iterable[PageSection]", section: "PageSection", offset: int
    ) -> list["PageSection"]:
        """Move ``section`` by ``offset`` positions (clamped to the start/end of the list)."""
        result = cls.parse_order(order)
        index = result.index(section)
        target = min(max(index + offset, 0), len(result) - 1)
        result.insert(target, result.pop(index))
        return result


_SECTION_LABELS: dict[PageSection, str] = {
    PageSection.COMPETENCIES: "Kompetenzen",
    PageSection.SERVICES: "Angebote & Tarife",
    PageSection.KIDS: "Atmen mit Kindern",
    PageSection.ABOUT: "Über mich & PUSTERUM",
    PageSection.QUOTES: "Zitate",
    PageSection.PRACTICE: "Praxis",
}


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

    # Dandelion Ambient Effects Engine (Multi-Select Modes 1–5 or Disabled) & Sliders
    dandelion_modes: list[DandelionEffectMode] = field(
        default_factory=lambda: [DandelionEffectMode.DISABLED]
    )
    dandelion_seed_size: int = SEED_SIZE_DEFAULT  # px, SEED_SIZE_MIN..SEED_SIZE_MAX
    dandelion_seed_opacity: int = SEED_OPACITY_DEFAULT  # %, SEED_OPACITY_MIN..SEED_OPACITY_MAX
    kids_photo_opacity: int = KIDS_PHOTO_OPACITY_DEFAULT  # %, KIDS_PHOTO_OPACITY_MIN..MAX
    header_opacity: int = HEADER_OPACITY_DEFAULT  # %, HEADER_OPACITY_MIN..MAX
    show_phone: bool = True  # practice phone visible on the public site
    # Order of the reorderable start-page sections (design studio)
    section_order: list[PageSection] = field(default_factory=lambda: list(PageSection))

    def apply_palette(self, preset_key: "ColorPresetKey") -> None:
        """Take over all colours of a preset palette (falls back to Salbei & Sand)."""
        palette = PRESET_THEMES.get(preset_key, PRESET_THEMES[ColorPresetKey.SALBEI_SAND])
        self.preset_key = preset_key
        self.name = palette.name
        self.primary_color = palette.primary
        self.primary_hover = palette.primary_hover
        self.secondary_color = palette.secondary
        self.accent_color = palette.accent
        self.background_color = palette.background
        self.surface_color = palette.surface
        self.surface_muted = palette.surface_muted
        self.text_main_color = palette.text_main
        self.text_muted_color = palette.text_muted
        self.border_color = palette.border_color


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
        description="Fliessende ovale Kapselformen mit dezenten Blattkonturen.",
        css_border_radius="2rem 6rem 2rem 6rem",
    ),
}


# Colours compared when detecting whether a custom theme equals a preset palette
PALETTE_MATCH_FIELDS = (
    ("primary_color", "primary"),
    ("secondary_color", "secondary"),
    ("accent_color", "accent"),
    ("background_color", "background"),
    ("surface_color", "surface"),
    ("border_color", "border_color"),
)


def find_matching_preset(colors: dict[str, str], current: ColorPresetKey) -> ColorPresetKey:
    """Return the preset whose palette equals ``colors`` (current preset first), else CUSTOM."""

    def matches(palette: ColorPalette) -> bool:
        return all(
            colors.get(field_name, "").lower() == getattr(palette, palette_attr).lower()
            for field_name, palette_attr in PALETTE_MATCH_FIELDS
        )

    candidates = [current, *(key for key in PRESET_THEMES if key != current)]
    for key in candidates:
        palette = PRESET_THEMES.get(key)
        if palette is not None and matches(palette):
            return key
    return ColorPresetKey.CUSTOM


# ------------------------------------------------------------------------------
# DANDELION AMBIENT MODES – metadata for the design studio (TDR-0002)
# ------------------------------------------------------------------------------
@dataclass(frozen=True)
class DandelionModeDefinition:
    """Label and description of an ambient effect mode."""

    key: str
    number: str
    name: str
    badge: str
    description: str


DANDELION_MODE_DEFINITIONS: tuple[DandelionModeDefinition, ...] = (
    DandelionModeDefinition(
        key=DandelionEffectMode.DISABLED.value,
        number="0",
        name="Deaktiviert",
        badge="Standard / Aus",
        description="Vollständig statische Seite ohne Hintergrund-Partikel oder Widgets.",
    ),
    DandelionModeDefinition(
        key=DandelionEffectMode.BREATHING_FLOW.value,
        number="1",
        name="Sanfter Atem-Drift",
        badge="Ambient Flow",
        description="5–6 zarte Samen schweben mit geringer Deckkraft im 4s/6s-Atemrhythmus.",
    ),
    DandelionModeDefinition(
        key=DandelionEffectMode.SCROLL_JOURNEY.value,
        number="2",
        name="Die Reise des Samens",
        badge="Scroll-Begleiter",
        description="Ein einzelner Samen begleitet den Besucher beim Scrollen bis zum Kontakt.",
    ),
    DandelionModeDefinition(
        key=DandelionEffectMode.WATERMARK_ACCENTS.value,
        number="3",
        name="Wasserzeichen-Akzente",
        badge="Statisch & Edel",
        description="Statische, feine Samen-Wasserzeichen an den Seitenrändern.",
    ),
    DandelionModeDefinition(
        key=DandelionEffectMode.BREATH_WIDGET.value,
        number="4",
        name="Interaktive Atem-Pause",
        badge="Zen-Widget",
        description="Schwebendes Zen-Widget unten rechts zum geführten 4-4-6 Durchatmen.",
    ),
    DandelionModeDefinition(
        key=DandelionEffectMode.WHISPER_TRAIL.value,
        number="5",
        name="Sanfter Hauch bei Bewegung",
        badge="Seed Whisper",
        description="Feine Samen entstehen bei Mausbewegung und verfliegen nach 1.2 s.",
    ),
    DandelionModeDefinition(
        key=DandelionEffectMode.KIDS_FLOWER.value,
        number="6",
        name="Atmende Blume (Kinder)",
        badge="Kinder-Widget",
        description=(
            "Geführte Kinder-Atemübung mit Blüte und Pusten-Spiel; mit der Atem-Pause"
            " kombiniert teilen sich beide einen Button. Aus = auch die Sektion «Atmen mit"
            " Kindern» samt Menü-Links und Druckkarte ist ausgeblendet."
        ),
    ),
)
