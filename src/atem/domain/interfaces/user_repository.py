"""User Repository Interface (ABC)."""

from abc import ABC, abstractmethod
from uuid import UUID

from atem.domain.models.user import User


class IUserRepository(ABC):
    """Abstract interface defining user and authentication storage."""

    @abstractmethod
    async def get_by_username(self, username: str) -> User | None:
        """Find user by username."""

    @abstractmethod
    async def get_by_email(self, email: str) -> User | None:
        """Find user by email address."""

    @abstractmethod
    async def get_by_id(self, user_id: UUID) -> User | None:
        """Find user by unique ID."""

    @abstractmethod
    async def create_user(self, user: User) -> User:
        """Create new system user."""

    @abstractmethod
    async def update_user(self, user: User) -> User:
        """Update existing user."""
