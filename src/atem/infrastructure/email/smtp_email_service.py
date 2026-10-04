"""SMTP Email Service implementation using aiosmtplib (implicit TLS or STARTTLS)."""

from email.message import EmailMessage
from email.utils import formataddr

import aiosmtplib
import structlog

from atem.domain.interfaces.email_service import IEmailService
from atem.domain.models.contact import ContactMessage
from atem.infrastructure.config.settings import Settings

logger = structlog.get_logger(__name__)

CONFIRMATION_SUBJECT = "Ihre Nachricht an PUSTERUM"
CONFIRMATION_BODY = (
    "Guten Tag\n\n"
    "Vielen Dank für Ihre Nachricht über www.pusterum.be. Sie ist bei mir eingegangen und\n"
    "ich melde mich so bald wie möglich persönlich bei Ihnen.\n\n"
    "Falls Sie diese Nachricht nicht ausgelöst haben, können Sie diese E-Mail ignorieren.\n\n"
    "Herzliche Grüsse\n"
    "Stephanie\n"
    "PUSTERUM – Praxis für Atem- und Körpertherapie\n"
)


class SmtpEmailService(IEmailService):
    """Asynchronous SMTP email delivery service."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def send_contact_notification(self, message: ContactMessage) -> bool:
        """Notify the practice; replying answers the visitor directly (Reply-To)."""
        if not self._settings.MAIL_ENABLED:
            return True
        try:
            msg = EmailMessage()
            msg["From"] = formataddr(("PUSTERUM Website", self._settings.MAIL_FROM))
            msg["To"] = self._settings.MAIL_TO
            msg["Reply-To"] = formataddr((message.sender_name, message.sender_email))
            msg["Subject"] = f"Neue Anfrage: {message.subject}"
            msg.set_content(
                "Neue Kontaktanfrage über die Website:\n\n"
                f"Name: {message.sender_name}\n"
                f"E-Mail: {message.sender_email}\n"
                f"Telefon: {message.sender_phone or 'Nicht angegeben'}\n"
                f"Betreff: {message.subject}\n\n"
                f"Nachricht:\n{message.message}\n"
            )
        except ValueError:
            # EmailMessage rejects CR/LF in headers – never build a header from raw input.
            logger.warning("email_build_rejected", message_id=str(message.id))
            return False
        return await self._send(msg, "notification")

    async def send_contact_confirmation(self, recipient: str) -> bool:
        """Send the fixed-text receipt (no visitor-controlled content)."""
        if not self._settings.MAIL_ENABLED:
            return True
        try:
            msg = EmailMessage()
            msg["From"] = formataddr(("PUSTERUM", self._settings.MAIL_FROM))
            msg["To"] = recipient
            msg["Subject"] = CONFIRMATION_SUBJECT
            msg.set_content(CONFIRMATION_BODY)
        except ValueError:
            logger.warning("email_build_rejected", kind="confirmation")
            return False
        return await self._send(msg, "confirmation")

    async def _send(self, msg: EmailMessage, kind: str) -> bool:
        settings = self._settings
        try:
            await aiosmtplib.send(
                msg,
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                username=settings.SMTP_USER or None,
                password=settings.SMTP_PASSWORD or None,
                use_tls=settings.SMTP_USE_TLS,
                start_tls=settings.SMTP_STARTTLS,
                timeout=settings.SMTP_TIMEOUT_SECONDS,
            )
        except Exception:
            logger.exception("email_delivery_failed", kind=kind)
            return False
        logger.info("email_sent", kind=kind)
        return True
