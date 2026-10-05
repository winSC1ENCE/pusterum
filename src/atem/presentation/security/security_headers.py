"""Security response headers incl. a strict Content-Security-Policy.

The policy allows no inline scripts, no eval and no inline <style> elements:
* Tailwind is compiled at build time, Alpine runs as its CSP build,
* theme variables are served as /theme.css, fonts and all libraries are self-hosted.
Only inline *style attributes* are permitted (``style-src-attr``) – they are used for
data-driven sizes and cannot execute script.

User uploads under /media are additionally sandboxed (defence in depth – uploads are
re-encoded raster images, see PillowImageSanitizer).
"""

from litestar.datastructures import MutableScopeHeaders
from litestar.enums import ScopeType
from litestar.types import ASGIApp, Message, Receive, Scope, Send

CSP_DIRECTIVES = (
    "default-src 'self'",
    "script-src 'self'",
    "style-src 'self'",
    "style-src-attr 'unsafe-inline'",
    "img-src 'self' data:",
    "font-src 'self'",
    "connect-src 'self'",
    "worker-src 'self'",
    "manifest-src 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
    "base-uri 'none'",
    "object-src 'none'",
)
MEDIA_CSP = "default-src 'none'; img-src 'self'; style-src 'unsafe-inline'; sandbox"

STATIC_HEADERS = {
    "x-content-type-options": "nosniff",
    "x-frame-options": "DENY",
    "referrer-policy": "strict-origin-when-cross-origin",
    "permissions-policy": "camera=(), microphone=(), geolocation=(), payment=(), usb=()",
    "cross-origin-opener-policy": "same-origin",
    "cross-origin-resource-policy": "same-origin",
}


def build_csp(*, upgrade_insecure_requests: bool) -> str:
    """Return the page CSP (with upgrade-insecure-requests behind HTTPS in production)."""
    directives = list(CSP_DIRECTIVES)
    if upgrade_insecure_requests:
        directives.append("upgrade-insecure-requests")
    return "; ".join(directives)


# The admin area is never linked publicly; keep search engines from indexing it should the URL leak.
ADMIN_ROBOTS_TAG = "noindex, nofollow"


def is_admin_path(path: str) -> bool:
    """True for ``/admin`` and everything below it (but not e.g. ``/administration``)."""
    return path == "/admin" or path.startswith("/admin/")


class SecurityHeadersMiddleware:
    """Add security headers to every HTTP response (unless the handler already set them)."""

    def __init__(self, app: ASGIApp, *, production: bool) -> None:
        self.app = app
        self.page_csp = build_csp(upgrade_insecure_requests=production)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != ScopeType.HTTP:
            await self.app(scope, receive, send)
            return
        csp = MEDIA_CSP if scope["path"].startswith("/media/") else self.page_csp
        admin_area = is_admin_path(scope["path"])

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableScopeHeaders.from_message(message)
                for name, value in STATIC_HEADERS.items():
                    headers.setdefault(name, value)
                headers.setdefault("content-security-policy", csp)
                if admin_area:
                    headers.setdefault("x-robots-tag", ADMIN_ROBOTS_TAG)
            await send(message)

        await self.app(scope, receive, send_with_headers)
