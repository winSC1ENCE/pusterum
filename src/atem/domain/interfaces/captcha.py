"""Captcha Interface (ABC) – privacy friendly proof-of-work bot protection."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class VerifiedCaptcha:
    """A valid solution; ``challenge_id`` must be registered once to prevent replays."""

    challenge_id: str
    expires_at: datetime


class ICaptcha(ABC):
    """Issue challenges and verify solutions submitted with a form."""

    @abstractmethod
    def create_challenge(self) -> dict[str, Any]:
        """Return the challenge as JSON-serialisable dict for the browser widget."""

    @abstractmethod
    def verify(self, payload: str) -> VerifiedCaptcha | None:
        """Return the verified challenge, or None if the solution is invalid/expired."""
