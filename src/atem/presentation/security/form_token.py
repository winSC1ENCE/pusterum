"""Signed form timing token – rejects bots that submit faster than a human can type.

The token is rendered into the contact form. It contains the issue timestamp and an
HMAC; a submission is only accepted between MIN_AGE and MAX_AGE after rendering.
"""

import hashlib
import hmac
import time

MIN_AGE_SECONDS = 3
MAX_AGE_SECONDS = 2 * 60 * 60


def issue_form_token(key: bytes, now: float | None = None) -> str:
    """Return ``<timestamp>.<signature>``."""
    timestamp = str(int(time.time() if now is None else now))
    signature = hmac.new(key, timestamp.encode(), hashlib.sha256).hexdigest()
    return f"{timestamp}.{signature}"


def verify_form_token(
    key: bytes,
    token: str,
    now: float | None = None,
    min_age: float = MIN_AGE_SECONDS,
) -> bool:
    """Return True for an authentic token within the allowed age window."""
    timestamp, _, signature = (token or "").partition(".")
    if not timestamp.isdigit() or len(signature) != 64:  # noqa: PLR2004 - sha256 hex length
        return False
    expected = hmac.new(key, timestamp.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        return False
    age = (time.time() if now is None else now) - int(timestamp)
    return min_age <= age <= MAX_AGE_SECONDS
