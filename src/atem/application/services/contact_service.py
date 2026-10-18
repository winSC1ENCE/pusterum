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
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from uuid import UUID

import structlog

from atem.application.dto.contact import (
    ContactMessageResponseDTO,
    CreateContactMessageDTO,
    MessageDetailDTO,
    MessageEventDTO,
    MessagePageDTO,
)
from atem.domain.exceptions import (
    EntityNotFoundException,
    RateLimitedException,
    ValidationException,
)
from atem.domain.interfaces.captcha import ICaptcha
from atem.domain.interfaces.contact_repository import IContactRepository
from atem.domain.interfaces.email_service import IEmailService
from atem.domain.models.contact import (
    OPEN_STATUSES,
    ContactMessage,
    ContactMessageEvent,
    DeletionReason,
    DeletionRecord,
    EventAction,
    MessageQuery,
    MessageStatus,
    RetentionPolicy,
)

logger = structlog.get_logger(__name__)

GENERIC_REJECTION = "Ihre Nachricht konnte nicht gesendet werden. Bitte versuchen Sie es erneut."
CAPTCHA_REQUIRED = "Bitte bestätigen Sie die Sicherheitsprüfung («Ich bin kein Roboter»)."
RATE_LIMITED = (
    "Sie haben bereits mehrere Nachrichten gesendet. Bitte versuchen Sie es später erneut "
    "oder rufen Sie direkt an."
)


