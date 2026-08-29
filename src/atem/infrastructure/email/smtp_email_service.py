"""SMTP Email Service implementation using aiosmtplib."""

from email.message import EmailMessage

import aiosmtplib
import structlog

from atem.domain.interfaces.email_service import IEmailService
from atem.domain.models.contact import ContactMessage
from atem.infrastructure.config.settings import Settings

logger = structlog.get_logger(__name__)


class SmtpEmailService(IEmailService):
    """Asynchronous SMTP email delivery service."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def send_contact_notification(self, message: ContactMessage) -> bool:
        """Send notification email to therapist."""
        if not self._settings.MAIL_ENABLED:
            logger.info(
                "Email disabled in settings, skipping notification",
                sender=message.sender_email,
            )
            return True

        msg = EmailMessage()
        msg["From"] = self._settings.MAIL_FROM
        msg["To"] = self._settings.MAIL_TO
        msg["Subject"] = f"Neue Anfrage von {message.sender_name}: {message.subject}"

        body = (
            f"Neue Kontaktanfrage über die Website:\n\n"
            f"Name: {message.sender_name}\n"
            f"E-Mail: {message.sender_email}\n"
            f"Telefon: {message.sender_phone or 'Nicht angegeben'}\n"
            f"Betreff: {message.subject}\n\n"
            f"Nachricht:\n{message.message}\n"
        )
        msg.set_content(body)

        try:
            await aiosmtplib.send(
                msg,
                hostname=self._settings.SMTP_HOST,
                port=self._settings.SMTP_PORT,
                username=self._settings.SMTP_USER if self._settings.SMTP_USER else None,
                password=self._settings.SMTP_PASSWORD if self._settings.SMTP_PASSWORD else None,
                use_tls=self._settings.SMTP_USE_TLS,
            )
            logger.info("Sent notification email successfully", to=self._settings.MAIL_TO)
        except Exception:
            logger.exception("Failed to deliver SMTP email")
            return False
        else:
            return True

    async def send_contact_confirmation(self, message: ContactMessage) -> bool:
        """Send receipt confirmation email to the client."""
        if not self._settings.MAIL_ENABLED:
            return True

        msg = EmailMessage()
        msg["From"] = self._settings.MAIL_FROM
        msg["To"] = message.sender_email
        msg["Subject"] = f"Empfangsbestätigung: {message.subject}"

        body = (
            f"Guten Tag {message.sender_name}\n\n"
            "Vielen Dank für Ihre Kontaktaufnahme. Ihre Nachricht ist erfolgreich bei mir "
            "eingegangen.\n"
            "Ich werde mich zeitnah bei Ihnen melden.\n\n"
            "Herzliche Grüsse\n"
            "Praxis für Atemtherapie\n"
        )
        msg.set_content(body)

        try:
            await aiosmtplib.send(
                msg,
                hostname=self._settings.SMTP_HOST,
                port=self._settings.SMTP_PORT,
                username=self._settings.SMTP_USER if self._settings.SMTP_USER else None,
                password=self._settings.SMTP_PASSWORD if self._settings.SMTP_PASSWORD else None,
                use_tls=self._settings.SMTP_USE_TLS,
            )
        except Exception:
            logger.exception("Failed to deliver confirmation email")
            return False
        else:
            return True
