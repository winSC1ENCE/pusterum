"""Trusted-device cookie (OWASP "device cookies" against lockout denial of service).

After a complete login (password + second factor) the browser receives a signed cookie
``<user_id>.<issued_at>.<device_id>.<hmac>``. It does **not** authenticate anybody – it only
exempts that browser from the account lockout, so a third party who knows the username can
lock out unknown devices but never the owner's own devices (see ADR-0004).
"""

import hashlib
import hmac
import secrets
import time
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from litestar import Request
from litestar.datastructures import Cookie

from atem.domain.models.user import DeviceClaim
from atem.infrastructure.config.settings import Settings, get_settings

DEVICE_COOKIE = "atem_device"
DEVICE_COOKIE_MAX_AGE = 180 * 24 * 60 * 60
_SIGNATURE_LENGTH = 64  # sha256 hex


def _key(settings: Settings) -> bytes:
    return settings.derive_key(b"atem-device-cookie")


def _sign(key: bytes, payload: str) -> str:
    return hmac.new(key, payload.encode(), hashlib.sha256).hexdigest()


def issue_device_token(key: bytes, user_id: UUID, now: float | None = None) -> str:
    """Return a new signed device token for ``user_id``."""
    payload = f"{user_id}.{int(time.time() if now is None else now)}.{secrets.token_hex(16)}"
    return f"{payload}.{_sign(key, payload)}"


def read_device_token(key: bytes, token: str, now: float | None = None) -> DeviceClaim | None:
    """Return the claim of an authentic, unexpired token – otherwise None."""
    parts = (token or "").split(".")
    if len(parts) != 4 or len(parts[3]) != _SIGNATURE_LENGTH:  # noqa: PLR2004 - 4 fields
        return None
    user_id, issued_at, device_id, signature = parts
    if not hmac.compare_digest(_sign(key, f"{user_id}.{issued_at}.{device_id}"), signature):
        return None
    if not issued_at.isdigit():
        return None
    age = (time.time() if now is None else now) - int(issued_at)
    if not 0 <= age <= DEVICE_COOKIE_MAX_AGE:
        return None
    try:
        uid = UUID(user_id)
    except ValueError:
        return None
    return DeviceClaim(
        user_id=uid, device_id=device_id, issued_at=datetime.fromtimestamp(int(issued_at), UTC)
    )


def device_claim(request: Request[Any, Any, Any]) -> DeviceClaim | None:
    """Device claim of the current browser (None for unknown devices)."""
    return read_device_token(_key(get_settings()), request.cookies.get(DEVICE_COOKIE, ""))


def device_cookie(user_id: UUID) -> Cookie:
    """Fresh trusted-device cookie for a user who just completed a full login."""
    settings = get_settings()
    return Cookie(
        key=DEVICE_COOKIE,
        value=issue_device_token(_key(settings), user_id),
        max_age=DEVICE_COOKIE_MAX_AGE,
        path="/admin",
        secure=settings.is_production_like,
        httponly=True,
        samesite="strict",
    )
