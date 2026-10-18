"""User Repository Interface (ABC)."""

from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from atem.domain.models.user import User


class IUserRepository(ABC):
    """Abstract interface defining user and authentication storage."""

    @abstractmethod
    async def get_by_email(self, email: str) -> User | None:
        """Find user by (normalized) login e-mail address."""

    @abstractmethod
    async def get_by_id(self, user_id: UUID) -> User | None:
        """Find user by unique ID."""

    @abstractmethod
    async def create_user(self, user: User) -> User:
        """Create new system user."""

    @abstractmethod
    async def update_user(self, user: User) -> User:
        """Persist all mutable fields of an existing user."""

    # --- Recovery codes (second factor fallback) ---------------------------------
    @abstractmethod
    async def delete_user(self, user_id: UUID) -> bool:
        """Delete a user and their recovery codes; True if a row was deleted."""

    @abstractmethod
    async def list_users(self) -> list[User]:
        """All accounts, ordered by e-mail address."""

    @abstractmethod
    async def count_active_admins(self) -> int:
        """Number of active administrator accounts."""

    @abstractmethod
    async def replace_recovery_codes(self, user_id: UUID, code_hashes: list[str]) -> None:
        """Delete all recovery codes of the user and store the given hashes."""

    @abstractmethod
    async def list_unused_recovery_codes(self, user_id: UUID) -> list[tuple[UUID, str]]:
        """Return ``(code_id, hash)`` pairs of recovery codes that were not used yet."""

    @abstractmethod
    async def mark_recovery_code_used(self, code_id: UUID, used_at: datetime) -> None:
        """Mark a recovery code as consumed."""

    # --- Login attempts (IP based rate limiting, works across workers) -----------
    @abstractmethod
    async def record_login_attempt(
        self, ip_address: str, *, success: bool, device_id: str | None = None
    ) -> None:
        """Store a login attempt for rate limiting and auditing."""

    @abstractmethod
    async def count_failed_attempts(self, ip_address: str, since: datetime) -> int:
        """Count failed login attempts from an IP address since the given time."""

    @abstractmethod
    async def count_failed_device_attempts(self, device_id: str, since: datetime) -> int:
        """Count failed login attempts from a trusted device since the given time."""

    @abstractmethod
    async def delete_login_attempts_older_than(self, cutoff: datetime) -> int:
        """Delete login attempt records created before ``cutoff`` (retention)."""
