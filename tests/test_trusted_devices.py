"""Trusted devices: third parties can lock out unknown devices, never the owner's devices."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from litestar import Litestar
from litestar.testing import AsyncTestClient

from atem.application.dto.auth import LoginRequestDTO
from atem.application.services.auth_service import AuthService
from atem.domain.exceptions import AuthenticationException, EntityNotFoundException
from atem.domain.interfaces.email_service import IEmailService
from atem.domain.models.user import (
    MAX_FAILED_DEVICE_LOGINS,
    MAX_FAILED_LOGINS,
    DeviceClaim,
    User,
)
from atem.infrastructure.email.mock_email_service import MockEmailService
from atem.presentation.security.device_cookie import (
    DEVICE_COOKIE,
    DEVICE_COOKIE_MAX_AGE,
    issue_device_token,
    read_device_token,
)

ADMIN_PASSWORD = "admin-secure-init-pass-change-me"
ATTACKER_IP = "203.0.113.66"
OWNER_IP = "198.51.100.10"
KEY = b"k" * 32


def _login(password: str) -> LoginRequestDTO:
    return LoginRequestDTO(username="stephanie", password=password)


async def _admin(auth_service: AuthService) -> DeviceClaim:
    user = await auth_service.create_admin("stephanie", "kontakt@pusterum.be", ADMIN_PASSWORD)
    return DeviceClaim(user_id=user.id, device_id="owner-laptop", issued_at=datetime.now(UTC))


async def _lock_account(auth_service: AuthService) -> None:
    for _ in range(MAX_FAILED_LOGINS):
        with pytest.raises(AuthenticationException):
            await auth_service.authenticate(_login("wrong"), ATTACKER_IP)


# ------------------------------------------------------------------------- tokens
def test_device_token_roundtrip_and_rejections() -> None:
    user_id = uuid4()
    now = 1_800_000_000.0
    token = issue_device_token(KEY, user_id, now=now)
    claim = read_device_token(KEY, token, now=now + 60)
    assert claim is not None
    assert claim.user_id == user_id
    assert claim.issued_at == datetime.fromtimestamp(int(now), UTC)

    assert read_device_token(b"x" * 32, token, now=now) is None  # other key
    assert read_device_token(KEY, token[:-1] + "0", now=now) is None  # tampered
    assert read_device_token(KEY, token, now=now + DEVICE_COOKIE_MAX_AGE + 1) is None  # expired
    assert read_device_token(KEY, token, now=now - 60) is None  # from the future
    assert read_device_token(KEY, "", now=now) is None
    assert read_device_token(KEY, "a.b.c", now=now) is None
    forged = issue_device_token(KEY, user_id, now=now).replace(str(user_id), "not-a-uuid")
    assert read_device_token(KEY, forged, now=now) is None


def test_trusts_device_rules() -> None:
    user = User(username="u", email="u@example.ch", password_hash="x")
    issued = datetime(2026, 10, 4, 12, 0, tzinfo=UTC)
    claim = DeviceClaim(user_id=user.id, device_id="d", issued_at=issued)
    assert user.trusts_device(claim)
    assert not user.trusts_device(None)
    assert not user.trusts_device(DeviceClaim(user_id=uuid4(), device_id="d", issued_at=issued))

    user.password_changed_at = issued - timedelta(days=1)
    assert user.trusts_device(claim)
    user.password_changed_at = (issued + timedelta(minutes=5)).replace(tzinfo=None)  # naive
    assert not user.trusts_device(claim)  # devices from before a password change lose trust


# ------------------------------------------------------------------- service layer
async def test_trusted_device_logs_in_despite_account_lockout(auth_service: AuthService) -> None:
    device = await _admin(auth_service)
    await _lock_account(auth_service)

    # Unknown devices – even with the correct password – stay locked out
    with pytest.raises(AuthenticationException):
        await auth_service.authenticate(_login(ADMIN_PASSWORD), OWNER_IP)

    # The owner's trusted device is not affected
    result = await auth_service.authenticate(_login(ADMIN_PASSWORD), OWNER_IP, device)
    assert result.user.username == "stephanie"

    # ...and the owner's login does not reset the lockout for the attacker
    with pytest.raises(AuthenticationException):
        await auth_service.authenticate(_login(ADMIN_PASSWORD), ATTACKER_IP)


async def test_trusted_device_has_its_own_failure_limit(auth_service: AuthService) -> None:
    device = await _admin(auth_service)
    for _ in range(MAX_FAILED_DEVICE_LOGINS):
        with pytest.raises(AuthenticationException):
            await auth_service.authenticate(_login("wrong"), OWNER_IP, device)
    with pytest.raises(AuthenticationException):  # this device is throttled now
        await auth_service.authenticate(_login(ADMIN_PASSWORD), OWNER_IP, device)

    # Device failures neither lock the account nor another device
    other = DeviceClaim(user_id=device.user_id, device_id="owner-phone", issued_at=device.issued_at)
    assert (await auth_service.authenticate(_login(ADMIN_PASSWORD), OWNER_IP, other)).user
    assert (await auth_service.authenticate(_login(ADMIN_PASSWORD), ATTACKER_IP)).user


async def test_device_of_another_user_is_ignored(auth_service: AuthService) -> None:
    await _admin(auth_service)
    await _lock_account(auth_service)
    foreign = DeviceClaim(user_id=uuid4(), device_id="x", issued_at=datetime.now(UTC))
    with pytest.raises(AuthenticationException):
        await auth_service.authenticate(_login(ADMIN_PASSWORD), OWNER_IP, foreign)


async def test_lockout_notice_is_sent_once_per_lockout(
    auth_service: AuthService, email_service: IEmailService
) -> None:
    assert isinstance(email_service, MockEmailService)
    await _admin(auth_service)
    await _lock_account(auth_service)
    for _ in range(3):  # attempts during the lockout do not trigger further mails
        with pytest.raises(AuthenticationException):
            await auth_service.authenticate(_login("wrong"), ATTACKER_IP)
    assert email_service.lockout_notices == ["kontakt@pusterum.be"]


async def test_lockout_notice_failure_does_not_break_login(
    auth_service: AuthService, email_service: IEmailService, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def broken(*_: object) -> bool:
        raise ConnectionError("smtp down")

    monkeypatch.setattr(email_service, "send_lockout_notice", broken)
    await _admin(auth_service)
    await _lock_account(auth_service)  # still the generic AuthenticationException


async def test_operator_unlock(auth_service: AuthService) -> None:
    await _admin(auth_service)
    await _lock_account(auth_service)
    await auth_service.unlock("stephanie")
    assert (await auth_service.authenticate(_login(ADMIN_PASSWORD), OWNER_IP)).user
    with pytest.raises(EntityNotFoundException):
        await auth_service.unlock("ghost")


# ---------------------------------------------------------------------------- HTTP
async def _post_login(client: AsyncTestClient[Litestar], password: str) -> str:
    response = await client.post(
        "/admin/login",
        data={"username": "admin", "password": password},
        follow_redirects=False,
    )
    return response.headers.get("location", "")


async def test_device_cookie_protects_owner_over_http(
    app_client: AsyncTestClient[Litestar],
) -> None:
    first = await app_client.post(
        "/admin/login",
        data={"username": "admin", "password": ADMIN_PASSWORD},
        follow_redirects=False,
    )
    cookie_header = first.headers.get("set-cookie", "")
    assert DEVICE_COOKIE in cookie_header
    assert "Path=/admin" in cookie_header and "HttpOnly" in cookie_header
    device_token = app_client.cookies.get(DEVICE_COOKIE)
    assert device_token
    await app_client.post("/admin/logout")

    # An attacker (no device cookie) locks the account
    app_client.cookies.delete(DEVICE_COOKIE)
    for _ in range(MAX_FAILED_LOGINS):
        assert await _post_login(app_client, "wrong") == ""
    assert await _post_login(app_client, ADMIN_PASSWORD) == ""

    # The owner's browser still gets in
    app_client.cookies.set(DEVICE_COOKIE, device_token, path="/admin")
    assert await _post_login(app_client, ADMIN_PASSWORD) == "/admin"
