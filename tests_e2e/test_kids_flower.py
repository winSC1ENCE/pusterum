"""«Atmende Blume» in a real browser: player, blow game, shared widget tabs, print card."""

import re

from playwright.sync_api import Page, expect

from tests_e2e.conftest import ADMIN_EMAIL, ADMIN_PASSWORD, assert_clean

MOBILE_WIDTH = 390


def _set_modes(page: Page, server_url: str, modes: str) -> None:
    page.goto(server_url + "/admin/login")
    page.fill("#email", ADMIN_EMAIL)
    page.fill("#password", ADMIN_PASSWORD)
    page.get_by_role("button", name="Anmelden").click()
    page.goto(server_url + "/admin/design")
    token = page.locator('meta[name="csrf-token"]').get_attribute("content")
    response = page.request.post(
        server_url + "/admin/design/dandelion",
        form={"dandelion_modes": modes},
        headers={"x-csrftoken": token or "", "hx-request": "true"},
    )
    assert response.ok


def _blow(page: Page, button_selector: str) -> None:
    button = page.locator(button_selector)
    button.hover()
    page.mouse.down()
    page.wait_for_timeout(800)
    page.mouse.up()


def test_section_player_guides_and_blow_game_finishes(page: Page, server_url: str) -> None:
    page.goto(server_url + "/")
    player = page.locator('[data-scope="section"]')
    player.scroll_into_view_if_needed()
    player.get_by_role("button", name="Mit Blume 1 beginnen").click()
    expect(player.get_by_text("Blume 1", exact=True)).to_be_visible()
    expect(player.get_by_text("Einatmen – die Blüte öffnet sich")).to_be_visible()
    expect(player.locator("svg.kids-flower")).to_have_class(re.compile(r"\bis-open\b"))
    expect(player.get_by_text("Ausatmen – die Blüte schliesst sich")).to_be_visible(timeout=5000)

    player.get_by_role("button", name="Zum Pusten").click()
    expect(player.get_by_text("10 Samen sind noch auf der Pusteblume")).to_be_visible()
    for _ in range(5):
        _blow(page, '[data-scope="section"] .kids-blow-button')
    expect(player.get_by_text("Alle Samen fliegen!")).to_be_visible(timeout=5000)
    player.get_by_role("button", name="Nochmals").click()
    expect(player.get_by_role("button", name="Mit Blume 1 beginnen")).to_be_visible()
    assert_clean(page)


def test_short_press_does_not_count(page: Page, server_url: str) -> None:
    page.goto(server_url + "/")
    player = page.locator('[data-scope="section"]')
    player.scroll_into_view_if_needed()
    player.get_by_role("button", name="Direkt zum Pusten").click()
    player.locator(".kids-blow-button").click()  # a quick tap is no breath
    expect(player.get_by_text("10 Samen sind noch auf der Pusteblume")).to_be_visible()
    _blow(page, '[data-scope="section"] .kids-blow-button')
    expect(player.get_by_text("8 Samen sind noch auf der Pusteblume")).to_be_visible()
    assert_clean(page)


def test_widget_tabs_with_breath_pause(page: Page, server_url: str) -> None:
    _set_modes(page, server_url, "breath_widget,kids_flower")
    page.goto(server_url + "/")
    page.get_by_title("Geführte Atem-Pause starten").click()
    expect(page.get_by_role("heading", name="Geführte Atem-Pause")).to_be_visible()
    expect(page.get_by_text("EINATMEN", exact=True)).to_be_visible()

    page.get_by_role("tab", name="Atmende Blume").click()
    widget = page.locator('[data-scope="widget"]')
    expect(page.get_by_role("heading", name="Geführte Atem-Pause")).to_be_hidden()
    widget.get_by_role("button", name="Mit Blume 1 beginnen").click()
    expect(widget.get_by_text("Blume 1", exact=True)).to_be_visible()

    # Switching back stops the flower; the adult exercise runs again
    page.get_by_role("tab", name="Atem-Pause").click()
    expect(page.get_by_text("EINATMEN", exact=True)).to_be_visible()
    page.get_by_role("tab", name="Atmende Blume").click()
    expect(widget.get_by_role("button", name="Mit Blume 1 beginnen")).to_be_visible()
    assert_clean(page)


