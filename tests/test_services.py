"""Unit tests for Application Services (Profile, Contact, Auth)."""

import pytest

from atem.application.dto.auth import LoginRequestDTO
from atem.application.dto.contact import CreateContactMessageDTO
from atem.application.dto.profile import PracticeInfoDTO, ServiceFormDTO, TherapistProfileDTO
from atem.application.services.auth_service import AuthService
from atem.application.services.contact_service import ContactService
from atem.application.services.profile_service import ProfileService
from atem.domain.exceptions import (
    AuthenticationException,
    EntityNotFoundException,
    ValidationException,
)
from atem.domain.models.contact import MessageStatus
from tests.conftest import solve_altcha


@pytest.mark.asyncio
async def test_profile_service_defaults_and_update(profile_service: ProfileService) -> None:
    """Test getting default public profile and updating."""
    profile = await profile_service.get_public_profile()
    assert profile.full_name is not None

    update_dto = TherapistProfileDTO(
        id=profile.id,
        full_name="Anna Beispiel",
        title="Dipl. Komplementärtherapeutin",
        diploma="OdA KT Atem",
        tagline="Tief durchatmen.",
        bio="Seit über 15 Jahren begleite ich Klientinnen und Klienten.",
        quote="In der Ruhe liegt die Kraft.",
    )
    saved = await profile_service.update_profile(update_dto)
    assert saved.full_name == "Anna Beispiel"

    # Test practice info update
    practice_dto = PracticeInfoDTO(
        name="Praxis Atem Oase",
        street="Bahnhofstrasse 1",
        zip_code="8001",
        city="Zürich",
        phone="+41 44 999 88 77",
        email="info@atem-oase.ch",
    )
    saved_practice = await profile_service.update_practice_info(practice_dto)
    assert saved_practice.name == "Praxis Atem Oase"


@pytest.mark.asyncio
async def test_service_offering_crud(profile_service: ProfileService) -> None:
    """Create/update/delete offerings; slugs are derived and unique."""
    form = ServiceFormDTO(
        title="Atem-Einzelsitzung für Körper & Psyche",
        subtitle="Individuelle Begleitung",
        description="60 Minuten sanfte Atem- und Körpertherapie",
        duration_minutes=60,
        price_chf=140.0,
    )
    created = await profile_service.create_service(form)
    assert created.id is not None
    assert created.slug == "atem-einzelsitzung-fuer-koerper-psyche"
    assert created.is_health_insurance_recognized is False

    duplicate = await profile_service.create_service(form)
    assert duplicate.slug == "atem-einzelsitzung-fuer-koerper-psyche-2"

    updated = await profile_service.update_service(
        created.id, form.model_copy(update={"price_chf": 150.0, "is_active": False})
    )
    assert updated.price_chf == 150.0
    assert updated.slug == created.slug  # unchanged title keeps its slug
    assert [s.id for s in await profile_service.list_services()] == [duplicate.id]
    assert len(await profile_service.list_services(include_inactive=True)) == 2

    assert await profile_service.delete_service(created.id) is True
    with pytest.raises(EntityNotFoundException):
        await profile_service.delete_service(created.id)
    with pytest.raises(EntityNotFoundException):
        await profile_service.update_service(created.id, form)


@pytest.mark.asyncio
async def test_contact_service_flow(contact_service: ContactService) -> None:
    """Test contact form submission and honeypot."""
    dto = CreateContactMessageDTO(
        sender_name="Maria Muster",
        sender_email="maria@muster.ch",
        sender_phone="+41 79 111 22 33",
        subject="Terminanfrage",
        message="Guten Tag, ich hätte gerne nächste Woche einen Termin.",
    )
    response = await contact_service.submit_contact_form(
        dto,
        client_ip="127.0.0.1",
        captcha_payload=solve_altcha(contact_service.create_captcha_challenge()),
    )
    assert response.sender_name == "Maria Muster"
    assert response.status == MessageStatus.NEW

    # Honeypot detection
    spam_dto = CreateContactMessageDTO(
        sender_name="Spam Bot",
        sender_email="bot@spam.com",
        message="Buy crypto now!",
        honeypot="http://spam-link.com",
    )
    with pytest.raises(ValidationException):
        await contact_service.submit_contact_form(spam_dto, client_ip=None, captcha_payload="")

    # List messages
    messages = await contact_service.list_messages()
    assert len(messages) >= 1

    # Update status
    updated = await contact_service.update_message_status(response.id, MessageStatus.READ)
    assert updated.status == MessageStatus.READ


@pytest.mark.asyncio
async def test_auth_service(auth_service: AuthService) -> None:
    """Test admin authentication lifecycle."""
    await auth_service.ensure_initial_admin(
        username="admin",
        email="admin@atem-praxis.ch",
        initial_password="SecretAdminPassword123!",
    )

    # Valid login
    result = await auth_service.authenticate(
        LoginRequestDTO(username="admin", password="SecretAdminPassword123!"), "198.51.100.1"
    )
    assert result.user.username == "admin"
    assert result.requires_totp is False

    # Invalid login
    with pytest.raises(AuthenticationException):
        await auth_service.authenticate(
            LoginRequestDTO(username="admin", password="wrong-password"), "198.51.100.1"
        )
