"""Tests for the contact form protection layers, mails, retention and admin message handling."""

import time
from datetime import timedelta
from email.message import EmailMessage
from typing import Any

import pytest
from litestar import Litestar
from litestar.testing import AsyncTestClient
from pydantic import ValidationError

from atem.application.dto.contact import CreateContactMessageDTO
from atem.application.services.contact_service import CAPTCHA_REQUIRED, ContactService
from atem.cli import build_parser
from atem.domain.exceptions import (
    EntityNotFoundException,
    RateLimitedException,
    ValidationException,
)
from atem.domain.models.contact import ContactMessage, MessageStatus
from atem.infrastructure.captcha.altcha_captcha import AltchaCaptcha
from atem.infrastructure.config.settings import Settings
from atem.infrastructure.email.mock_email_service import MockEmailService
from atem.infrastructure.email.smtp_email_service import CONFIRMATION_BODY, SmtpEmailService
from atem.presentation.security.form_token import issue_form_token, verify_form_token
from tests.conftest import contact_form_payload, solve_altcha

ADMIN = {"username": "admin", "password": "admin-secure-init-pass-change-me"}


def _dto(**overrides: Any) -> CreateContactMessageDTO:
    data = {
        "sender_name": "Maria Muster",
        "sender_email": "maria@muster.ch",
        "subject": "Terminanfrage",
        "message": "Guten Tag, ich hätte gerne einen Termin.",
        **overrides,
    }
    return CreateContactMessageDTO(**data)


async def _submit(service: ContactService, ip: str = "198.51.100.5", **overrides: Any) -> Any:
    return await service.submit_contact_form(
        _dto(**overrides),
        client_ip=ip,
        captcha_payload=solve_altcha(service.create_captcha_challenge()),
    )


# ------------------------------------------------------------------------ form token
def test_form_token_window_and_signature() -> None:
    key = b"k" * 32
    now = time.time()
    token = issue_form_token(key, now=now - 10)
    assert verify_form_token(key, token, now=now)
    assert not verify_form_token(key, issue_form_token(key, now=now), now=now)  # too fast
    assert not verify_form_token(key, issue_form_token(key, now=now - 3 * 3600), now=now)
    assert not verify_form_token(b"x" * 32, token, now=now)  # wrong key
    assert not verify_form_token(key, token[:-1] + "0", now=now)  # tampered
    assert not verify_form_token(key, "garbage", now=now)


# --------------------------------------------------------------------------- captcha
def test_altcha_rejects_invalid_and_expired_payloads() -> None:
    captcha = AltchaCaptcha("k" * 64, max_number=500, expires_after=timedelta(minutes=5))
    payload = solve_altcha(captcha.create_challenge())
    verified = captcha.verify(payload)
    assert verified is not None
    assert len(verified.challenge_id) == 64

    other_key = AltchaCaptcha("x" * 64, max_number=500, expires_after=timedelta(minutes=5))
    assert other_key.verify(payload) is None
    assert captcha.verify("") is None
    assert captcha.verify("not-base64!!") is None
    assert captcha.verify("a" * 5000) is None

    expired = AltchaCaptcha("k" * 64, max_number=500, expires_after=timedelta(seconds=-1))
    assert expired.verify(solve_altcha(expired.create_challenge())) is None


async def test_captcha_is_required_and_cannot_be_replayed(contact_service: ContactService) -> None:
    with pytest.raises(ValidationException, match="Sicherheitsprüfung"):
        await contact_service.submit_contact_form(_dto(), client_ip="1.2.3.4", captcha_payload="")

    payload = solve_altcha(contact_service.create_captcha_challenge())
    await contact_service.submit_contact_form(_dto(), client_ip="1.2.3.4", captcha_payload=payload)
    with pytest.raises(ValidationException) as replay:
        await contact_service.submit_contact_form(
            _dto(), client_ip="1.2.3.4", captcha_payload=payload
        )
    assert replay.value.message == CAPTCHA_REQUIRED


# ---------------------------------------------------------------------- rate limits
async def test_ip_rate_limit_per_hour(contact_service: ContactService) -> None:
    for _ in range(3):
        await _submit(contact_service, ip="203.0.113.99")
    with pytest.raises(RateLimitedException):
        await _submit(contact_service, ip="203.0.113.99")
    # Other visitors are not affected
    await _submit(contact_service, ip="203.0.113.100")


async def test_confirmation_mail_once_per_address_and_day(
    contact_service: ContactService, email_service: MockEmailService
) -> None:
    first = await _submit(contact_service, ip="10.0.0.1")
    second = await _submit(contact_service, ip="10.0.0.2", sender_email="MARIA@muster.ch ")
    assert first.confirmation_sent is True
    assert second.confirmation_sent is False
    assert email_service.confirmations == ["maria@muster.ch"]
    assert len(email_service.sent_messages) == 2


def test_dto_rejects_header_injection_and_garbage() -> None:
    with pytest.raises(ValidationError):
        _dto(sender_name="Eve\r\nBcc: victim@example.com")
    with pytest.raises(ValidationError):
        _dto(subject="Hallo\nBcc: x@example.com")
    with pytest.raises(ValidationError):
        _dto(sender_phone="<script>")


# ---------------------------------------------------------------------------- mails
@pytest.fixture
def smtp_capture(monkeypatch: pytest.MonkeyPatch) -> list[tuple[EmailMessage, dict[str, Any]]]:
    sent: list[tuple[EmailMessage, dict[str, Any]]] = []

    async def fake_send(message: EmailMessage, **kwargs: Any) -> None:
        sent.append((message, kwargs))

    monkeypatch.setattr("aiosmtplib.send", fake_send)
    return sent


