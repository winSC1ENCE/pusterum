"""Unit tests for Domain Models and Password Hashing."""

from uuid import UUID

from atem.domain.models.contact import ContactMessage, MessageStatus
from atem.domain.models.profile import Competency, TherapistProfile
from atem.infrastructure.security.argon2_password_hasher import Argon2PasswordHasher


def test_domain_entity_creation() -> None:
    """Test BaseEntity defaults (UUID, timestamps)."""
    comp = Competency(title="Atem & Stimme", description="Erweiterung des Stimmraums")
    assert isinstance(comp.id, UUID)
    assert comp.is_active is True
    assert comp.created_at is not None


def test_therapist_profile_model() -> None:
    """Test TherapistProfile domain entity."""
    profile = TherapistProfile(
        full_name="Sabine Muster",
        title="Dipl. Atemtherapeutin",
        diploma="OdA KT",
        tagline="Atem entdecken",
        bio="Ausbildung und Praxis",
        quote="Der Atem verbindet",
    )
    assert profile.full_name == "Sabine Muster"
    assert profile.competencies == []


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
