"""Argon2 Password Hasher Implementation."""

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from atem.domain.interfaces.password_hasher import IPasswordHasher


class Argon2PasswordHasher(IPasswordHasher):
    """Secure password hashing using Argon2id algorithm."""

    def __init__(self) -> None:
        self._ph = PasswordHasher(
            time_cost=3,
            memory_cost=65536,
            parallelism=4,
            hash_len=32,
            salt_len=16,
        )

    def hash_password(self, plain_password: str) -> str:
        """Create Argon2id hash."""
        return self._ph.hash(plain_password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against Argon2id hash."""
        try:
            return self._ph.verify(hashed_password, plain_password)
        except VerifyMismatchError:
            return False
