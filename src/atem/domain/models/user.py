"""User and Authentication Domain Models."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from uuid import UUID

from atem.domain.models.base import BaseEntity

# Account lockout policy: after MAX_FAILED_LOGINS failures the account is locked for
# LOCKOUT_BASE, doubling with every further failure up to LOCKOUT_MAX.
MAX_FAILED_LOGINS = 5
LOCKOUT_BASE = timedelta(minutes=15)
LOCKOUT_MAX = timedelta(hours=24)


# Trusted devices (OWASP "device cookies"): browsers that completed a full login before are
# exempt from the account lockout and get their own, per-device failure limit instead.
# Third parties can therefore lock out unknown devices only – never the owner.
MAX_FAILED_DEVICE_LOGINS = 5
DEVICE_FAILURE_WINDOW = timedelta(minutes=15)


@dataclass(frozen=True)
class DeviceClaim:
    """Authentic (signature-checked) device cookie content."""

    user_id: UUID
    device_id: str
    issued_at: datetime


# Admin logins are personal e-mail addresses. Generic role mailboxes are refused: they are
# guessable (lockout and password-guessing target) and not tied to one person.
RESERVED_LOGIN_LOCAL_PARTS = frozenset(
    {"admin", "administrator", "root", "superuser", "webmaster", "postmaster", "hostmaster"}
)


def normalize_email(email: str) -> str:
    """Canonical form of a login e-mail address (trimmed, lower case)."""
    return email.strip().lower()


def is_reserved_login(email: str) -> bool:
    """True for generic role mailboxes such as ``admin@…`` that must not be logins."""
    return normalize_email(email).partition("@")[0] in RESERVED_LOGIN_LOCAL_PARTS


class UserRole(StrEnum):
    """User authorization roles."""

    ADMIN = "ADMIN"
    EDITOR = "EDITOR"


@dataclass(kw_only=True)
class User(BaseEntity):
    """System user model for administration."""

    email: str  # login (normalized, unique)
    password_hash: str
    role: UserRole = UserRole.ADMIN
    is_active: bool = True

    # Second factor (TOTP, RFC 6238). The secret is stored encrypted (ISecretCipher).
    totp_secret_encrypted: str | None = None
    totp_enabled: bool = False
    totp_last_used_step: int | None = None

    # Session revocation: every logout / password change increments the version, which
    # invalidates all previously issued session cookies.
    session_version: int = 1

    # Brute-force protection
    failed_login_count: int = 0
    locked_until: datetime | None = None

    must_change_password: bool = False
    password_changed_at: datetime | None = None
    last_login_at: datetime | None = None

    def is_locked(self, now: datetime) -> bool:
        """Return True while the account is temporarily locked."""
        return self.locked_until is not None and self.locked_until > now

    def trusts_device(self, claim: DeviceClaim | None) -> bool:
        """A device is trusted if it belongs to this user and predates no password change."""
        if claim is None or claim.user_id != self.id:
            return False
        changed = self.password_changed_at
        if changed is None:
            return True
        if changed.tzinfo is None:  # SQLite returns naive UTC values
            changed = changed.replace(tzinfo=UTC)
        return claim.issued_at >= changed.replace(microsecond=0)

    def register_failed_login(self, now: datetime) -> None:
        """Count a failed attempt and lock the account with exponential back-off."""
        self.failed_login_count += 1
        excess = self.failed_login_count - MAX_FAILED_LOGINS
        if excess >= 0:
            self.locked_until = now + min(LOCKOUT_BASE * (2**excess), LOCKOUT_MAX)

    def register_successful_login(self, now: datetime) -> None:
        """Reset brute-force counters after a fully completed login."""
        self.failed_login_count = 0
        self.locked_until = None
        self.last_login_at = now

    def revoke_sessions(self) -> None:
        """Invalidate every session cookie issued so far."""
        self.session_version += 1
