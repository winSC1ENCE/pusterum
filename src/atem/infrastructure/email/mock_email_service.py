"""Mock Email Service for local development and testing."""

from datetime import datetime

import structlog

from atem.domain.interfaces.email_service import IEmailService
from atem.domain.models.contact import ContactMessage

logger = structlog.get_logger(__name__)


class MockEmailService(IEmailService):
    """Records transactional emails in memory without outbound network calls."""

    def __init__(self) -> None:
        self.sent_messages: list[ContactMessage] = []
        self.confirmations: list[str] = []
        self.lockout_notices: list[str] = []

    async def send_contact_notification(self, message: ContactMessage) -> bool:
        """Record mock notification email (no personal data in the log)."""
        logger.info("mock_email_notification", message_id=str(message.id))
        self.sent_messages.append(message)
        return True

    async def send_contact_confirmation(self, recipient: str) -> bool:
        """Record mock confirmation email."""
        logger.info("mock_email_confirmation")
        self.confirmations.append(recipient)
        return True

    async def send_lockout_notice(
        self, recipient: str, ip_address: str, locked_until: datetime
    ) -> bool:
        """Record mock lockout notice."""
        logger.info("mock_email_lockout_notice", ip=ip_address, locked_until=locked_until)
        self.lockout_notices.append(recipient)
        return True
