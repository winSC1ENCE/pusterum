"""SQLAlchemy implementation of IUserRepository."""

from dataclasses import fields
from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from atem.domain.interfaces.user_repository import IUserRepository
from atem.domain.models.user import User
from atem.infrastructure.database.models.user import (
    LoginAttemptModel,
    RecoveryCodeModel,
    UserModel,
)

_USER_FIELDS = tuple(f.name for f in fields(User))
_IMMUTABLE_FIELDS = frozenset({"id", "created_at", "updated_at"})


def _to_entity(model: UserModel) -> User:
    return User(**{name: getattr(model, name) for name in _USER_FIELDS})


class SqlAlchemyUserRepository(IUserRepository):
    """SQLAlchemy 2.0 Async repository for users, recovery codes and login attempts."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_username(self, username: str) -> User | None:
        """Find user by username."""
        model = await self._session.scalar(select(UserModel).where(UserModel.username == username))
        return _to_entity(model) if model else None

    async def get_by_id(self, user_id: UUID) -> User | None:
        """Find user by UUID."""
        model = await self._session.get(UserModel, user_id)
        return _to_entity(model) if model else None

    async def create_user(self, user: User) -> User:
        """Create new user entity in database."""
        model = UserModel(**{name: getattr(user, name) for name in _USER_FIELDS})
        self._session.add(model)
        await self._session.flush()
        return _to_entity(model)

    async def update_user(self, user: User) -> User:
        """Persist all mutable fields of an existing user."""
        model = await self._session.get(UserModel, user.id)
        if model is None:
            return user
        for name in _USER_FIELDS:
            if name not in _IMMUTABLE_FIELDS:
                setattr(model, name, getattr(user, name))
        await self._session.flush()
        return _to_entity(model)

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

    async def record_login_attempt(self, ip_address: str, *, success: bool) -> None:
        """Store a login attempt for rate limiting and auditing."""
        self._session.add(LoginAttemptModel(ip_address=ip_address, success=success))
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
