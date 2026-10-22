"""Tests for WP7: editable practice address, offerings admin, design studio mode handling."""

import re

from litestar import Litestar
from litestar.testing import AsyncTestClient

from tests.conftest import contact_form_payload

ADMIN = {"email": "entwicklung@pusterum.be", "password": "admin-secure-init-pass-change-me"}
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
    # PUSTERUM's own address is shown in the Impressum, not in the location card
    assert "Musterweg 7" in (await app_client.get("/impressum")).text
    assert "Musterweg 7" not in (await app_client.get("/")).text


async def test_services_admin_crud_and_public_rendering(
    app_client: AsyncTestClient[Litestar],
) -> None:
    public_before = await app_client.get("/")
    assert SERVICE_FORM["subtitle"] not in public_before.text  # no offerings yet, no placeholder

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
    assert "&#34;breathing_flow&#34;, &#34;whisper_trail&#34;" in design.text


async def test_offerings_become_contact_subjects(app_client: AsyncTestClient[Litestar]) -> None:
    subject = "Terminanfrage: Einzelsitzung Atem- &amp; Körpertherapie"
    assert "Terminanfrage:" not in (await app_client.get("/")).text

    await _login(app_client)
    await app_client.post("/admin/services", data=SERVICE_FORM)
    page = (await app_client.get("/")).text
    assert f'data-contact-subject="{subject}"' in page
    assert f'<option value="{subject}">' in page
    assert '<optgroup label="Allgemein">' in page

    fields = {
        "sender_name": "Erika Muster",
        "sender_email": "erika@muster.ch",
        "message": "Guten Tag, ich möchte einen Termin vereinbaren.",
    }
    booked = await app_client.post(
        "/contact",
        data=await contact_form_payload(
            app_client, subject="Terminanfrage: Einzelsitzung Atem- & Körpertherapie", **fields
        ),
    )
    assert "Vielen Dank" in booked.text
    forged = await app_client.post(
        "/contact",
        data=await contact_form_payload(app_client, subject="Gewinnspiel!!!", **fields),
    )
    assert "Vielen Dank" in forged.text

    dashboard = (await app_client.get("/admin")).text
    assert "Terminanfrage: Einzelsitzung Atem- &amp; Körpertherapie" in dashboard
    assert "Gewinnspiel" not in dashboard  # unknown subjects are stored as «Sonstiges»

    # A failed submission keeps the chosen subject selected
    retry = await app_client.post(
        "/contact",
        data=await contact_form_payload(
            app_client,
            subject="Terminanfrage: Einzelsitzung Atem- & Körpertherapie",
            sender_name="Erika",
            sender_email="kaputt",
            message="",
        ),
    )
    assert f'<option value="{subject}" selected>' in retry.text


async def test_location_links_to_google_maps_and_website(
    app_client: AsyncTestClient[Litestar],
) -> None:
    page = (await app_client.get("/")).text
    assert "Physio La Fontaine" in page
    assert (
        'href="https://www.google.com/maps/search/?api=1&amp;query='
        'R%C3%BCschlistrasse%209%2C%202502%20Biel"'
    ) in page
    assert 'href="https://physio-lafontaine.ch" target="_blank"' in page
    # Formatted directions: bold heading and bullet list
    assert "<strong>Anreise mit dem ÖV ab Bahnhof Biel</strong>" in page
    assert "<ul><li><strong>Bus nehmen:</strong>" in page


async def test_location_website_link_is_always_https(app_client: AsyncTestClient[Litestar]) -> None:
    await _login(app_client)
    saved = await app_client.post(
        "/admin/content/practice.location_website/save",
        data={"content": "javascript:alert(1)", "tag": "p"},
    )
    assert saved.status_code == 200
    app_client.cookies.delete("atem_session")
    page = (await app_client.get("/")).text
    assert 'href="https://javascript:alert(1)"' in page
    assert 'href="javascript:' not in page


async def test_directions_are_saved_and_rendered_as_rich_text(
    app_client: AsyncTestClient[Litestar],
) -> None:
    await _login(app_client)
    saved = await app_client.post(
        "/admin/content/practice.directions/save",
        data={"content": "**Bus** <script>x</script>\n- Linie 1", "tag": "div"},
    )
    assert saved.status_code == 200
    assert 'role="toolbar"' in saved.text  # re-rendered with the formatting toolbar
    app_client.cookies.delete("atem_session")
    page = (await app_client.get("/")).text
    assert (
        "<p><strong>Bus</strong> &lt;script&gt;x&lt;/script&gt;</p><ul><li>Linie 1</li></ul>"
        in page
    )


