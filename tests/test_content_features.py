"""Tests for WP7: editable practice address, offerings admin, design studio mode handling."""

import re

from litestar import Litestar
from litestar.testing import AsyncTestClient

ADMIN = {"username": "admin", "password": "admin-secure-init-pass-change-me"}
SERVICE_FORM = {
    "title": "Einzelsitzung Atem- & Körpertherapie",
    "subtitle": "Individuelle Begleitung",
    "description": "Atem- und Körperübungen, Behandlung auf der Liege und Gespräch.",
    "duration_minutes": "60",
    "price_chf": "140,00",
    "sort_order": "1",
    "is_active": "on",
}


async def _login(client: AsyncTestClient[Litestar]) -> None:
    await client.post("/admin/login", data=ADMIN)


async def test_practice_address_is_an_editable_block(app_client: AsyncTestClient[Litestar]) -> None:
    await _login(app_client)
    saved = await app_client.post(
        "/admin/content/practice.address/save",
        data={"content": "Musterweg 7\n3000 Bern", "tag": "p"},
    )
    assert saved.status_code == 200
    app_client.cookies.delete("atem_session")
    for path in ("/", "/impressum"):
        page = await app_client.get(path)
        assert "Musterweg 7" in page.text


async def test_services_admin_crud_and_public_rendering(
    app_client: AsyncTestClient[Litestar],
) -> None:
    public_before = await app_client.get("/")
    assert "Tarife auf Anfrage" in public_before.text

    await _login(app_client)
    created = await app_client.post("/admin/services", data=SERVICE_FORM, follow_redirects=False)
    assert created.headers["location"] == "/admin/services?saved=1"

    page = await app_client.get("/admin/services?saved=1")
    assert "Gespeichert." in page.text
    service_id = re.search(r'action="/admin/services/([0-9a-f-]{36})"', page.text)
    assert service_id
    assert "CHF 140.00" in (await app_client.get("/")).text

    invalid = await app_client.post("/admin/services", data={**SERVICE_FORM, "title": "x"})
    assert "Bitte prüfen Sie die Angaben" in invalid.text

    hidden = {**SERVICE_FORM, "price_chf": "160"}
    hidden.pop("is_active")
    await app_client.post(f"/admin/services/{service_id.group(1)}", data=hidden)
    assert "CHF 160.00" not in (await app_client.get("/")).text  # inactive offers are hidden
    bad_update = await app_client.post(
        f"/admin/services/{service_id.group(1)}", data={**SERVICE_FORM, "duration_minutes": "5"}
    )
    assert "Bitte prüfen Sie die Angaben" in bad_update.text

    deleted = await app_client.post(
        f"/admin/services/{service_id.group(1)}/delete", follow_redirects=False
    )
    assert deleted.status_code == 302
    assert (
        await app_client.post(f"/admin/services/{service_id.group(1)}/delete")
    ).status_code == 404


async def test_services_admin_requires_login(app_client: AsyncTestClient[Litestar]) -> None:
    response = await app_client.get("/admin/services", follow_redirects=False)
    assert response.headers["location"] == "/admin/login"


async def test_custom_theme_keeps_all_selected_dandelion_modes(
    app_client: AsyncTestClient[Litestar],
) -> None:
    """BUG-02: saving custom colours must not reset the multi-select ambient modes."""
    await _login(app_client)
    await app_client.post(
        "/admin/design/dandelion",
        data={"dandelion_modes": "breathing_flow,whisper_trail"},
        headers={"hx-request": "true"},
    )
    await app_client.post(
        "/admin/design/custom",
        data={
            "primary_color": "#112233",
            "secondary_color": "#445566",
            "accent_color": "#778899",
            "background_color": "#FAF8F5",
            "border_color": "#E6DED1",
            "dandelion_mode": "breathing_flow,whisper_trail",
        },
        headers={"hx-request": "true"},
    )
    design = await app_client.get("/admin/design")
    assert '"breathing_flow", "whisper_trail"' in design.text
