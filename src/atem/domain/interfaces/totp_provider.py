"""TOTP Provider Interface (ABC) – time-based one-time passwords (RFC 6238)."""

from abc import ABC, abstractmethod


class ITotpProvider(ABC):
    """Generate and verify TOTP secrets and codes."""

    @abstractmethod
    def generate_secret(self) -> str:
        """Return a new random Base32 secret."""

    @abstractmethod
    def provisioning_uri(self, secret: str, account_name: str) -> str:
        """Return the ``otpauth://`` URI for authenticator apps (QR code content)."""

    @abstractmethod
    def verify(self, secret: str, code: str, last_used_step: int | None) -> int | None:
        """Return the matched time step if ``code`` is valid and newer than ``last_used_step``.

        Returning the step allows the caller to persist it and reject replays of the same code.
        """