async def test_empty_directions_hide_the_row(app_client: AsyncTestClient[Litestar]) -> None:
    await _login(app_client)
    await app_client.post(
        "/admin/content/practice.directions/save", data={"content": "", "tag": "div"}
    )
    assert ">Anreise</h4>" in (await app_client.get("/")).text
    app_client.cookies.delete("atem_session")
    assert ">Anreise</h4>" not in (await app_client.get("/")).text


async def test_empty_trust_and_badge_texts_hide_their_icons(
    app_client: AsyncTestClient[Litestar],
) -> None:
    await _login(app_client)
    for key in ("hero.trust_1", "hero.trust_2", "about.badge_title", "about.badge_subtitle"):
        await app_client.post(f"/admin/content/{key}/save", data={"content": "", "tag": "span"})
    admin_page = (await app_client.get("/")).text
    assert "content-block-hero-trust_1" in admin_page
    assert "content-block-about-badge_title" in admin_page
    app_client.cookies.delete("atem_session")
    page = (await app_client.get("/")).text
    assert "pt-6 border-t border-theme/60" not in page
    assert "absolute -bottom-4 -right-2" not in page


async def test_services_boxes_render_bullet_lists(app_client: AsyncTestClient[Litestar]) -> None:
    await _login(app_client)
    await app_client.post(
        "/admin/content/services.insurance_text/save",
        data={"content": "Ablauf:\n- Erstgespräch\n- Sitzung", "tag": "div"},
    )
    app_client.cookies.delete("atem_session")
    page = (await app_client.get("/")).text
    assert "<p>Ablauf:</p><ul><li>Erstgespräch</li><li>Sitzung</li></ul>" in page


async def test_availability_card_is_hidden_when_empty(
    app_client: AsyncTestClient[Litestar],
) -> None:
    assert "Freitagvormittag" in (await app_client.get("/")).text
    await _login(app_client)
    await app_client.post(
        "/admin/content/contact.availability/save", data={"content": "", "tag": "p"}
    )
    app_client.cookies.delete("atem_session")
    assert "Terminmöglichkeiten" not in (await app_client.get("/")).text


async def test_services_intro_is_shown_above_the_offerings(
    app_client: AsyncTestClient[Litestar],
) -> None:
    """«Arbeitsweise» stays visible with offerings; the empty-offerings hint is admin-only."""
    page = (await app_client.get("/")).text
    assert "content-block-services-intro" not in page  # empty default: hidden publicly
    assert "Noch keine Angebote erfasst" not in page

    await _login(app_client)
    admin_page = (await app_client.get("/")).text
    assert "Noch keine Angebote erfasst" in admin_page
    assert 'href="/admin/services"' in admin_page
    await app_client.post(
        "/admin/content/services.intro/save",
        data={"content": "Ich begleite Sie:\n- Atemübungen\n- Gespräch", "tag": "div"},
    )
    await app_client.post("/admin/services", data=SERVICE_FORM)
    app_client.cookies.delete("atem_session")

    page = (await app_client.get("/")).text
    intro = page.index("<li>Atemübungen</li>")
    assert (
        page.index('id="angebote"')
        < intro
        < page.index(SERVICE_FORM["title"].replace("&", "&amp;"))
    )
    assert "Noch keine Angebote erfasst" not in page


async def test_empty_price_labels_are_hidden(app_client: AsyncTestClient[Litestar]) -> None:
    page = (await app_client.get("/")).text
    assert "lg:col-span-8 space-y-2" in page  # default labels shown next to the text
    await _login(app_client)
    for key in ("services.insurance_label_1", "services.insurance_label_2"):
        await app_client.post(f"/admin/content/{key}/save", data={"content": "", "tag": "span"})
    assert "content-block-services-insurance_label_1" in (await app_client.get("/")).text
    app_client.cookies.delete("atem_session")
    page = (await app_client.get("/")).text
    assert "lg:col-span-12 space-y-2" in page
    assert "lg:col-span-8 space-y-2" not in page
