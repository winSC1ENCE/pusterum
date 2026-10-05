"""Children's breathing exercise «Atmende Blume»: section, widget mode, printable card."""

from litestar import Litestar
from litestar.testing import AsyncTestClient

from atem.domain.models.theme import DANDELION_MODE_DEFINITIONS, DandelionEffectMode

ADMIN = {"email": "entwicklung@pusterum.be", "password": "admin-secure-init-pass-change-me"}


async def _set_modes(client: AsyncTestClient[Litestar], modes: str) -> None:
    await client.post("/admin/login", data=ADMIN)
    res = await client.post("/admin/design/dandelion", data={"dandelion_modes": modes})
    assert res.status_code in (200, 201, 302, 303)
    client.cookies.delete("atem_session")


def test_kids_flower_mode_is_combinable_and_listed() -> None:
    modes = DandelionEffectMode.parse_many("breath_widget,kids_flower")
    assert modes == [DandelionEffectMode.BREATH_WIDGET, DandelionEffectMode.KIDS_FLOWER]
    assert "kids_flower" in {d.key for d in DANDELION_MODE_DEFINITIONS}


async def test_section_renders_variants_player_and_tips(
    app_client: AsyncTestClient[Litestar],
) -> None:
    page = (await app_client.get("/")).text
    assert 'id="kinder"' in page
    assert 'href="/#kinder"' in page
    assert "Die Knospe öffnet sich" in page
    assert "Die Blumenwiese (in der Gruppe)" in page
    # The guided player gets the first three variants (the group variant is not guided)
    assert 'x-data="kidsFlower"' in page
    assert 'data-scope="section"' in page
    assert "Die grosse Blume" in page.split('data-scope="section"')[0].rsplit("data-variants", 1)[1]
    assert "<strong>Mit Freude:</strong>" in page
    assert "Volker Friebel" in page
    assert 'href="/atmende-blume/karte"' in page


async def test_widget_only_with_kids_mode(app_client: AsyncTestClient[Litestar]) -> None:
    await _set_modes(app_client, "kids_flower")
    page = (await app_client.get("/")).text
    assert 'data-tab="kids"' in page
    assert 'data-scope="widget"' in page
    assert 'role="tablist"' not in page
    assert "Geführte Atem-Pause" not in page


async def test_widget_tabs_when_combined_with_breath_pause(
    app_client: AsyncTestClient[Litestar],
) -> None:
    await _set_modes(app_client, "breath_widget,kids_flower")
    page = (await app_client.get("/")).text
    assert 'data-tab="adult"' in page
    assert 'role="tablist"' in page
    assert "Geführte Atem-Pause" in page
    assert 'data-scope="widget"' in page


async def test_breath_pause_alone_has_no_kids_tab(app_client: AsyncTestClient[Litestar]) -> None:
    await _set_modes(app_client, "breath_widget")
    page = (await app_client.get("/")).text
    assert 'role="tablist"' not in page
    assert 'data-scope="widget"' not in page


async def test_printable_card(app_client: AsyncTestClient[Litestar]) -> None:
    res = await app_client.get("/atmende-blume/karte")
    assert res.status_code == 200
    assert "kids-card" in res.text
    assert "Die Knospe öffnet sich" in res.text
    assert "<strong>Mit Freude:</strong>" in res.text
    assert "data-print" in res.text
    assert "/admin" not in res.text


async def test_edited_variant_appears_in_section_and_card(
    app_client: AsyncTestClient[Litestar],
) -> None:
    await app_client.post("/admin/login", data=ADMIN)
    saved = await app_client.post(
        "/admin/content/kids.variant_1.title/save",
        data={"content": "Die kleine Tulpe", "tag": "h3"},
    )
    assert saved.status_code == 200
    app_client.cookies.delete("atem_session")
    assert "Die kleine Tulpe" in (await app_client.get("/")).text
    assert "Die kleine Tulpe" in (await app_client.get("/atmende-blume/karte")).text
