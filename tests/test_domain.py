"""Unit tests for Domain Models and Password Hashing."""

from uuid import UUID

from atem.domain.models.contact import ContactMessage, MessageStatus
from atem.domain.models.offering import ServiceOffering
from atem.domain.models.theme import (
    PRESET_THEMES,
    ColorPresetKey,
    DandelionEffectMode,
    ThemeConfig,
    find_matching_preset,
)
from atem.infrastructure.security.argon2_password_hasher import Argon2PasswordHasher


def test_domain_entity_creation() -> None:
    """BaseEntity defaults (UUID, timestamps) and offering defaults."""
    offering = ServiceOffering(
        title="Einzelsitzung", slug="einzelsitzung", subtitle="", description="60 Minuten"
    )
    assert isinstance(offering.id, UUID)
    assert offering.created_at is not None
    assert offering.is_active is True
    assert offering.is_health_insurance_recognized is False


def test_dandelion_mode_parsing() -> None:
    """parse_many ignores garbage, de-duplicates and drops 'disabled' next to visual modes."""
    parse = DandelionEffectMode.parse_many
    assert parse(None) == [DandelionEffectMode.DISABLED]
    assert parse(",,unknown,") == [DandelionEffectMode.DISABLED]
    assert parse("disabled,breath_widget,breath_widget") == [DandelionEffectMode.BREATH_WIDGET]
    assert parse(["whisper_trail", "scroll_journey"]) == [
        DandelionEffectMode.WHISPER_TRAIL,
        DandelionEffectMode.SCROLL_JOURNEY,
    ]


def test_palette_application_and_preset_detection() -> None:
    """Applying a palette sets all colours; identical colours are recognised as that preset."""
    theme = ThemeConfig()
    theme.apply_palette(ColorPresetKey.LAVENDEL_NEBEL)
    palette = PRESET_THEMES[ColorPresetKey.LAVENDEL_NEBEL]
    assert theme.primary_color == palette.primary
    colors = {
        "primary_color": palette.primary.lower(),
        "secondary_color": palette.secondary,
        "accent_color": palette.accent,
        "background_color": palette.background,
        "surface_color": palette.surface,
        "border_color": palette.border_color,
    }
    assert find_matching_preset(colors, ColorPresetKey.SALBEI_SAND) == ColorPresetKey.LAVENDEL_NEBEL
    assert (
        find_matching_preset({**colors, "primary_color": "#000000"}, ColorPresetKey.SALBEI_SAND)
        == ColorPresetKey.CUSTOM
    )


def test_contact_message_model() -> None:
    """Test ContactMessage domain entity."""
    msg = ContactMessage(
        sender_name="Hans Peter",
        sender_email="hans@example.com",
        message="Ich möchte einen Termin buchen.",
    )
    assert msg.status == MessageStatus.NEW
    assert msg.subject == "Kontaktanfrage via Website"


def test_argon2_password_hasher() -> None:
    """Test Argon2 hashing and verification."""
    hasher = Argon2PasswordHasher()
    pwd = "super-secret-password-123"
    hashed = hasher.hash_password(pwd)
    assert hashed != pwd
    assert hasher.verify_password(pwd, hashed) is True
    assert hasher.verify_password("wrong-password", hashed) is False
