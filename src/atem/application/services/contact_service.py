"""Contact Application Service.

Abuse protection is layered (each layer alone is cheap to bypass, together they are not):

1. honeypot field and signed form timing token (checked in the presentation layer),
2. ALTCHA proof-of-work captcha with replay protection,
3. per-IP rate limits (hour/day) stored in the database (works across all workers),
4. at most one confirmation mail per address and day – and that mail never contains
   visitor-controlled text, so the form cannot be abused as a spam relay.
"""

import hashlib
import hmac
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

import structlog

from atem.application.dto.contact import ContactMessageResponseDTO, CreateContactMessageDTO
from atem.domain.exceptions import (
    EntityNotFoundException,
    RateLimitedException,
    ValidationException,
)
from atem.domain.interfaces.captcha import ICaptcha
from atem.domain.interfaces.contact_repository import IContactRepository
from atem.domain.interfaces.email_service import IEmailService
from atem.domain.models.contact import ContactMessage, MessageStatus

logger = structlog.get_logger(__name__)

GENERIC_REJECTION = "Ihre Nachricht konnte nicht gesendet werden. Bitte versuchen Sie es erneut."
CAPTCHA_REQUIRED = "Bitte bestätigen Sie die Sicherheitsprüfung («Ich bin kein Roboter»)."
RATE_LIMITED = (
    "Sie haben bereits mehrere Nachrichten gesendet. Bitte versuchen Sie es später erneut "
    "oder rufen Sie direkt an."
)


@dataclass(frozen=True)
class ContactLimits:
    """Abuse-protection thresholds."""

    per_ip_hour: int = 3
    per_ip_day: int = 10
    confirmation_interval: timedelta = timedelta(hours=24)


class ContactService:
    """Application service for handling contact inquiries and notifications."""

    def __init__(
        self,
        contact_repository: IContactRepository,
        email_service: IEmailService,
        captcha: ICaptcha,
        email_hash_key: bytes,
        limits: ContactLimits | None = None,
    ) -> None:
        self._repository = contact_repository
        self._email_service = email_service
        self._captcha = captcha
        self._email_hash_key = email_hash_key
        self._limits = limits or ContactLimits()

    def create_captcha_challenge(self) -> dict[str, object]:
        """Issue a captcha challenge for the browser widget."""
        return self._captcha.create_challenge()

    def hash_email(self, email: str) -> str:
        """Peppered hash of an address (no plain-text lookup of e-mail addresses)."""
        return hmac.new(
            self._email_hash_key, email.strip().lower().encode(), hashlib.sha256
        ).hexdigest()

    async def submit_contact_form(
        self,
        dto: CreateContactMessageDTO,
        client_ip: str | None,
        captcha_payload: str,
    ) -> ContactMessageResponseDTO:
        """Validate, rate-limit, store and notify."""
        if dto.honeypot:
            logger.warning("contact_spam_honeypot")
            raise ValidationException(GENERIC_REJECTION)

        verified = self._captcha.verify(captcha_payload)
        if verified is None:
            raise ValidationException(CAPTCHA_REQUIRED)
        if not await self._repository.register_captcha_challenge(
            verified.challenge_id, verified.expires_at
        ):
            logger.warning("contact_captcha_replay")
            raise ValidationException(CAPTCHA_REQUIRED)

        now = datetime.now(UTC)
        if client_ip:
            last_hour = await self._repository.count_messages_from_ip(
                client_ip, now - timedelta(hours=1)
            )
            last_day = await self._repository.count_messages_from_ip(
                client_ip, now - timedelta(days=1)
            )
            if last_hour >= self._limits.per_ip_hour or last_day >= self._limits.per_ip_day:
                logger.warning("contact_rate_limited")
                raise RateLimitedException(RATE_LIMITED)

        email_hash = self.hash_email(str(dto.sender_email))
        saved = await self._repository.create_message(
            ContactMessage(
                sender_name=dto.sender_name.strip(),
                sender_email=str(dto.sender_email).strip(),
                sender_phone=dto.sender_phone.strip() if dto.sender_phone else None,
                subject=dto.subject.strip(),
                message=dto.message.strip(),
                status=MessageStatus.NEW,
                ip_address=client_ip,
                email_hash=email_hash,
            )
        )
        logger.info("contact_message_stored", message_id=str(saved.id))

        await self._email_service.send_contact_notification(saved)
        already_confirmed = await self._repository.confirmation_sent_since(
            email_hash, now - self._limits.confirmation_interval
        )
        if not already_confirmed and await self._email_service.send_contact_confirmation(
            saved.sender_email
        ):
            saved.confirmation_sent = True
            saved = await self._repository.update_message(saved)

        return ContactMessageResponseDTO.model_validate(saved)

    async def list_messages(
        self,
        *,
        status: MessageStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ContactMessageResponseDTO]:
        """Fetch inquiries for the admin view."""
        messages = await self._repository.get_messages(status=status, limit=limit, offset=offset)
        return [ContactMessageResponseDTO.model_validate(m) for m in messages]

    async def message_counts(self) -> dict[str, int]:
        """Totals for the dashboard: ``total`` and one entry per status value (e.g. ``NEW``)."""
        per_status = await self._repository.count_by_status()
        counts = {status.value: per_status.get(status, 0) for status in MessageStatus}
        counts["total"] = sum(per_status.values())
        return counts

    async def update_message_status(
        self, message_id: UUID, status: MessageStatus
    ) -> ContactMessageResponseDTO:
        """Change the processing status of an inquiry."""
        existing = await self._repository.get_message_by_id(message_id)
        if not existing:
            raise EntityNotFoundException("ContactMessage", str(message_id))
        existing.status = status
        updated = await self._repository.update_message(existing)
        logger.info("admin_action", action="message_status", status=status.value)
        return ContactMessageResponseDTO.model_validate(updated)

    async def delete_message(self, message_id: UUID) -> None:
        """Permanently delete an inquiry (data protection: right to erasure)."""
        if not await self._repository.delete_message(message_id):
            raise EntityNotFoundException("ContactMessage", str(message_id))
        logger.info("admin_action", action="message_deleted")

    async def purge_expired(self, retention: timedelta) -> int:
        """Delete messages older than the retention period and expired captcha records."""
        now = datetime.now(UTC)
        deleted = await self._repository.delete_messages_older_than(now - retention)
        await self._repository.purge_expired_captcha_challenges(now)
        if deleted:
            logger.info("contact_messages_purged", deleted=deleted)
        return deleted
