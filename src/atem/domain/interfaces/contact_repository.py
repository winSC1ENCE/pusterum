"""Contact Repository Interface (ABC)."""

from abc import ABC, abstractmethod
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
        """Update message status or notes."""

    @abstractmethod
    async def delete_message(self, message_id: UUID) -> bool:
        """Delete message by ID."""
