"""Authentication Application Service.

Implements the complete admin login security model:

* password check with constant-time behaviour for unknown users (dummy hash),
* per-account lockout with exponential back-off (domain: ``User.register_failed_login``) that
  only applies to unknown devices – trusted devices (device cookie of a previous full login)
  have their own failure limit, so third parties cannot lock the owner out,
* e-mail notice to the account owner when a lockout starts,
* per-IP rate limiting stored in the database (works across all web workers),
* TOTP second factor with replay protection and one-time recovery codes,
* session revocation via ``User.session_version`` (logout, password change, 2FA changes).
"""

import secrets
from datetime import UTC, datetime, timedelta
from typing import NoReturn
from uuid import UUID

import structlog
from pydantic import ValidationError

from atem.application.dto.auth import (
    CreateAdminDTO,
    LoginRequestDTO,
    LoginResultDTO,
    TotpSetupDTO,
    UserResponseDTO,
)
from atem.domain.exceptions import (
    AuthenticationException,
    EntityNotFoundException,
    RateLimitedException,
    ValidationException,
)
from atem.domain.interfaces.email_service import IEmailService
from atem.domain.interfaces.password_hasher import IPasswordHasher
from atem.domain.interfaces.secret_cipher import ISecretCipher
from atem.domain.interfaces.totp_provider import ITotpProvider
from atem.domain.interfaces.user_repository import IUserRepository
from atem.domain.models.user import (
    DEVICE_FAILURE_WINDOW,
    MAX_FAILED_DEVICE_LOGINS,
    DeviceClaim,
    User,
    UserRole,
    is_reserved_login,
    normalize_email,
)

logger = structlog.get_logger(__name__)

MIN_ADMIN_PASSWORD_LENGTH = 12
IP_FAILURE_WINDOW = timedelta(minutes=15)
IP_FAILURE_LIMIT = 20
RECOVERY_CODE_COUNT = 10
GENERIC_LOGIN_ERROR = "Ungültige Anmeldedaten oder Konto vorübergehend gesperrt."
RATE_LIMIT_ERROR = "Zu viele Anmeldeversuche. Bitte versuchen Sie es in 15 Minuten erneut."


def _now() -> datetime:
    return datetime.now(UTC)


def _as_aware(value: datetime | None) -> datetime | None:
    """SQLite returns naive datetimes; treat them as UTC."""
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def _generate_recovery_code() -> str:
    """Return a human friendly one-time code such as ``k7f2-9qxm``."""
    alphabet = "abcdefghjkmnpqrstuvwxyz23456789"  # no 0/o/1/l/i
    raw = "".join(secrets.choice(alphabet) for _ in range(8))
    return f"{raw[:4]}-{raw[4:]}"


def _normalise_recovery_code(code: str) -> str:
    return code.strip().lower().replace(" ", "")


