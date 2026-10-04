"""Fernet (AES-128-CBC + HMAC-SHA256) implementation of ISecretCipher."""

import base64

from cryptography.fernet import Fernet, InvalidToken

from atem.domain.interfaces.secret_cipher import ISecretCipher


class FernetSecretCipher(ISecretCipher):
    """Authenticated symmetric encryption for secrets stored in the database."""

    def __init__(self, key: bytes) -> None:
        if len(key) != 32:  # noqa: PLR2004 - Fernet requires exactly 32 raw key bytes
            raise ValueError("Fernet key must be 32 bytes")
        self._fernet = Fernet(base64.urlsafe_b64encode(key))

    def encrypt(self, plaintext: str) -> str:
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        try:
            return self._fernet.decrypt(ciphertext.encode()).decode()
        except InvalidToken as exc:
            raise ValueError("Ciphertext is invalid or was tampered with") from exc
