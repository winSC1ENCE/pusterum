"""Tests for the admin security model: guard, CSRF, lockout, rate limits, 2FA, revocation."""

import re
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pyotp
import pytest
from litestar import Litestar
from litestar.testing import AsyncTestClient

from atem.application.dto.auth import LoginRequestDTO
from atem.application.services.auth_service import IP_FAILURE_LIMIT, AuthService
from atem.domain.exceptions import (
    AuthenticationException,
    EntityNotFoundException,
    RateLimitedException,
    ValidationException,
)
from atem.domain.models.user import LOCKOUT_BASE, LOCKOUT_MAX, MAX_FAILED_LOGINS, User
from atem.infrastructure.config.settings import get_settings
from atem.infrastructure.security.fernet_secret_cipher import FernetSecretCipher
from atem.infrastructure.security.pyotp_totp_provider import PyotpTotpProvider
from atem.presentation.security.proxy_headers import parse_networks, resolve_client_ip

ADMIN_PASSWORD = "admin-secure-init-pass-change-me"  # dev/test admin seeded in conftest env
IP = "203.0.113.7"
GUARDED_GET_ROUTES = ["/admin", "/admin/design", "/admin/security"]


# --------------------------------------------------------------------------- helpers
async def login(client: AsyncTestClient[Litestar], password: str = ADMIN_PASSWORD) -> str:
    response = await client.post(
        "/admin/login",
        data={"username": "admin", "password": password},
        follow_redirects=False,
    )
    return response.headers.get("location", "")


async def enable_totp_via_ui(client: AsyncTestClient[Litestar]) -> tuple[str, list[str]]:
    """Enrol 2FA through the security pages; return (secret, recovery codes)."""
    page = await client.post("/admin/security/totp/start")
    secret_match = re.search(
        r'<code class="text-sm text-theme-text-main">([A-Z2-7]+)</code>', page.text
    )
    assert secret_match, "secret not rendered"
    secret = secret_match.group(1)
    confirm = await client.post(
        "/admin/security/totp/confirm", data={"code": pyotp.TOTP(secret).now()}
    )
    assert "Zwei-Faktor-Anmeldung aktiviert" in confirm.text
    codes = re.findall(r">([a-z2-9]{4}-[a-z2-9]{4})<", confirm.text)
    assert len(codes) == 10
    return secret, codes


