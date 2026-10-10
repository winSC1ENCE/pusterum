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


async def test_every_variant_card_can_be_started(app_client: AsyncTestClient[Litestar]) -> None:
    page = (await app_client.get("/")).text
    for index in range(4):
        assert f'@click="start({index})"' in page
    # All four flowers (including the group meadow) are passed to the player
    assert (
        "Die Blumenwiese (in der Gruppe)"
        in page.split('data-scope="section"')[0].rsplit("data-variants", 1)[1]
    )
    assert '@kids-flower-start.window="startFrom($event)"' in page


async def test_photos_are_admin_only_until_uploaded(app_client: AsyncTestClient[Litestar]) -> None:
    public = (await app_client.get("/")).text
    assert "Bild hinzufügen" not in public
    assert "Foto Ausatmen" not in public
    assert "photo_closed" in public  # key exists, value empty → no photo layer

    await app_client.post("/admin/login", data=ADMIN)
    admin = (await app_client.get("/")).text
    assert admin.count("Foto Ausatmen (geschlossen)") == 4
    assert "Bild hinzufügen" in admin

    saved = await app_client.post(
        "/admin/content/kids.variant_2.photo_open/save",
        data={"content": "/media/blume2-offen.jpg", "tag": "p"},
    )
    assert saved.status_code == 200
    app_client.cookies.delete("atem_session")
    page = (await app_client.get("/")).text
    assert "/media/blume2-offen.jpg" in page
    assert '<img src="/media/blume2-offen.jpg"' not in page  # only inside the player data


async def test_photo_opacity_slider_is_saved_clamped_and_kept(
    app_client: AsyncTestClient[Litestar],
) -> None:
    theme_css = (await app_client.get("/theme.css")).text
    assert "--kids-photo-opacity: 0.30;" in theme_css  # default 30 %

    await app_client.post("/admin/login", data=ADMIN)
    design = (await app_client.get("/admin/design")).text
    assert 'name="kids_photo_opacity"' in design

    await app_client.post(
        "/admin/design/dandelion",
        data={"dandelion_modes": "kids_flower", "kids_photo_opacity": "55"},
    )
    assert "--kids-photo-opacity: 0.55;" in (await app_client.get("/theme.css")).text

    # Out-of-range values are clamped (never fully opaque)
    await app_client.post(
        "/admin/design/dandelion",
        data={"dandelion_modes": "kids_flower", "kids_photo_opacity": "100"},
    )
    assert "--kids-photo-opacity: 0.80;" in (await app_client.get("/theme.css")).text

    # Saving colours (custom form without the slider field) keeps the value
    await app_client.post("/admin/design/custom", data={"primary_color": "#4A6C50"})
    assert "--kids-photo-opacity: 0.80;" in (await app_client.get("/theme.css")).text
