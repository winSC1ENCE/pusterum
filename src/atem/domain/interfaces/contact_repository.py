"""Contact Repository Interface (ABC)."""

from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from atem.domain.models.contact import ContactMessage, MessageStatus


class IContactRepository(ABC):
    """Abstract interface defining operations for contact inquiries."""

    @abstractmethod
    async def create_message(self, message: ContactMessage) -> ContactMessage:
        """Store incoming contact inquiry."""

    @abstractmethod
    async def get_messages(
        self,
        *,
        status: MessageStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ContactMessage]:
        """Fetch contact messages with optional status filter and pagination."""

    @abstractmethod
    async def get_message_by_id(self, message_id: UUID) -> ContactMessage | None:
        """Fetch single contact message by ID."""

    @abstractmethod
    async def update_message(self, message: ContactMessage) -> ContactMessage:
        """Persist status, notes and confirmation flag."""

    @abstractmethod
    async def delete_message(self, message_id: UUID) -> bool:
        """Delete message by ID."""

    @abstractmethod
    async def count_messages_from_ip(self, ip_address: str, since: datetime) -> int:
        """Count messages sent from an IP address since the given time (rate limiting)."""

    @abstractmethod
    async def confirmation_sent_since(self, email_hash: str, since: datetime) -> bool:
        """Return True if a confirmation mail went to this address since the given time."""

    @abstractmethod
    async def delete_messages_older_than(self, cutoff: datetime) -> int:
        """Delete messages created before ``cutoff`` (retention); return the count."""

    @abstractmethod
    async def register_captcha_challenge(self, challenge_id: str, expires_at: datetime) -> bool:
        """Mark a solved captcha challenge as used; False if it was used before (replay)."""

    @abstractmethod
    async def purge_expired_captcha_challenges(self, now: datetime) -> int:
        """Remove used-challenge records that expired."""