class AuthService:
    """Application service for administrator authentication."""

    def __init__(
        self,
        user_repository: IUserRepository,
        password_hasher: IPasswordHasher,
        secret_cipher: ISecretCipher,
        totp_provider: ITotpProvider,
        email_service: IEmailService | None = None,
    ) -> None:
        self._user_repository = user_repository
        self._email = email_service
        self._password_hasher = password_hasher
        self._cipher = secret_cipher
        self._totp = totp_provider
        self._dummy_hash: str | None = None

    # ------------------------------------------------------------------ login ---
    async def authenticate(
        self, dto: LoginRequestDTO, ip_address: str, device: DeviceClaim | None = None
    ) -> LoginResultDTO:
        """Verify e-mail + password (first factor).

        ``device`` is the authentic device cookie of the browser (if any). For the owner's
        trusted devices the account lockout is replaced by a per-device failure limit.
        """
        now = _now()
        failures = await self._user_repository.count_failed_attempts(
            ip_address, now - IP_FAILURE_WINDOW
        )
        if failures >= IP_FAILURE_LIMIT:
            logger.warning("login_rate_limited", ip=ip_address)
            raise RateLimitedException(RATE_LIMIT_ERROR)

        user = await self._user_repository.get_by_email(normalize_email(dto.email))
        if user is None or not user.is_active:
            # Spend the same time as a real check so addresses cannot be enumerated.
            self._password_hasher.verify_password(dto.password, self._get_dummy_hash())
            await self._fail(ip_address, None, now)

        device_id = await self._check_lockout(user, device, ip_address, now)
        if not self._password_hasher.verify_password(dto.password, user.password_hash):
            await self._fail(ip_address, user, now, device_id)

        if user.totp_enabled:
            # Counters are only reset once the second factor is completed as well.
            return LoginResultDTO(user=UserResponseDTO.model_validate(user), requires_totp=True)

        await self._succeed(ip_address, user, now, device_id)
        return LoginResultDTO(user=UserResponseDTO.model_validate(user), requires_totp=False)

    async def verify_second_factor(
        self, user_id: UUID, code: str, ip_address: str, device: DeviceClaim | None = None
    ) -> UserResponseDTO:
        """Verify a TOTP code or a one-time recovery code (second factor)."""
        now = _now()
        user = await self._require_user(user_id)
        device_id = await self._check_lockout(user, device, ip_address, now)
        if not user.totp_enabled or not user.totp_secret_encrypted:
            await self._fail(ip_address, user, now, device_id)

        secret = self._cipher.decrypt(user.totp_secret_encrypted or "")
        step = self._totp.verify(secret, code, user.totp_last_used_step)
        if step is not None:
            user.totp_last_used_step = step
        elif not await self._consume_recovery_code(user, code, now):
            await self._fail(ip_address, user, now, device_id)

        await self._succeed(ip_address, user, now, device_id)
        return UserResponseDTO.model_validate(user)

    async def get_session_user(self, user_id: UUID, session_version: int) -> UserResponseDTO | None:
        """Return the user for a session cookie, or None if it was revoked."""
        user = await self._user_repository.get_by_id(user_id)
        if user is None or not user.is_active or user.session_version != session_version:
            return None
        return UserResponseDTO.model_validate(user)

    async def get_user(self, user_id: UUID) -> UserResponseDTO:
        """Return the current state of an active user."""
        return UserResponseDTO.model_validate(await self._require_user(user_id))

    async def logout(self, user_id: UUID) -> None:
        """Revoke all sessions of the user (all devices)."""
        user = await self._user_repository.get_by_id(user_id)
        if user is not None:
            user.revoke_sessions()
            await self._user_repository.update_user(user)
            logger.info("admin_action", action="logout", user_id=str(user_id))

    # --------------------------------------------------------------- password ---
    async def change_password(
        self, user_id: UUID, current_password: str, new_password: str
    ) -> UserResponseDTO:
        """Change the password; revokes all other sessions."""
        user = await self._require_user(user_id)
        if not self._password_hasher.verify_password(current_password, user.password_hash):
            raise ValidationException("Das aktuelle Passwort ist falsch.")
        self._validate_new_password(new_password, current_password)
        user.password_hash = self._password_hasher.hash_password(new_password)
        user.must_change_password = False
        user.password_changed_at = _now()
        user.revoke_sessions()
        updated = await self._user_repository.update_user(user)
        logger.info("admin_action", action="password_changed", user_id=str(user_id))
        return UserResponseDTO.model_validate(updated)

    # -------------------------------------------------------------------- 2FA ---
    def start_totp_setup(self, user: UserResponseDTO) -> TotpSetupDTO:
        """Create a new TOTP secret (not yet active until confirmed with a code)."""
        secret = self._totp.generate_secret()
        return TotpSetupDTO(
            secret=secret, provisioning_uri=self.totp_provisioning_uri(user, secret)
        )

    def totp_provisioning_uri(self, user: UserResponseDTO, secret: str) -> str:
        """Return the otpauth:// URI (QR code content) for a pending secret."""
        return self._totp.provisioning_uri(secret, user.email)

    async def confirm_totp_setup(self, user_id: UUID, secret: str, code: str) -> list[str]:
        """Activate 2FA after the user proved possession; return fresh recovery codes."""
        user = await self._require_user(user_id)
        step = self._totp.verify(secret, code, None)
        if step is None:
            raise ValidationException("Der Code ist ungültig. Bitte erneut versuchen.")
        user.totp_secret_encrypted = self._cipher.encrypt(secret)
        user.totp_enabled = True
        user.totp_last_used_step = step
        user.revoke_sessions()
        await self._user_repository.update_user(user)
        codes = await self._issue_recovery_codes(user.id)
        logger.info("admin_action", action="totp_enabled", user_id=str(user_id))
        return codes

    async def disable_totp(self, user_id: UUID, password: str) -> UserResponseDTO:
        """Disable 2FA (requires the password)."""
        user = await self._require_user(user_id)
        if not self._password_hasher.verify_password(password, user.password_hash):
            raise ValidationException("Das Passwort ist falsch.")
        user.totp_enabled = False
        user.totp_secret_encrypted = None
        user.totp_last_used_step = None
        user.revoke_sessions()
        await self._user_repository.replace_recovery_codes(user.id, [])
        updated = await self._user_repository.update_user(user)
        logger.info("admin_action", action="totp_disabled", user_id=str(user_id))
        return UserResponseDTO.model_validate(updated)

    async def regenerate_recovery_codes(self, user_id: UUID, password: str) -> list[str]:
        """Replace all recovery codes (requires the password)."""
        user = await self._require_user(user_id)
        if not self._password_hasher.verify_password(password, user.password_hash):
            raise ValidationException("Das Passwort ist falsch.")
        if not user.totp_enabled:
            raise ValidationException("Die Zwei-Faktor-Anmeldung ist nicht aktiv.")
        codes = await self._issue_recovery_codes(user.id)
        logger.info("admin_action", action="recovery_codes_regenerated", user_id=str(user_id))
        return codes

    async def count_recovery_codes(self, user_id: UUID) -> int:
        """Return the number of unused recovery codes."""
        return len(await self._user_repository.list_unused_recovery_codes(user_id))

    async def reset_totp(self, email: str) -> None:
        """Operator recovery (CLI): disable 2FA for a user who lost their device."""
        user = await self._require_user_by_email(email)
        user.totp_enabled = False
        user.totp_secret_encrypted = None
        user.totp_last_used_step = None
        user.revoke_sessions()
        await self._user_repository.replace_recovery_codes(user.id, [])
        await self._user_repository.update_user(user)
        logger.info("admin_action", action="totp_reset_by_operator", user_id=str(user.id))

    async def unlock(self, email: str) -> None:
        """Operator recovery (CLI): lift an account lockout immediately."""
        user = await self._require_user_by_email(email)
        user.failed_login_count = 0
        user.locked_until = None
        await self._user_repository.update_user(user)
        logger.info("admin_action", action="unlocked_by_operator", user_id=str(user.id))

    # ---------------------------------------------------------------- accounts ---
    async def create_admin(self, email: str, password: str) -> UserResponseDTO:
        """Create a new administrator account (used by the CLI in production).

        The login is a personal e-mail address; generic mailboxes (``admin@…``) are refused.
        """
        login = self._validate_login_email(email)
        self._validate_new_password(password)
        if await self._user_repository.get_by_email(login):
            raise ValidationException(f"Ein Konto für «{login}» existiert bereits.")
        user = await self._user_repository.create_user(
            User(
                email=login,
                password_hash=self._password_hasher.hash_password(password),
                role=UserRole.ADMIN,
                is_active=True,
                password_changed_at=_now(),
            )
        )
        logger.info("admin_created", user_id=str(user.id))
        return UserResponseDTO.model_validate(user)

    async def ensure_initial_admin(self, email: str, initial_password: str) -> None:
        """Ensure the local development admin exists (development/test only)."""
        login = self._validate_login_email(email)
        if await self._user_repository.get_by_email(login):
            return
        await self._user_repository.create_user(
            User(
                email=login,
                password_hash=self._password_hasher.hash_password(initial_password),
                role=UserRole.ADMIN,
                is_active=True,
            )
        )
        logger.info("dev_admin_created")

    # ---------------------------------------------------------------- helpers ---
    def _get_dummy_hash(self) -> str:
        if self._dummy_hash is None:
            self._dummy_hash = self._password_hasher.hash_password(secrets.token_hex(16))
        return self._dummy_hash

    @staticmethod
    def _validate_login_email(email: str) -> str:
        """Return the normalized login or raise a ValidationException."""
        try:
            login = normalize_email(CreateAdminDTO(email=normalize_email(email)).email)
        except ValidationError as exc:
            raise ValidationException("Bitte eine gültige E-Mail-Adresse angeben.") from exc
        if is_reserved_login(login):
            raise ValidationException(
                "Bitte eine persönliche E-Mail-Adresse verwenden – "
                "Sammeladressen wie «admin@…» sind als Login nicht erlaubt."
            )
        return login

    async def _require_user_by_email(self, email: str) -> User:
        user = await self._user_repository.get_by_email(normalize_email(email))
        if user is None:
            raise EntityNotFoundException("User", normalize_email(email))
        return user

    async def _require_user(self, user_id: UUID) -> User:
        user = await self._user_repository.get_by_id(user_id)
        if user is None or not user.is_active:
            raise AuthenticationException(GENERIC_LOGIN_ERROR)
        return user

    async def _check_lockout(
        self, user: User, device: DeviceClaim | None, ip_address: str, now: datetime
    ) -> str | None:
        """Apply the lockout that fits the client; return the trusted device id (if any).

        Unknown devices are subject to the account lockout. Trusted devices of this user
        ignore it and are limited per device instead – the owner can always log in.
        """
        if user.trusts_device(device) and device is not None:
            failures = await self._user_repository.count_failed_device_attempts(
                device.device_id, now - DEVICE_FAILURE_WINDOW
            )
            if failures >= MAX_FAILED_DEVICE_LOGINS:
                await self._fail(ip_address, None, now, device.device_id)
            return device.device_id
        user.locked_until = _as_aware(user.locked_until)
        if user.is_locked(now):
            await self._fail(ip_address, None, now)
        return None

    async def _fail(
        self, ip_address: str, user: User | None, now: datetime, device_id: str | None = None
    ) -> NoReturn:
        """Record a failed attempt and raise a generic error.

        Failures from a trusted device only count for that device; failures from unknown
        devices count towards the account lockout (and notify the owner when it starts).
        """
        await self._user_repository.record_login_attempt(
            ip_address, success=False, device_id=device_id
        )
        if user is not None and device_id is None:
            user.register_failed_login(now)
            await self._user_repository.update_user(user)
            if user.locked_until is not None and user.is_locked(now):
                await self._notify_lockout(user, ip_address, user.locked_until)
        logger.warning("login_failed", ip=ip_address)
        raise AuthenticationException(GENERIC_LOGIN_ERROR)

    async def _notify_lockout(self, user: User, ip_address: str, locked_until: datetime) -> None:
        """Tell the owner about a new lockout; delivery problems never break the login flow."""
        logger.warning("account_locked", user_id=str(user.id), ip=ip_address)
        if self._email is None:
            return
        try:
            await self._email.send_lockout_notice(user.email, ip_address, locked_until)
        except Exception:
            logger.exception("lockout_notice_failed", user_id=str(user.id))

    async def _succeed(
        self, ip_address: str, user: User, now: datetime, device_id: str | None = None
    ) -> None:
        await self._user_repository.record_login_attempt(
            ip_address, success=True, device_id=device_id
        )
        if device_id is None:
            user.register_successful_login(now)
        else:
            # A trusted device leaves a running lockout of unknown devices untouched – the
            # owner logging in must not hand an attacker a fresh set of guesses.
            user.last_login_at = now
        await self._user_repository.update_user(user)
        logger.info("admin_action", action="login", user_id=str(user.id), ip=ip_address)

    async def _issue_recovery_codes(self, user_id: UUID) -> list[str]:
        codes = [_generate_recovery_code() for _ in range(RECOVERY_CODE_COUNT)]
        hashes = [self._password_hasher.hash_password(code) for code in codes]
        await self._user_repository.replace_recovery_codes(user_id, hashes)
        return codes

    async def _consume_recovery_code(self, user: User, code: str, now: datetime) -> bool:
        candidate = _normalise_recovery_code(code)
        if len(candidate) != 9:  # noqa: PLR2004 - format xxxx-xxxx
            return False
        for code_id, code_hash in await self._user_repository.list_unused_recovery_codes(user.id):
            if self._password_hasher.verify_password(candidate, code_hash):
                await self._user_repository.mark_recovery_code_used(code_id, now)
                logger.info("admin_action", action="recovery_code_used", user_id=str(user.id))
                return True
        return False

    @staticmethod
    def _validate_new_password(new_password: str, current_password: str | None = None) -> None:
        if len(new_password) < MIN_ADMIN_PASSWORD_LENGTH:
            raise ValidationException(
                f"Das Passwort muss mindestens {MIN_ADMIN_PASSWORD_LENGTH} Zeichen lang sein."
            )
        if current_password is not None and new_password == current_password:
            raise ValidationException("Das neue Passwort muss sich vom aktuellen unterscheiden.")
