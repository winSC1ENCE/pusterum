"""Host header validation (protects against host header injection / cache poisoning).

Unlike Litestar's AllowedHostsConfig, the port is ignored, so ``localhost:8000`` (container
health check, local development) matches ``localhost``. Entries may use ``*.example.com``.
"""

from collections.abc import Iterable

from litestar.response.base import ASGIResponse
from litestar.status_codes import HTTP_400_BAD_REQUEST
from litestar.types import ASGIApp, Receive, Scope, Send

_INVALID_HOST_BODY = b'{"detail":"Ungueltiger Host-Header"}'
# Container/uptime probes call the app directly (Host: 127.0.0.1:8000); they reveal nothing.
EXEMPT_PATH_PREFIXES = ("/health",)


def _hostname(host_header: str) -> str:
    host = host_header.strip().lower()
    if host.startswith("["):  # IPv6 literal, e.g. [::1]:8000
        return host[1:].split("]", 1)[0]
    return host.rsplit(":", 1)[0] if host.count(":") == 1 else host


class HostValidationMiddleware:
    """Reject requests whose Host header is not in ALLOWED_HOSTS (HTTP 400)."""

    def __init__(self, app: ASGIApp, allowed_hosts: Iterable[str]) -> None:
        self.app = app
        hosts = [h.strip().lower() for h in allowed_hosts]
        self.allow_all = "*" in hosts
        self.exact = {h for h in hosts if not h.startswith("*.")}
        self.suffixes = tuple(h[1:] for h in hosts if h.startswith("*."))

    def is_allowed(self, host_header: str) -> bool:
        """Return True if the host (without port) is allowed."""
        if self.allow_all:
            return True
        name = _hostname(host_header)
        return bool(name) and (name in self.exact or name.endswith(self.suffixes or ("\0",)))

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] in ("http", "websocket") and not scope["path"].startswith(
            EXEMPT_PATH_PREFIXES
        ):
            host = next(
                (v.decode("latin-1") for k, v in scope.get("headers", []) if k == b"host"), ""
            )
            if not self.is_allowed(host):
                response = ASGIResponse(
                    body=_INVALID_HOST_BODY,
                    status_code=HTTP_400_BAD_REQUEST,
                    media_type="application/json",
                )
                await response(scope, receive, send)
                return
        await self.app(scope, receive, send)