# Longer than the widest per-IP limit window (24 h) so the limits keep working (ADR-0006)
IP_RETENTION = timedelta(days=7)
# A message still «Neu» after this time is marked as overdue in the admin list.
OVERDUE_AFTER = timedelta(days=2)
MAX_NOTES_LENGTH = 5000
# Deletion log entries are needed while a backup can still hold the deleted message: restic keeps
# monthly snapshots for 6 months (docker/backup/backup.sh), plus a margin (ADR-0006).
DELETION_LOG_RETENTION = timedelta(days=213)


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
        *,
        email_hash_key: bytes,
        limits: ContactLimits | None = None,
        retention: RetentionPolicy | None = None,
    ) -> None:
        self._repository = contact_repository
        self._email_service = email_service
        self._captcha = captcha
        self._email_hash_key = email_hash_key
        self._limits = limits or ContactLimits()
        self._retention = retention or RetentionPolicy()

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

        return self._to_dto(saved)

    async def search_messages(self, query: MessageQuery) -> MessagePageDTO:
        """One page of the admin list with retention date and overdue hint per message."""
        messages, total = await self._repository.search_messages(query)
        page_size = max(query.limit, 1)
        return MessagePageDTO(
            items=[self._to_dto(m) for m in messages],
            total=total,
            page=query.offset // page_size + 1,
            pages=max(1, -(-total // page_size)),
        )

    async def export_person(self, email: str) -> list[dict[str, object]]:
        """All stored data of one sender for an access request (Art. 25 DSG, runbook 7.1)."""
        messages = await self._repository.find_by_sender_email(email)
        logger.info("admin_action", action="person_exported", messages=len(messages))
        return [
            {
                "eingang": m.created_at.isoformat() if m.created_at else None,
                "name": m.sender_name,
                "email": m.sender_email,
                "telefon": m.sender_phone,
                "betreff": m.subject,
                "nachricht": m.message,
                "status": m.status.value,
                "abgeschlossen": m.closed_at.isoformat() if m.closed_at else None,
                "notizen": m.notes,
                "ip_adresse": m.ip_address,
            }
            for m in messages
        ]

    async def export_sender_of(self, message_id: UUID) -> list[dict[str, object]]:
        """All messages from the sender address of this message (admin download)."""
        return await self.export_person((await self._get(message_id)).sender_email)

    async def message_counts(self) -> dict[str, int]:
        """Totals: ``total``, ``open`` and one entry per status value (e.g. ``NEW``)."""
        per_status = await self._repository.count_by_status()
        counts = {status.value: per_status.get(status, 0) for status in MessageStatus}
        counts["open"] = sum(counts[status.value] for status in OPEN_STATUSES)
        counts["total"] = sum(per_status.values())
        return counts

    async def open_message(self, message_id: UUID, actor_id: UUID | None) -> MessageDetailDTO:
        """Detail view; the first opening moves a new message to «In Bearbeitung»."""
        message = await self._get(message_id)
        if message.status == MessageStatus.NEW:
            message = await self._set_status(message, MessageStatus.IN_PROGRESS, actor_id)
        events = await self._repository.list_events(message_id)
        same_sender = await self._repository.find_by_sender_email(message.sender_email)
        return MessageDetailDTO(
            message=self._to_dto(message),
            sender_message_count=len(same_sender),
            events=[
                MessageEventDTO(
                    created_at=_as_utc(e.created_at),
                    action=e.action,
                    summary=_event_summary(e),
                    actor_email=e.actor_email,
                )
                for e in events
            ],
        )

    async def change_status(
        self, message_id: UUID, status: MessageStatus, actor_id: UUID | None
    ) -> ContactMessageResponseDTO:
        """Change the processing status (recorded in the history)."""
        message = await self._set_status(await self._get(message_id), status, actor_id)
        return self._to_dto(message)

    async def update_notes(self, message_id: UUID, notes: str, actor_id: UUID | None) -> None:
        """Save the internal notes; the history records only that they changed."""
        if len(notes) > MAX_NOTES_LENGTH:
            raise ValidationException(f"Notizen: höchstens {MAX_NOTES_LENGTH} Zeichen.")
        message = await self._get(message_id)
        cleaned = notes.strip() or None
        if cleaned == message.notes:
            return
        message.notes = cleaned
        await self._repository.update_message(message)
        await self._repository.add_event(
            ContactMessageEvent(message_id=message.id, action=EventAction.NOTES, actor_id=actor_id)
        )
        logger.info("admin_action", action="message_notes")

    async def delete_message(self, message_id: UUID, actor_id: UUID | None = None) -> None:
        """Permanently delete an inquiry and log it for re-deletion after a restore."""
        message = await self._get(message_id)
        await self._log_deletions([message], DeletionReason.MESSAGE, actor_id)
        await self._repository.delete_message(message_id)
        logger.info("admin_action", action="message_deleted")

    async def forget_person(self, email: str, actor_id: UUID | None = None) -> int:
        """Erasure request (Art. 32 DSG): delete all messages of an address; return the count."""
        messages = await self._repository.find_by_sender_email(email)
        await self._log_deletions(messages, DeletionReason.PERSON, actor_id)
        deleted = await self._repository.delete_messages([m.id for m in messages])
        logger.info("admin_action", action="person_forgotten", messages=deleted)
        return deleted

    async def forget_sender_of(self, message_id: UUID, actor_id: UUID | None) -> int:
        """Erasure request from the detail view: all messages from this sender address."""
        return await self.forget_person((await self._get(message_id)).sender_email, actor_id)

    async def reapply_deletions(self) -> int:
        """Delete logged messages again, e.g. after a restore from backup; return the count."""
        deleted = await self._repository.reapply_deletions()
        if deleted:
            logger.warning("deletions_reapplied", messages=deleted)
        return deleted

    async def _log_deletions(
        self, messages: list[ContactMessage], reason: DeletionReason, actor_id: UUID | None
    ) -> None:
        await self._repository.record_deletions(
            [
                DeletionRecord(
                    message_id=m.id,
                    reason=reason,
                    email_hash=self.hash_email(m.sender_email),
                    actor_id=actor_id,
                )
                for m in messages
            ]
        )

    async def _get(self, message_id: UUID) -> ContactMessage:
        message = await self._repository.get_message_by_id(message_id)
        if message is None:
            raise EntityNotFoundException("ContactMessage", str(message_id))
        return message

    async def _set_status(
        self, message: ContactMessage, status: MessageStatus, actor_id: UUID | None
    ) -> ContactMessage:
        old = message.status
        if status == old:
            return message
        message.change_status(status)
        updated = await self._repository.update_message(message)
        await self._repository.add_event(
            ContactMessageEvent(
                message_id=message.id,
                action=EventAction.STATUS,
                old_value=old.value,
                new_value=status.value,
                actor_id=actor_id,
            )
        )
        logger.info("admin_action", action="message_status", status=status.value)
        return updated

    def _to_dto(self, message: ContactMessage) -> ContactMessageResponseDTO:
        message = replace(
            message,
            created_at=_as_utc(message.created_at),
            closed_at=_as_utc(message.closed_at) if message.closed_at else None,
        )
        dto = ContactMessageResponseDTO.model_validate(message)
        dto.delete_after = self._retention.delete_after(message)
        dto.overdue = (
            message.status == MessageStatus.NEW
            and message.created_at < datetime.now(UTC) - OVERDUE_AFTER
        )
        return dto

    async def purge_expired(self) -> int:
        """Delete messages past their retention period and expired captcha records.

        Periods per status: ``RetentionPolicy`` (ADR-0006, TDR-0010). Sender IPs are only needed
        for the per-IP limits (at most 24 h); they are removed after ``IP_RETENTION``.
        """
        now = datetime.now(UTC)
        deleted = await self._repository.delete_expired(self._retention, now)
        anonymized = await self._repository.anonymize_ips_older_than(now - IP_RETENTION)
        await self._repository.purge_expired_captcha_challenges(now)
        await self._repository.purge_deletion_log(now - DELETION_LOG_RETENTION)
        if deleted or anonymized:
            logger.info("contact_messages_purged", deleted=deleted, ips_removed=anonymized)
        return deleted


def _as_utc(value: datetime) -> datetime:
    """SQLite returns naive timestamps; they are UTC."""
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def _event_summary(event: ContactMessageEvent) -> str:
    if event.action == EventAction.NOTES:
        return "Notizen geändert"
    old = MessageStatus(event.old_value).label if event.old_value else "?"
    new = MessageStatus(event.new_value).label if event.new_value else "?"
    return f"Status: {old} → {new}"
