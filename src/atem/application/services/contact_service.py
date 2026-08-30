"""Contact Application Service."""

from uuid import UUID

import structlog

from atem.application.dto.contact import (
    ContactMessageResponseDTO,
    CreateContactMessageDTO,
    UpdateContactMessageStatusDTO,
)
from atem.domain.exceptions import EntityNotFoundException, ValidationException
from atem.domain.interfaces.contact_repository import IContactRepository
from atem.domain.interfaces.email_service import IEmailService
from atem.domain.models.contact import ContactMessage, MessageStatus

logger = structlog.get_logger(__name__)


class ContactService:
    """Application service for handling contact inquiries and notifications."""

    def __init__(
        self,
        contact_repository: IContactRepository,
        email_service: IEmailService,
    ) -> None:
        self._repository = contact_repository
        self._email_service = email_service

    async def submit_contact_form(
        self,
        dto: CreateContactMessageDTO,
        client_ip: str | None = None,
    ) -> ContactMessageResponseDTO:
        """Process incoming public contact form submission with anti-spam check."""
        # 1. Anti-spam honeypot verification
        if dto.honeypot:
            logger.warning("Spam submission detected via honeypot field", ip=client_ip)
            raise ValidationException("Spam submission detected.")

        # 2. Persist contact message
        domain_message = ContactMessage(
            sender_name=dto.sender_name.strip(),
            sender_email=dto.sender_email.strip(),
            sender_phone=dto.sender_phone.strip() if dto.sender_phone else None,
            subject=dto.subject.strip(),
            message=dto.message.strip(),
            status=MessageStatus.NEW,
            ip_address=client_ip,
        )

        saved = await self._repository.create_message(domain_message)
        logger.info("New contact message stored", message_id=str(saved.id))

        # 3. Trigger email notification (non-blocking failure)
        try:
            await self._email_service.send_contact_notification(saved)
            await self._email_service.send_contact_confirmation(saved)
        except Exception:
            logger.exception("Failed to send contact notification email")

        return ContactMessageResponseDTO(
            id=saved.id,
            sender_name=saved.sender_name,
            sender_email=saved.sender_email,
            sender_phone=saved.sender_phone,
            subject=saved.subject,
            message=saved.message,
            status=saved.status,
            notes=saved.notes,
            created_at=saved.created_at,
        )

    async def list_messages(
        self,
        *,
        status: MessageStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ContactMessageResponseDTO]:
        """Fetch inquiries for admin view."""
        messages = await self._repository.get_messages(status=status, limit=limit, offset=offset)
        return [
            ContactMessageResponseDTO(
                id=m.id,
                sender_name=m.sender_name,
                sender_email=m.sender_email,
                sender_phone=m.sender_phone,
                subject=m.subject,
                message=m.message,
                status=m.status,
                notes=m.notes,
                created_at=m.created_at,
            )
            for m in messages
        ]

    async def update_message_status(
        self,
        message_id: UUID,
        dto: UpdateContactMessageStatusDTO,
    ) -> ContactMessageResponseDTO:
        """Update inquiry status and internal notes."""
        existing = await self._repository.get_message_by_id(message_id)
        if not existing:
            raise EntityNotFoundException("ContactMessage", str(message_id))

        existing.status = dto.status
        if dto.notes is not None:
            existing.notes = dto.notes

        updated = await self._repository.update_message(existing)
        return ContactMessageResponseDTO(
            id=updated.id,
            sender_name=updated.sender_name,
            sender_email=updated.sender_email,
            sender_phone=updated.sender_phone,
            subject=updated.subject,
            message=updated.message,
            status=updated.status,
            notes=updated.notes,
            created_at=updated.created_at,
        )