def _smtp_settings(**overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "ENVIRONMENT": "test",
        "MAIL_ENABLED": True,
        "SMTP_STARTTLS": True,
        "SMTP_HOST": "mail.example",
        **overrides,
    }
    return Settings(_env_file=None, **values)  # type: ignore[call-arg]


async def test_confirmation_mail_contains_no_visitor_text(
    smtp_capture: list[tuple[EmailMessage, dict[str, Any]]],
) -> None:
    service = SmtpEmailService(_smtp_settings())
    assert await service.send_contact_confirmation("maria@muster.ch")
    message, kwargs = smtp_capture[0]
    assert message["To"] == "maria@muster.ch"
    assert message.get_content().strip() == CONFIRMATION_BODY.strip()
    assert kwargs["start_tls"] is True
    assert kwargs["timeout"] == 15


async def test_notification_mail_sets_reply_to(
    smtp_capture: list[tuple[EmailMessage, dict[str, Any]]],
) -> None:
    service = SmtpEmailService(_smtp_settings())
    message = ContactMessage(
        sender_name="Maria Muster",
        sender_email="maria@muster.ch",
        subject="Termin",
        message="Hallo",
    )
    assert await service.send_contact_notification(message)
    sent, _ = smtp_capture[0]
    assert "maria@muster.ch" in sent["Reply-To"]
    assert sent["To"] == "kontakt@pusterum.be"


async def test_mail_build_and_delivery_failures_are_contained(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = SmtpEmailService(_smtp_settings())
    injected = ContactMessage(
        sender_name="x", sender_email="a@b.ch", subject="a\nBcc: evil@x.ch", message="m"
    )
    assert await service.send_contact_notification(injected) is False

    async def broken_send(*_: Any, **__: Any) -> None:
        raise OSError("connection refused")

    monkeypatch.setattr("aiosmtplib.send", broken_send)
    assert await service.send_contact_confirmation("a@b.ch") is False

    disabled = SmtpEmailService(_smtp_settings(MAIL_ENABLED=False, SMTP_STARTTLS=False))
    assert await disabled.send_contact_confirmation("a@b.ch") is True
    assert await disabled.send_contact_notification(injected) is True


# ------------------------------------------------------------ retention & management
async def test_message_management_and_retention(contact_service: ContactService) -> None:
    saved = await _submit(contact_service)
    updated = await contact_service.update_message_status(saved.id, MessageStatus.REPLIED)
    assert updated.status == MessageStatus.REPLIED

    assert await contact_service.purge_expired(timedelta(days=365)) == 0
    assert await contact_service.purge_expired(timedelta(seconds=-1)) == 1
    with pytest.raises(EntityNotFoundException):
        await contact_service.delete_message(saved.id)
    with pytest.raises(EntityNotFoundException):
        await contact_service.update_message_status(saved.id, MessageStatus.READ)


def test_cli_has_purge_command() -> None:
    assert build_parser().parse_args(["purge-messages"]).command == "purge-messages"


# ----------------------------------------------------------------------------- HTTP
async def test_altcha_challenge_endpoint(app_client: AsyncTestClient[Litestar]) -> None:
    response = await app_client.get("/altcha/challenge")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert {"algorithm", "challenge", "salt", "signature", "maxNumber"} <= response.json().keys()


async def test_http_honeypot_missing_token_and_missing_captcha(
    app_client: AsyncTestClient[Litestar],
) -> None:
    fields = {
        "sender_name": "Erika Muster",
        "sender_email": "erika@muster.ch",
        "message": "Guten Tag, ich möchte einen Termin vereinbaren.",
    }
    no_token = await app_client.post("/contact", data=fields)
    assert "zu schnell abgeschickt oder ist abgelaufen" in no_token.text

    honeypot = await app_client.post(
        "/contact", data=await contact_form_payload(app_client, website_url="http://spam", **fields)
    )
    assert "konnte nicht gesendet werden" in honeypot.text

    payload = await contact_form_payload(app_client, **fields)
    payload["altcha"] = ""
    no_captcha = await app_client.post("/contact", data=payload)
    assert "Sicherheitsprüfung" in no_captcha.text
    assert 'name="form_token"' in no_captcha.text  # fresh token for the next attempt


async def test_admin_can_change_status_and_delete_messages(
    app_client: AsyncTestClient[Litestar],
) -> None:
    await app_client.post(
        "/contact",
        data=await contact_form_payload(
            app_client,
            sender_name="Erika Muster",
            sender_email="erika@muster.ch",
            message="Guten Tag, ich möchte einen Termin vereinbaren.",
        ),
    )
    await app_client.post("/admin/login", data=ADMIN)
    dashboard = await app_client.get("/admin")
    message_id = dashboard.text.split('id="message-', 1)[1].split('"', 1)[0]

    row = await app_client.post(f"/admin/messages/{message_id}/status", data={"status": "READ"})
    assert row.status_code == 200
    assert 'value="READ" selected' in row.text
    invalid = await app_client.post(f"/admin/messages/{message_id}/status", data={"status": "X"})
    assert invalid.status_code == 400

    deleted = await app_client.post(f"/admin/messages/{message_id}/delete")
    assert deleted.status_code == 200
    again = await app_client.post(f"/admin/messages/{message_id}/delete")
    assert again.status_code == 404
