"""SMTP Email Service implementation using aiosmtplib (implicit TLS or STARTTLS)."""

from datetime import datetime
from email.message import EmailMessage
from email.utils import formataddr
from zoneinfo import ZoneInfo

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

NOTIFICATION_BODY = (
    "Neue Kontaktanfrage über die Website\n\n"
    "Von: {first_name}\n"
    "Betreff: {subject}\n\n"
    "Nachricht und Kontaktdaten stehen aus Datenschutzgründen nur im Admin-Bereich:\n"
    "{url}\n"
)

LOCKOUT_SUBJECT = "PUSTERUM: Anmeldung vorübergehend gesperrt"
LOCKOUT_BODY = (
    "Guten Tag\n\n"
    "Für Ihr Administrationskonto auf www.pusterum.be gab es mehrere fehlgeschlagene\n"
    "Anmeldeversuche (zuletzt von der IP-Adresse {ip}).\n\n"
    "Anmeldungen von unbekannten Geräten sind deshalb bis {until} Uhr gesperrt.\n"
    "Geräte, auf denen Sie sich bereits angemeldet haben, funktionieren weiterhin.\n\n"
    "Waren Sie das nicht, ist keine Aktion nötig: Ohne Ihr Passwort und Ihren\n"
    "Zwei-Faktor-Code ist keine Anmeldung möglich.\n"
)
RESET_NOTICE_SUBJECT = "PUSTERUM: Ihr Passwort wurde zurückgesetzt"
RESET_NOTICE_BODY = (
    "Guten Tag\n\n"
    "Das Passwort Ihres Administrationskontos auf www.pusterum.be wurde soeben vom Betreiber\n"
    "zurückgesetzt. Alle bisherigen Anmeldungen sind beendet.\n\n"
    "Haben Sie das nicht veranlasst, melden Sie sich bitte umgehend beim Betreiber.\n"
)
LOCAL_TIMEZONE = ZoneInfo("Europe/Zurich")


class SmtpEmailService(IEmailService):
    """Asynchronous SMTP email delivery service."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def send_contact_notification(self, message: ContactMessage) -> bool:
        """Notify the practice with first name, subject and a link to the admin (ADR-0006).

        No message text, phone or e-mail address: the mailbox holds no copy of health data.
        """
        if not self._settings.MAIL_ENABLED:
            return True
        try:
            msg = EmailMessage()
            msg["From"] = formataddr(("PUSTERUM Website", self._settings.MAIL_FROM))
            msg["To"] = self._settings.MAIL_TO
            msg["Subject"] = f"Neue Anfrage: {message.subject}"
            msg.set_content(
                NOTIFICATION_BODY.format(
                    first_name=message.first_name,
                    subject=message.subject,
                    url=f"{self._settings.PUBLIC_BASE_URL}/admin/messages/{message.id}",
                )
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

    async def send_lockout_notice(
        self, recipient: str, ip_address: str, locked_until: datetime
    ) -> bool:
        """Security notice to the account owner (fixed text, no secrets)."""
        if not self._settings.MAIL_ENABLED:
            return True
        try:
            msg = EmailMessage()
            msg["From"] = formataddr(("PUSTERUM Website", self._settings.MAIL_FROM))
            msg["To"] = recipient
            msg["Subject"] = LOCKOUT_SUBJECT
            until = locked_until.astimezone(LOCAL_TIMEZONE).strftime("%d.%m.%Y %H:%M")
            msg.set_content(LOCKOUT_BODY.format(ip=ip_address, until=until))
        except ValueError:
            logger.warning("email_build_rejected", kind="lockout_notice")
            return False
        return await self._send(msg, "lockout_notice")

    async def send_password_reset_notice(self, recipient: str) -> bool:
        """Security notice to the account owner after an operator password reset."""
        if not self._settings.MAIL_ENABLED:
            return True
        try:
            msg = EmailMessage()
            msg["From"] = formataddr(("PUSTERUM Website", self._settings.MAIL_FROM))
            msg["To"] = recipient
            msg["Subject"] = RESET_NOTICE_SUBJECT
            msg.set_content(RESET_NOTICE_BODY)
        except ValueError:
            logger.warning("email_build_rejected", kind="password_reset_notice")
            return False
        return await self._send(msg, "password_reset_notice")

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