def test_widget_kids_only_on_mobile(page: Page, server_url: str) -> None:
    _set_modes(page, server_url, "kids_flower")
    page.set_viewport_size({"width": MOBILE_WIDTH, "height": 844})
    page.goto(server_url + "/")
    page.get_by_title("Atmende Blume für Kinder starten").click()
    widget = page.locator('[data-scope="widget"]')
    widget.get_by_role("button", name="Mit Blume 1 beginnen").click()
    expect(widget.get_by_text("Blume 1", exact=True)).to_be_visible()
    box = page.locator('[data-scope="widget"]').bounding_box()
    assert box is not None and box["x"] >= 0 and box["x"] + box["width"] <= MOBILE_WIDTH
    assert_clean(page)


def test_kids_link_in_navigation(page: Page, server_url: str) -> None:
    # Desktop bar from xl (1280 px) – it has to fit there; at lg widths only footer/mobile menu
    page.set_viewport_size({"width": 1280, "height": 800})
    page.goto(server_url + "/")
    expect(page.get_by_role("link", name="Für Kinder", exact=True)).to_be_visible()
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    page.set_viewport_size({"width": 1024, "height": 800})
    expect(page.get_by_role("link", name="Für Kinder", exact=True)).to_be_hidden()


def test_print_card_renders_under_csp(page: Page, server_url: str) -> None:
    page.goto(server_url + "/atmende-blume/karte")
    expect(page.get_by_role("heading", name="Die atmende Blume")).to_be_visible()
    expect(page.get_by_role("button", name="Karte drucken")).to_be_visible()
    page.emulate_media(media="print")
    expect(page.get_by_role("button", name="Karte drucken")).to_be_hidden()
    assert_clean(page)


def test_player_keeps_its_size_and_aligns_with_cards(page: Page, server_url: str) -> None:
    page.set_viewport_size({"width": 1280, "height": 900})
    page.goto(server_url + "/")
    player = page.locator('[data-scope="section"]')
    player.scroll_into_view_if_needed()
    card = player.locator("xpath=..")
    cards = page.locator("#kinder ol")

    def height() -> float:
        box = card.bounding_box()
        assert box is not None
        return round(box["height"])

    heights = [height()]
    player.get_by_role("button", name="Mit Blume 1 beginnen").click()
    expect(player.get_by_text("Blume 1", exact=True)).to_be_visible()
    # The guided flower is highlighted in the card grid
    expect(cards.locator("li").nth(0)).to_have_class(re.compile(r"\bkids-card-active\b"))
    heights.append(height())
    page.wait_for_timeout(3500)  # inhale → exhale
    heights.append(height())
    player.get_by_role("button", name="Zum Pusten").click()
    expect(cards.locator("li.kids-card-active")).to_have_count(0)
    heights.append(height())
    for _ in range(5):
        _blow(page, '[data-scope="section"] .kids-blow-button')
    expect(player.get_by_text("Alle Samen fliegen!")).to_be_visible(timeout=5000)
    heights.append(height())
    assert len(set(heights)) == 1, heights

    # Top and bottom flush with the variant cards on the left
    card_box, grid_box = card.bounding_box(), cards.bounding_box()
    assert card_box is not None and grid_box is not None
    assert abs(card_box["y"] - grid_box["y"]) <= 1
    assert abs((card_box["y"] + card_box["height"]) - (grid_box["y"] + grid_box["height"])) <= 1
    assert_clean(page)


def test_player_size_is_stable_on_mobile(page: Page, server_url: str) -> None:
    page.set_viewport_size({"width": MOBILE_WIDTH, "height": 844})
    page.goto(server_url + "/")
    player = page.locator('[data-scope="section"]')
    player.scroll_into_view_if_needed()
    sizes = [player.bounding_box()["height"]]  # type: ignore[index]
    player.get_by_role("button", name="Mit Blume 1 beginnen").click()
    sizes.append(player.bounding_box()["height"])  # type: ignore[index]
    player.get_by_role("button", name="Zum Pusten").click()
    sizes.append(player.bounding_box()["height"])  # type: ignore[index]
    assert max(sizes) - min(sizes) <= 1, sizes
    assert_clean(page)


