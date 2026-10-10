"""Secret Cipher Interface (ABC) – symmetric encryption of secrets at rest."""

from abc import ABC, abstractmethod


class ISecretCipher(ABC):
    """Encrypt/decrypt small secrets (e.g. TOTP seeds) before they are persisted."""

    @abstractmethod
    def encrypt(self, plaintext: str) -> str:
        """Return an opaque, authenticated ciphertext."""

    @abstractmethod
    def decrypt(self, ciphertext: str) -> str:
        """Return the plaintext; raise ValueError if the ciphertext was tampered with."""
