"""Email Notification Service Interface (ABC)."""

from abc import ABC, abstractmethod
from datetime import datetime

from atem.domain.models.contact import ContactMessage


class IEmailService(ABC):
    """Abstract interface defining transactional email delivery."""

    @abstractmethod
    async def send_contact_notification(self, message: ContactMessage) -> bool:
        """Notify the practice about a new message (Reply-To = sender)."""

    @abstractmethod
    async def send_contact_confirmation(self, recipient: str) -> bool:
        """Send a fixed-text receipt to the sender.

        Deliberately takes only the address: no visitor-controlled text (name, subject,
        message) is ever mirrored to an arbitrary address – the form cannot be abused
        to relay spam.
        """

    @abstractmethod
    async def send_lockout_notice(
        self, recipient: str, ip_address: str, locked_until: datetime
    ) -> bool:
        """Tell an admin that logins from unknown devices are temporarily locked."""