def test_card_starts_its_own_flower(page: Page, server_url: str) -> None:
    page.set_viewport_size({"width": 1280, "height": 900})
    page.goto(server_url + "/")
    cards = page.locator("#kinder ol li")
    player = page.locator('[data-scope="section"]')
    cards.nth(2).scroll_into_view_if_needed()
    cards.nth(2).get_by_role("button", name="Mitmachen").click()
    expect(player.get_by_text("Blume 3", exact=True)).to_be_visible()
    expect(player.get_by_text("Die grosse Blume")).to_be_visible()
    expect(cards.nth(2)).to_have_class(re.compile(r"\bkids-card-active\b"))
    expect(cards.nth(2).get_by_role("button", name="Läuft gerade")).to_be_visible()
    expect(player.locator("svg.kids-flower")).to_have_class(re.compile(r"\bv3\b"))

    # The group meadow (Blume 4) is a live exercise as well
    cards.nth(3).get_by_role("button", name="Mitmachen").click()
    expect(player.get_by_text("Blume 4", exact=True)).to_be_visible()
    expect(cards.nth(2)).not_to_have_class(re.compile(r"\bkids-card-active\b"))
    expect(player.locator("svg.kids-flower")).to_have_class(re.compile(r"\bv4\b"))
    assert_clean(page)


def test_variant_done_offers_next_flower(page: Page, server_url: str) -> None:
    page.clock.install()
    page.goto(server_url + "/")
    player = page.locator('[data-scope="section"]')
    player.scroll_into_view_if_needed()
    player.get_by_role("button", name="Mit Blume 1 beginnen").click()
    page.clock.run_for(5 * 7000 + 500)  # five breaths of 3 s + 4 s
    expect(player.get_by_text("Blume 1 geschafft!")).to_be_visible()
    player.get_by_role("button", name="Nächste Blume").click()
    expect(player.get_by_text("Blume 2", exact=True)).to_be_visible()
    assert_clean(page)


def test_photos_fade_behind_the_flower(page: Page, server_url: str) -> None:
    _set_modes(page, server_url, "disabled")  # logged in as admin now
    token = page.locator('meta[name="csrf-token"]').get_attribute("content") or ""
    for kind in ("photo_closed", "photo_open"):
        response = page.request.post(
            server_url + f"/admin/content/kids.variant_1.{kind}/save",
            form={"content": "/static/images/practice_interior.png", "tag": "p"},
            headers={"x-csrftoken": token},
        )
        assert response.ok
    page.context.clear_cookies()
    page.goto(server_url + "/")
    player = page.locator('[data-scope="section"]')
    player.scroll_into_view_if_needed()
    expect(player.locator(".kids-photo")).to_have_count(0)  # no photos before the exercise
    player.get_by_role("button", name="Mit Blume 1 beginnen").click()
    photos = player.locator(".kids-photos img")
    expect(photos).to_have_count(2)
    expect(photos.nth(1)).to_have_class(re.compile(r"\bis-visible\b"))  # inhale → open photo
    expect(photos.nth(0)).to_have_class(re.compile(r"\bis-visible\b"), timeout=5000)  # exhale
    assert_clean(page)


def test_design_studio_photo_opacity_slider(page: Page, server_url: str) -> None:
    _set_modes(page, server_url, "kids_flower")  # logged in, on /admin/design
    page.goto(server_url + "/admin/design")
    slider = page.locator("#kids_photo_opacity_input")
    with page.expect_response(lambda r: "/admin/design/dandelion" in r.url):
        slider.fill("60")
    expect(page.get_by_text("60 %", exact=True)).to_be_visible()
    assert_clean(page)

    page.goto(server_url + "/")
    value = page.evaluate(
        "getComputedStyle(document.documentElement).getPropertyValue('--kids-photo-opacity')"
    )
    assert value.strip() == "0.60"
