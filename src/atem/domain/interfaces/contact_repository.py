"""Contact Repository Interface (ABC)."""

from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from atem.domain.models.contact import (
    ContactMessage,
    ContactMessageEvent,
    MessageQuery,
    MessageStatus,
    RetentionPolicy,
)


class IContactRepository(ABC):
    """Abstract interface defining operations for contact inquiries."""

    @abstractmethod
    async def create_message(self, message: ContactMessage) -> ContactMessage:
        """Store incoming contact inquiry."""

    @abstractmethod
    async def search_messages(self, query: MessageQuery) -> tuple[list[ContactMessage], int]:
        """One page of messages matching the query, and the number of all matches."""

    @abstractmethod
    async def get_message_by_id(self, message_id: UUID) -> ContactMessage | None:
        """Fetch single contact message by ID."""

    @abstractmethod
    async def update_message(self, message: ContactMessage) -> ContactMessage:
        """Persist status, notes and confirmation flag."""

    @abstractmethod
    async def add_event(self, event: ContactMessageEvent) -> None:
        """Append an entry to the history of a message."""

    @abstractmethod
    async def list_events(self, message_id: UUID) -> list[ContactMessageEvent]:
        """History of a message, oldest first, with the e-mail of the acting admin."""

    @abstractmethod
    async def delete_message(self, message_id: UUID) -> bool:
        """Delete message by ID."""

    @abstractmethod
    async def find_by_sender_email(self, email: str) -> list[ContactMessage]:
        """All messages from an address (case-insensitive), oldest first."""

    @abstractmethod
    async def count_by_status(self) -> dict[MessageStatus, int]:
        """Number of messages per status (statuses without messages may be missing)."""

    @abstractmethod
    async def count_messages_from_ip(self, ip_address: str, since: datetime) -> int:
        """Count messages sent from an IP address since the given time (rate limiting)."""

    @abstractmethod
    async def confirmation_sent_since(self, email_hash: str, since: datetime) -> bool:
        """Return True if a confirmation mail went to this address since the given time."""

    @abstractmethod
    async def delete_expired(self, policy: RetentionPolicy, now: datetime) -> int:
        """Delete messages whose retention period is over, with their history; return the count."""

    @abstractmethod
    async def anonymize_ips_older_than(self, cutoff: datetime) -> int:
        """Remove the sender IP of messages created before ``cutoff``; return the count."""

    @abstractmethod
    async def register_captcha_challenge(self, challenge_id: str, expires_at: datetime) -> bool:
        """Mark a solved captcha challenge as used; False if it was used before (replay)."""

    @abstractmethod
    async def purge_expired_captcha_challenges(self, now: datetime) -> int:
        """Remove used-challenge records that expired."""
