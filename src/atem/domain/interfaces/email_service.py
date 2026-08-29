"""Email Notification Service Interface (ABC)."""

from abc import ABC, abstractmethod

from atem.domain.models.contact import ContactMessage


class IEmailService(ABC):
    """Abstract interface defining transactional email delivery."""

    @abstractmethod
    async def send_contact_notification(self, message: ContactMessage) -> bool:
        """Send notification email about a new contact message to the therapist."""

    @abstractmethod
    async def send_contact_confirmation(self, message: ContactMessage) -> bool:
        """Send receipt confirmation email to the client."""
