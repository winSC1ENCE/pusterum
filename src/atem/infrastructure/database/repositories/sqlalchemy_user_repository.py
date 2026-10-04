"""SQLAlchemy implementation of IUserRepository."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, func, select, update

from atem.domain.interfaces.user_repository import IUserRepository
from atem.domain.models.user import User
from atem.infrastructure.database.models.user import (
    LoginAttemptModel,
    RecoveryCodeModel,
    UserModel,
)
from atem.infrastructure.database.repositories.base import SqlAlchemyRepository


class SqlAlchemyUserRepository(SqlAlchemyRepository[UserModel, User], IUserRepository):
    """SQLAlchemy 2.0 Async repository for users, recovery codes and login attempts."""

    model = UserModel
    entity = User

    async def get_by_email(self, email: str) -> User | None:
        """Find user by (normalized) login e-mail address."""
        model = await self._session.scalar(select(UserModel).where(UserModel.email == email))
        return self._to_entity(model) if model else None

    async def get_by_id(self, user_id: UUID) -> User | None:
        """Find user by UUID."""
        return await self._get(user_id)

    async def create_user(self, user: User) -> User:
        """Create new user entity in database."""
        return await self._add(user)

    async def update_user(self, user: User) -> User:
        """Persist all mutable fields of an existing user."""
        return await self._save(user)

    async def replace_recovery_codes(self, user_id: UUID, code_hashes: list[str]) -> None:
        """Delete all recovery codes of the user and store the given hashes."""
        await self._session.execute(
            delete(RecoveryCodeModel).where(RecoveryCodeModel.user_id == user_id)
        )
        self._session.add_all(
            RecoveryCodeModel(user_id=user_id, code_hash=code_hash) for code_hash in code_hashes
        )
        await self._session.flush()

    async def list_unused_recovery_codes(self, user_id: UUID) -> list[tuple[UUID, str]]:
        """Return ``(code_id, hash)`` pairs of recovery codes that were not used yet."""
        rows = await self._session.execute(
            select(RecoveryCodeModel.id, RecoveryCodeModel.code_hash).where(
                RecoveryCodeModel.user_id == user_id, RecoveryCodeModel.used_at.is_(None)
            )
        )
        return [(row.id, row.code_hash) for row in rows]

    async def mark_recovery_code_used(self, code_id: UUID, used_at: datetime) -> None:
        """Mark a recovery code as consumed."""
        await self._session.execute(
            update(RecoveryCodeModel).where(RecoveryCodeModel.id == code_id).values(used_at=used_at)
        )

    async def record_login_attempt(
        self, ip_address: str, *, success: bool, device_id: str | None = None
    ) -> None:
        """Store a login attempt for rate limiting and auditing."""
        self._session.add(
            LoginAttemptModel(ip_address=ip_address, success=success, device_id=device_id)
        )
        await self._session.flush()

    async def count_failed_attempts(self, ip_address: str, since: datetime) -> int:
        """Count failed login attempts from an IP address since the given time."""
        count = await self._session.scalar(
            select(func.count()).where(
                LoginAttemptModel.ip_address == ip_address,
                LoginAttemptModel.success.is_(False),
                LoginAttemptModel.created_at >= since,
            )
        )
        return int(count or 0)

    async def count_failed_device_attempts(self, device_id: str, since: datetime) -> int:
        """Count failed login attempts from a trusted device since the given time."""
        count = await self._session.scalar(
            select(func.count()).where(
                LoginAttemptModel.device_id == device_id,
                LoginAttemptModel.success.is_(False),
                LoginAttemptModel.created_at >= since,
            )
        )
        return int(count or 0)

    async def delete_login_attempts_older_than(self, cutoff: datetime) -> int:
        """Delete login attempt records created before ``cutoff``."""
        result = await self._session.execute(
            delete(LoginAttemptModel).where(LoginAttemptModel.created_at < cutoff)
        )
        return int(getattr(result, "rowcount", 0) or 0)
