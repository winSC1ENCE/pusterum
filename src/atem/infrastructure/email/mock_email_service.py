"""Mock Email Service for local development and testing."""

import structlog

from atem.domain.interfaces.email_service import IEmailService
from atem.domain.models.contact import ContactMessage

logger = structlog.get_logger(__name__)


class MockEmailService(IEmailService):
    """Logs transactional emails to structlog without outbound network calls."""

    def __init__(self) -> None:
        self.sent_messages: list[ContactMessage] = []

    async def send_contact_notification(self, message: ContactMessage) -> bool:
        """Log mock notification email."""
        logger.info(
            "MOCK EMAIL: Notification to therapist",
            sender_name=message.sender_name,
            sender_email=message.sender_email,
            subject=message.subject,
        )
        self.sent_messages.append(message)
        return True

    async def send_contact_confirmation(self, message: ContactMessage) -> bool:
        """Log mock confirmation email."""
        logger.info(
            "MOCK EMAIL: Confirmation to client",
            recipient=message.sender_email,
            subject=f"Empfangsbestätigung: {message.subject}",
        )
        return True