@pytest.fixture
def require_2fa(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("ADMIN_REQUIRE_2FA", "true")
    get_settings.cache_clear()
    yield
    monkeypatch.delenv("ADMIN_REQUIRE_2FA")
    get_settings.cache_clear()


# ---------------------------------------------------------------------- domain rules
def test_lockout_escalates_exponentially_and_is_capped() -> None:
    now = datetime.now(UTC)
    user = User(username="u", email="u@pusterum.be", password_hash="x")
    for _ in range(MAX_FAILED_LOGINS - 1):
        user.register_failed_login(now)
    assert not user.is_locked(now)

    user.register_failed_login(now)
    assert user.locked_until == now + LOCKOUT_BASE
    user.register_failed_login(now)
    assert user.locked_until == now + LOCKOUT_BASE * 2
    for _ in range(20):
        user.register_failed_login(now)
    assert user.locked_until == now + LOCKOUT_MAX

    user.register_successful_login(now)
    assert user.failed_login_count == 0
    assert not user.is_locked(now)


def test_revoke_sessions_increments_version() -> None:
    user = User(username="u", email="u@pusterum.be", password_hash="x")
    user.revoke_sessions()
    assert user.session_version == 2


def test_fernet_cipher_roundtrip_and_tamper_detection() -> None:
    cipher = FernetSecretCipher(b"k" * 32)
    token = cipher.encrypt("JBSWY3DPEHPK3PXP")
    assert cipher.decrypt(token) == "JBSWY3DPEHPK3PXP"
    with pytest.raises(ValueError, match="tampered"):
        cipher.decrypt(token[:-4] + "AAAA")
    with pytest.raises(ValueError, match="32 bytes"):
        FernetSecretCipher(b"short")


def test_totp_provider_rejects_replay_and_garbage() -> None:
    provider = PyotpTotpProvider()
    secret = provider.generate_secret()
    assert provider.provisioning_uri(secret, "admin").startswith("otpauth://totp/PUSTERUM")
    step = provider.verify(secret, pyotp.TOTP(secret).now(), None)
    assert step is not None
    assert provider.verify(secret, pyotp.TOTP(secret).now(), step) is None  # replay
    assert provider.verify(secret, "abc", None) is None
    assert provider.verify(secret, "000000", None) in (None, step - 1, step, step + 1)


@pytest.mark.parametrize(
    ("peer", "forwarded", "expected"),
    [
        ("172.18.0.5", "198.51.100.9", "198.51.100.9"),  # via trusted Caddy
        ("172.18.0.5", "198.51.100.9, 172.18.0.2", "198.51.100.9"),  # skip trusted hops
        ("198.51.100.1", "10.0.0.1", "198.51.100.1"),  # untrusted peer: header ignored
        ("172.18.0.5", None, "172.18.0.5"),
        ("172.18.0.5", "not-an-ip", "not-an-ip"),
        ("testclient", "198.51.100.9", "testclient"),
    ],
)
def test_resolve_client_ip(peer: str, forwarded: str | None, expected: str) -> None:
    networks = parse_networks(["127.0.0.1/32", "172.16.0.0/12"])
    assert resolve_client_ip(peer, forwarded, networks) == expected


# --------------------------------------------------------------------- service layer
async def _seed_admin(auth_service: AuthService) -> None:
    await auth_service.create_admin("admin", "admin@pusterum.be", ADMIN_PASSWORD)


async def test_unknown_user_and_wrong_password_give_generic_error(
    auth_service: AuthService,
) -> None:
    await _seed_admin(auth_service)
    with pytest.raises(AuthenticationException) as unknown:
        await auth_service.authenticate(LoginRequestDTO(username="nobody", password="x"), IP)
    with pytest.raises(AuthenticationException) as wrong:
        await auth_service.authenticate(LoginRequestDTO(username="admin", password="x"), IP)
    assert unknown.value.message == wrong.value.message


async def test_account_lockout_blocks_even_correct_password(auth_service: AuthService) -> None:
    await _seed_admin(auth_service)
    for _ in range(MAX_FAILED_LOGINS):
        with pytest.raises(AuthenticationException):
            await auth_service.authenticate(LoginRequestDTO(username="admin", password="wrong"), IP)
    with pytest.raises(AuthenticationException):
        await auth_service.authenticate(
            LoginRequestDTO(username="admin", password=ADMIN_PASSWORD), "198.51.100.2"
        )


async def test_ip_rate_limit_across_accounts(auth_service: AuthService) -> None:
    for i in range(IP_FAILURE_LIMIT):
        with pytest.raises(AuthenticationException):
            await auth_service.authenticate(LoginRequestDTO(username=f"user{i}", password="x"), IP)
    with pytest.raises(RateLimitedException):
        await auth_service.authenticate(LoginRequestDTO(username="admin", password="x"), IP)


async def test_totp_and_recovery_code_flow(auth_service: AuthService) -> None:
    await _seed_admin(auth_service)
    first = await auth_service.authenticate(
        LoginRequestDTO(username="admin", password=ADMIN_PASSWORD), IP
    )
    setup = auth_service.start_totp_setup(first.user)
    with pytest.raises(ValidationException):
        await auth_service.confirm_totp_setup(first.user.id, setup.secret, "000000x")
    codes = await auth_service.confirm_totp_setup(
        first.user.id, setup.secret, pyotp.TOTP(setup.secret).now()
    )
    assert await auth_service.count_recovery_codes(first.user.id) == 10

    # Enabling 2FA revoked the old session
    assert await auth_service.get_session_user(first.user.id, first.user.session_version) is None

    second = await auth_service.authenticate(
        LoginRequestDTO(username="admin", password=ADMIN_PASSWORD), IP
    )
    assert second.requires_totp

    # The TOTP code used for enrolment cannot be replayed
    with pytest.raises(AuthenticationException):
        await auth_service.verify_second_factor(first.user.id, pyotp.TOTP(setup.secret).now(), IP)

    # Recovery code works exactly once (case/space insensitive)
    user = await auth_service.verify_second_factor(first.user.id, f" {codes[0].upper()} ", IP)
    assert user.totp_enabled
    with pytest.raises(AuthenticationException):
        await auth_service.verify_second_factor(first.user.id, codes[0], IP)
    assert await auth_service.count_recovery_codes(first.user.id) == 9

    new_codes = await auth_service.regenerate_recovery_codes(first.user.id, ADMIN_PASSWORD)
    assert set(new_codes).isdisjoint(codes)
    with pytest.raises(ValidationException):
        await auth_service.regenerate_recovery_codes(first.user.id, "wrong")

    with pytest.raises(ValidationException):
        await auth_service.disable_totp(first.user.id, "wrong")
    disabled = await auth_service.disable_totp(first.user.id, ADMIN_PASSWORD)
    assert not disabled.totp_enabled
    with pytest.raises(ValidationException, match="nicht aktiv"):
        await auth_service.regenerate_recovery_codes(first.user.id, ADMIN_PASSWORD)


async def test_operator_can_reset_totp(auth_service: AuthService) -> None:
    await _seed_admin(auth_service)
    result = await auth_service.authenticate(
        LoginRequestDTO(username="admin", password=ADMIN_PASSWORD), IP
    )
    setup = auth_service.start_totp_setup(result.user)
    await auth_service.confirm_totp_setup(
        result.user.id, setup.secret, pyotp.TOTP(setup.secret).now()
    )
    await auth_service.reset_totp("admin")
    assert not (await auth_service.get_user(result.user.id)).totp_enabled
    with pytest.raises(EntityNotFoundException):
        await auth_service.reset_totp("ghost")


async def test_change_password_policy_and_revocation(auth_service: AuthService) -> None:
    await _seed_admin(auth_service)
    result = await auth_service.authenticate(
        LoginRequestDTO(username="admin", password=ADMIN_PASSWORD), IP
    )
    with pytest.raises(ValidationException, match="aktuelle Passwort"):
        await auth_service.change_password(result.user.id, "wrong", "ein-neues-passwort!")
    with pytest.raises(ValidationException, match="mindestens 12"):
        await auth_service.change_password(result.user.id, ADMIN_PASSWORD, "kurz")
    with pytest.raises(ValidationException, match="unterscheiden"):
        await auth_service.change_password(result.user.id, ADMIN_PASSWORD, ADMIN_PASSWORD)

    updated = await auth_service.change_password(
        result.user.id, ADMIN_PASSWORD, "ein-neues-passwort!"
    )
    assert updated.session_version == result.user.session_version + 1
    assert await auth_service.get_session_user(result.user.id, updated.session_version)
    assert await auth_service.get_session_user(result.user.id, result.user.session_version) is None


async def test_locked_until_from_naive_database_value(auth_service: AuthService) -> None:
    """SQLite returns naive datetimes – the lock check must still work."""
    await _seed_admin(auth_service)
    user = await auth_service._user_repository.get_by_username("admin")
    assert user is not None
    user.locked_until = (datetime.now(UTC) + timedelta(minutes=5)).replace(tzinfo=None)
    await auth_service._user_repository.update_user(user)
    with pytest.raises(AuthenticationException):
        await auth_service.authenticate(
            LoginRequestDTO(username="admin", password=ADMIN_PASSWORD), IP
        )


# ------------------------------------------------------------------------ HTTP layer
@pytest.mark.parametrize("path", GUARDED_GET_ROUTES)
async def test_guard_redirects_anonymous_browsers(
    app_client: AsyncTestClient[Litestar], path: str
) -> None:
    response = await app_client.get(path, follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "/admin/login"


async def test_guard_answers_api_and_htmx_with_401(app_client: AsyncTestClient[Litestar]) -> None:
    api = await app_client.get("/admin/images/list")
    assert api.status_code == 401
    htmx = await app_client.post(
        "/admin/design/preset", data={"preset_key": "salbei_sand"}, headers={"hx-request": "true"}
    )
    assert htmx.status_code == 401
    assert htmx.headers["HX-Redirect"] == "/admin/login"


async def test_post_without_csrf_token_is_rejected(app_client: AsyncTestClient[Litestar]) -> None:
    del app_client.headers["x-csrftoken"]
    response = await app_client.post(
        "/admin/login", data={"username": "admin", "password": ADMIN_PASSWORD}
    )
    assert response.status_code == 403


async def test_unknown_host_is_rejected(app_client: AsyncTestClient[Litestar]) -> None:
    response = await app_client.get("/", headers={"host": "evil.example"})
    assert response.status_code == 400


async def test_login_input_validation_does_not_crash(app_client: AsyncTestClient[Litestar]) -> None:
    response = await app_client.post("/admin/login", data={"username": "", "password": ""})
    assert response.status_code == 200
    assert "Bitte Benutzername und Passwort eingeben" in response.text


async def test_login_rate_limit_middleware(app_client: AsyncTestClient[Litestar]) -> None:
    statuses = [
        (
            await app_client.post("/admin/login", data={"username": "admin", "password": "wrong"})
        ).status_code
        for _ in range(get_settings().RATE_LIMIT_SENSITIVE_PER_MINUTE + 1)
    ]
    assert statuses[-1] == 429


async def test_already_logged_in_skips_login_form(app_client: AsyncTestClient[Litestar]) -> None:
    assert await login(app_client) == "/admin"
    response = await app_client.get("/admin/login", follow_redirects=False)
    assert response.headers["location"] == "/admin"


async def test_full_2fa_login_flow_over_http(app_client: AsyncTestClient[Litestar]) -> None:
    assert await login(app_client) == "/admin"
    _, codes = await enable_totp_via_ui(app_client)

    # Enabling 2FA revoked the current cookie version – but the session was re-issued
    assert (await app_client.get("/admin", follow_redirects=False)).status_code == 200

    await app_client.post("/admin/logout")
    assert (await app_client.get("/admin/login/verify", follow_redirects=False)).headers[
        "location"
    ] == "/admin/login"
    assert await login(app_client) == "/admin/login/verify"
    assert (await app_client.get("/admin", follow_redirects=False)).status_code == 302

    page = await app_client.get("/admin/login/verify")
    assert "Zwei-Faktor-Anmeldung" in page.text
    wrong = await app_client.post("/admin/login/verify", data={"code": "123456"})
    assert "Ungültige Anmeldedaten" in wrong.text

    ok = await app_client.post(
        "/admin/login/verify", data={"code": codes[0]}, follow_redirects=False
    )
    assert ok.headers["location"] == "/admin"
    security = await app_client.get("/admin/security")
    assert "noch 9 unbenutzte" in security.text

    regenerated = await app_client.post(
        "/admin/security/recovery-codes", data={"password": ADMIN_PASSWORD}
    )
    assert "Neue Wiederherstellungscodes erstellt" in regenerated.text
    bad = await app_client.post("/admin/security/recovery-codes", data={"password": "wrong"})
    assert "Das Passwort ist falsch" in bad.text

    disabled = await app_client.post(
        "/admin/security/totp/disable", data={"password": ADMIN_PASSWORD}
    )
    assert "deaktiviert" in disabled.text


async def test_security_page_errors(app_client: AsyncTestClient[Litestar]) -> None:
    assert await login(app_client) == "/admin"
    expired = await app_client.post("/admin/security/totp/confirm", data={"code": "123456"})
    assert "Einrichtung ist abgelaufen" in expired.text

    await app_client.post("/admin/security/totp/start")
    wrong = await app_client.post("/admin/security/totp/confirm", data={"code": "000000x"})
    assert "Der Code ist ungültig" in wrong.text
    assert "<svg" in wrong.text  # QR code rendered again

    mismatch = await app_client.post(
        "/admin/security/password",
        data={
            "current_password": ADMIN_PASSWORD,
            "new_password": "ein-neues-passwort!",
            "new_password_confirm": "anderes-passwort!!",
        },
    )
    assert "stimmen nicht überein" in mismatch.text
    wrong_current = await app_client.post(
        "/admin/security/password",
        data={
            "current_password": "wrong",
            "new_password": "ein-neues-passwort!",
            "new_password_confirm": "ein-neues-passwort!",
        },
    )
    assert "aktuelle Passwort ist falsch" in wrong_current.text
    bad_disable = await app_client.post("/admin/security/totp/disable", data={"password": "x"})
    assert "Passwort ist falsch" in bad_disable.text


async def test_password_change_keeps_current_device_logged_in(
    app_client: AsyncTestClient[Litestar],
) -> None:
    assert await login(app_client) == "/admin"
    stolen_cookie = app_client.cookies.get("atem_session")
    response = await app_client.post(
        "/admin/security/password",
        data={
            "current_password": ADMIN_PASSWORD,
            "new_password": "ein-neues-passwort!",
            "new_password_confirm": "ein-neues-passwort!",
        },
    )
    assert "Passwort geändert" in response.text
    assert (await app_client.get("/admin", follow_redirects=False)).status_code == 200

    # An old copy of the cookie (e.g. stolen) is revoked
    app_client.cookies.set("atem_session", stolen_cookie or "")
    assert (await app_client.get("/admin", follow_redirects=False)).status_code == 302


@pytest.mark.usefixtures("require_2fa")
async def test_mandatory_2fa_forces_setup_before_admin_access(
    app_client: AsyncTestClient[Litestar],
) -> None:
    assert await login(app_client) == "/admin"
    blocked = await app_client.get("/admin", follow_redirects=False)
    assert blocked.headers["location"] == "/admin/security"
    page = await app_client.get("/admin/security")
    assert "Richten Sie die Zwei-Faktor-Anmeldung ein" in page.text
    refused = await app_client.post("/admin/security/totp/disable", data={"password": "x"})
    assert "obligatorisch" in refused.text

    await enable_totp_via_ui(app_client)
    assert (await app_client.get("/admin", follow_redirects=False)).status_code == 200
