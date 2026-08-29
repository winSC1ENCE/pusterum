"""Unit tests for Application Services (Profile, Contact, Auth)."""

import pytest

from atem.application.dto.auth import LoginRequestDTO
from atem.application.dto.contact import CreateContactMessageDTO, UpdateContactMessageStatusDTO
from atem.application.dto.profile import PracticeInfoDTO, ServiceOfferingDTO, TherapistProfileDTO
from atem.application.services.auth_service import AuthService
from atem.application.services.contact_service import ContactService
from atem.application.services.profile_service import ProfileService
from atem.domain.exceptions import (
    AuthenticationException,
    EntityNotFoundException,
    ValidationException,
)
from atem.domain.models.contact import MessageStatus


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
    """Test service offering CRUD operations."""
    service_dto = ServiceOfferingDTO(
        title="Atem-Einzelsitzung",
        slug="einzelsitzung",
        subtitle="Individuelle Begleitung",
        description="60 Minuten sanfte Atemtherapie",
        duration_minutes=60,
        price_chf=140.0,
    )
    created = await profile_service.create_service(service_dto)
    assert created.id is not None

    # Update
    created.price_chf = 150.0
    updated = await profile_service.update_service(created.id, created)
    assert updated.price_chf == 150.0

    # Delete
    deleted = await profile_service.delete_service(created.id)
    assert deleted is True

    # Delete non-existing throws EntityNotFoundException
    with pytest.raises(EntityNotFoundException):
        await profile_service.delete_service(created.id)


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
    response = await contact_service.submit_contact_form(dto, client_ip="127.0.0.1")
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
        await contact_service.submit_contact_form(spam_dto)

    # List messages
    messages = await contact_service.list_messages()
    assert len(messages) >= 1

    # Update status
    updated = await contact_service.update_message_status(
        response.id,
        UpdateContactMessageStatusDTO(status=MessageStatus.READ, notes="Gelesen"),
    )
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
    user = await auth_service.authenticate(
        LoginRequestDTO(username="admin", password="SecretAdminPassword123!")
    )
    assert user.username == "admin"

    # Invalid login
    with pytest.raises(AuthenticationException):
        await auth_service.authenticate(
            LoginRequestDTO(username="admin", password="wrong-password")
        )
