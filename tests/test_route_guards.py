"""Regression guard: every /admin route (except the login flow) requires authentication.

Routes are discovered from the application itself – a new admin endpoint without the
``require_admin`` guard makes this test fail.
"""

import re
import uuid

import pytest
from litestar import Litestar
from litestar.routes import HTTPRoute
from litestar.testing import AsyncTestClient

from atem.presentation.app import create_app

PUBLIC_ADMIN_PATHS = {"/admin/login", "/admin/login/verify", "/admin/logout"}
PARAM_SAMPLES = {"uuid": str(uuid.uuid4()), "str": "hero.title", "int": "1"}


def _admin_endpoints() -> list[tuple[str, str]]:
    endpoints: list[tuple[str, str]] = []
    for route in create_app().routes:
        if not isinstance(route, HTTPRoute) or not route.path.startswith("/admin"):
            continue
        if route.path in PUBLIC_ADMIN_PATHS:
            continue
        path = re.sub(r"\{\w+:(\w+)\}", lambda m: PARAM_SAMPLES.get(m.group(1), "x"), route.path)
        endpoints.extend((method, path) for method in sorted(route.methods - {"HEAD", "OPTIONS"}))
    return endpoints


ADMIN_ENDPOINTS = _admin_endpoints()


def test_admin_routes_were_discovered() -> None:
    assert len(ADMIN_ENDPOINTS) >= 20


@pytest.mark.parametrize(("method", "path"), ADMIN_ENDPOINTS)
async def test_admin_route_requires_login(
    app_client: AsyncTestClient[Litestar], method: str, path: str
) -> None:
    response = await app_client.request(method, path, follow_redirects=False)
    assert response.status_code in {302, 401}, f"{method} {path} -> {response.status_code}"
    if response.status_code == 302:
        assert response.headers["location"] == "/admin/login"
