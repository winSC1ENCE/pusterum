"""Password Hasher Interface (ABC)."""

from abc import ABC, abstractmethod


class IPasswordHasher(ABC):
    """Abstract interface defining password hashing and verification."""

    @abstractmethod
    def hash_password(self, plain_password: str) -> str:
        """Create secure cryptographic hash of password."""

    @abstractmethod
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify plain password against hashed password."""
