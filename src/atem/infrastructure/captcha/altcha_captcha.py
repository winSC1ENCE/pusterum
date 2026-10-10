"""ALTCHA (self-hosted proof-of-work) implementation of ICaptcha.

No third party is involved: the server issues an HMAC-signed challenge, the browser solves
it in a web worker (a fraction of a second for humans, expensive at scale for bots) and
the server verifies signature, solution and expiry. No cookies, no tracking.
"""

import base64
import binascii
import json
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import parse_qs

from altcha.v1 import ChallengeOptions, create_challenge, verify_solution

from atem.domain.interfaces.captcha import ICaptcha, VerifiedCaptcha

MAX_PAYLOAD_LENGTH = 2048


class AltchaCaptcha(ICaptcha):
    """ALTCHA v1 protocol (compatible with the ``altcha`` web component 1.x)."""

    def __init__(self, hmac_key: str, max_number: int, expires_after: timedelta) -> None:
        self._hmac_key = hmac_key
        self._max_number = max_number
        self._expires_after = expires_after

    def create_challenge(self) -> dict[str, Any]:
        challenge = create_challenge(
            ChallengeOptions(
                hmac_key=self._hmac_key,
                max_number=self._max_number,
                expires=datetime.now(UTC) + self._expires_after,
            )
        )
        return dict(challenge.to_dict())

    def verify(self, payload: str) -> VerifiedCaptcha | None:
        if not payload or len(payload) > MAX_PAYLOAD_LENGTH:
            return None
        try:
            ok, _ = verify_solution(payload, self._hmac_key, check_expires=True)
            if not ok:
                return None
            data = json.loads(base64.b64decode(payload))
            expires = int(parse_qs(str(data["salt"]).split("?", 1)[1])["expires"][0])
            return VerifiedCaptcha(
                challenge_id=str(data["signature"]),
                expires_at=datetime.fromtimestamp(expires, UTC),
            )
        except (ValueError, KeyError, IndexError, TypeError, binascii.Error):
            return None
