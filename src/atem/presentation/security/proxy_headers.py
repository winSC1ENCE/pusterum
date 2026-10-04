"""ASGI middleware resolving the real client IP behind trusted reverse proxies (Caddy).

Only when the direct peer is a trusted proxy is ``X-Forwarded-For`` evaluated, from right
to left, skipping further trusted hops. Otherwise the header is ignored, so clients cannot
spoof their IP address.
"""

import ipaddress
from collections.abc import Iterable

from litestar.types import ASGIApp, Receive, Scope, Send

IPNetwork = ipaddress.IPv4Network | ipaddress.IPv6Network


def parse_networks(cidrs: Iterable[str]) -> tuple[IPNetwork, ...]:
    """Parse CIDR strings into network objects."""
    return tuple(ipaddress.ip_network(cidr, strict=False) for cidr in cidrs)


def _is_trusted(host: str, networks: tuple[IPNetwork, ...]) -> bool:
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return False
    return any(address in network for network in networks)


def resolve_client_ip(peer: str, forwarded_for: str | None, networks: tuple[IPNetwork, ...]) -> str:
    """Return the first untrusted address in the proxy chain (or the peer itself)."""
    if not forwarded_for or not _is_trusted(peer, networks):
        return peer
    for hop in reversed([part.strip() for part in forwarded_for.split(",") if part.strip()]):
        if not _is_trusted(hop, networks):
            return hop
    return peer


class ProxyHeadersMiddleware:
    """Rewrite ``scope["client"]`` with the resolved client IP."""

    def __init__(self, app: ASGIApp, trusted_proxies: Iterable[str]) -> None:
        self.app = app
        self.networks = parse_networks(trusted_proxies)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] in ("http", "websocket") and scope.get("client"):
            peer, port = scope["client"]  # type: ignore[misc]
            forwarded = None
            for name, value in scope.get("headers", []):
                if name == b"x-forwarded-for":
                    forwarded = value.decode("latin-1")
                    break
            client_ip = resolve_client_ip(peer, forwarded, self.networks)
            if client_ip != peer:
                scope = {**scope, "client": (client_ip, port)}  # type: ignore[assignment]
        await self.app(scope, receive, send)
