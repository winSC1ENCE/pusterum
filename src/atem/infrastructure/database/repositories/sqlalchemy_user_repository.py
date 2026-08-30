"""SQLAlchemy implementation of IUserRepository."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from atem.domain.interfaces.user_repository import IUserRepository
from atem.domain.models.user import User
from atem.infrastructure.database.models.user import UserModel


class SqlAlchemyUserRepository(IUserRepository):
    """SQLAlchemy 2.0 Async repository for Users."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_username(self, username: str) -> User | None:
        """Find user by username."""
        stmt = select(UserModel).where(UserModel.username == username)
        result = await self._session.execute(stmt)
        m = result.scalar_one_or_none()
        if not m:
            return None
        return User(
            id=m.id,
            created_at=m.created_at,
            updated_at=m.updated_at,
            username=m.username,
            email=m.email,
            password_hash=m.password_hash,
            role=m.role,
            is_active=m.is_active,
        )

    async def get_by_email(self, email: str) -> User | None:
        """Find user by email."""
        stmt = select(UserModel).where(UserModel.email == email)
        result = await self._session.execute(stmt)
        m = result.scalar_one_or_none()
        if not m:
            return None
        return User(
            id=m.id,
            created_at=m.created_at,
            updated_at=m.updated_at,
            username=m.username,
            email=m.email,
            password_hash=m.password_hash,
            role=m.role,
            is_active=m.is_active,
        )

    async def get_by_id(self, user_id: UUID) -> User | None:
        """Find user by UUID."""
        stmt = select(UserModel).where(UserModel.id == user_id)
        result = await self._session.execute(stmt)
        m = result.scalar_one_or_none()
        if not m:
            return None
        return User(
            id=m.id,
            created_at=m.created_at,
            updated_at=m.updated_at,
            username=m.username,
            email=m.email,
            password_hash=m.password_hash,
            role=m.role,
            is_active=m.is_active,
        )

    async def create_user(self, user: User) -> User:
        """Create new user entity in database."""
        model = UserModel(
            id=user.id,
            username=user.username,
            email=user.email,
            password_hash=user.password_hash,
            role=user.role,
            is_active=user.is_active,
        )
        self._session.add(model)
        await self._session.flush()
        user.id = model.id
        user.created_at = model.created_at
        user.updated_at = model.updated_at
        return user

    async def update_user(self, user: User) -> User:
        """Update existing user entity."""
        stmt = select(UserModel).where(UserModel.id == user.id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model:
            model.email = user.email
            model.password_hash = user.password_hash
            model.role = user.role
            model.is_active = user.is_active
            await self._session.flush()
            user.updated_at = model.updated_at
        return user
