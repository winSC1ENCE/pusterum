"""The admin area stays invisible on the public website (no links, no admin JS, noindex)."""

import pytest
from litestar import Litestar
from litestar.testing import AsyncTestClient

from atem.presentation.security.security_headers import is_admin_path

ADMIN = {"email": "entwicklung@pusterum.be", "password": "admin-secure-init-pass-change-me"}
LIVE_EDITOR_JS = "/static/js/admin/live-editor.js"


@pytest.mark.parametrize("path", ["/", "/impressum", "/datenschutz"])
async def test_public_pages_do_not_reveal_admin_area(
    app_client: AsyncTestClient[Litestar], path: str
) -> None:
    page = await app_client.get(path)
    assert page.status_code == 200
    assert "/admin" not in page.text
    assert "x-robots-tag" not in page.headers


async def test_public_javascript_contains_no_admin_endpoints(
    app_client: AsyncTestClient[Litestar],
) -> None:
    script = await app_client.get("/static/js/app.js")
    assert script.status_code == 200
    assert "/admin" not in script.text


async def test_live_editor_is_loaded_for_admins_only(
    app_client: AsyncTestClient[Litestar],
) -> None:
    assert LIVE_EDITOR_JS not in (await app_client.get("/")).text

    await app_client.post("/admin/login", data=ADMIN, follow_redirects=False)
    assert LIVE_EDITOR_JS in (await app_client.get("/")).text


async def test_admin_area_is_marked_noindex(app_client: AsyncTestClient[Litestar]) -> None:
    login = await app_client.get("/admin/login")
    assert login.headers["x-robots-tag"] == "noindex, nofollow"

    redirect = await app_client.get("/admin", follow_redirects=False)
    assert redirect.headers["x-robots-tag"] == "noindex, nofollow"


@pytest.mark.parametrize(
    ("path", "expected"),
    [("/admin", True), ("/admin/login", True), ("/administration", False), ("/", False)],
)
def test_is_admin_path(path: str, expected: bool) -> None:
    assert is_admin_path(path) is expected
