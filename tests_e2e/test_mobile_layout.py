"""Mobile layout: menu reachable without zooming, anchor jumps land below the header, contrast."""

import re

import pytest
from playwright.sync_api import Page, expect

from tests_e2e.conftest import assert_clean

ANCHOR_BELOW_HEADER = """
(id) => {
  const top = document.getElementById(id).getBoundingClientRect().top;
  const header = document.querySelector('header').getBoundingClientRect().bottom;
  return Math.abs(top - header) <= 2;
}
"""


@pytest.mark.parametrize("width", [360, 375, 390])
def test_mobile_menu_button_is_inside_viewport(page: Page, server_url: str, width: int) -> None:
    page.set_viewport_size({"width": width, "height": 800})
    page.goto(server_url + "/")
    assert page.evaluate("document.documentElement.scrollWidth") <= width
    box = page.get_by_role("button", name="Menü öffnen").bounding_box()
    assert box is not None
    assert box["x"] >= 0 and box["x"] + box["width"] <= width
    assert_clean(page)


def test_mobile_menu_jump_lands_below_header(page: Page, server_url: str) -> None:
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(server_url + "/")
    page.get_by_role("button", name="Menü öffnen").click()
    page.get_by_role("link", name="Angebote & Tarife").last.click()
    page.wait_for_function(ANCHOR_BELOW_HEADER, arg="angebote", timeout=5000)
    assert_clean(page)


def test_desktop_nav_jump_lands_below_header(page: Page, server_url: str) -> None:
    page.set_viewport_size({"width": 1440, "height": 900})
    page.goto(server_url + "/")
    page.locator("header nav").get_by_role("link", name="Praxis", exact=True).click()
    page.wait_for_function(ANCHOR_BELOW_HEADER, arg="praxis", timeout=5000)
    assert_clean(page)


def test_footer_brand_is_light_on_dark(page: Page, server_url: str) -> None:
    page.goto(server_url + "/")
    brand = page.locator("footer").get_by_text("PUSTERUM", exact=True)
    expect(brand).to_have_css("color", "rgb(255, 255, 255)")
    expect(page.locator("footer h4").first).to_have_css("color", "rgb(226, 232, 240)")


ROOT_FONT_SIZE = "getComputedStyle(document.documentElement).fontSize"
PHONE_WIDTH = 375
# At the very end of the page the browser cannot scroll further, so the button may move
# a few pixels (before the fix it slid ~900 px out of view).
POSITION_TOLERANCE_PX = 10


def test_font_size_control_in_mobile_menu_persists(page: Page, server_url: str) -> None:
    page.set_viewport_size({"width": PHONE_WIDTH, "height": 800})
    page.goto(server_url + "/")
    assert page.evaluate(ROOT_FONT_SIZE) == "16px"
    page.get_by_role("button", name="Menü öffnen").click()
    menu = page.locator("header")
    larger = menu.get_by_role("button", name="Schrift vergrössern")
    larger.click()
    assert page.evaluate(ROOT_FONT_SIZE) == "18px"
    larger.click()
    assert page.evaluate(ROOT_FONT_SIZE) == "20px"
    expect(larger).to_be_disabled()

    # Kept after a reload (applied before Alpine starts) – and still no horizontal scrolling
    page.reload()
    assert page.evaluate(ROOT_FONT_SIZE) == "20px"
    assert page.evaluate("document.documentElement.scrollWidth") <= PHONE_WIDTH
    box = page.get_by_role("button", name="Menü öffnen").bounding_box()
    assert box is not None and box["x"] + box["width"] <= PHONE_WIDTH

    page.get_by_role("button", name="Menü öffnen").click()
    smaller = menu.get_by_role("button", name="Schrift verkleinern")
    smaller.click()
    assert page.evaluate(ROOT_FONT_SIZE) == "18px"
    expect(smaller).to_be_enabled()  # middle step: both directions possible
    expect(larger).to_be_enabled()
    smaller.click()
    assert page.evaluate(ROOT_FONT_SIZE) == "16px"
    assert page.evaluate("localStorage.getItem('pusterum_font_scale')") is None
    expect(smaller).to_be_disabled()
    # Only − and + (no separate reset button)
    expect(menu.get_by_role("button", name="Normale Schriftgrösse")).to_have_count(0)
    assert_clean(page)


def test_font_size_control_in_footer_syncs_menu(page: Page, server_url: str) -> None:
    page.set_viewport_size({"width": 1440, "height": 900})
    page.goto(server_url + "/")
    footer = page.locator("footer")
    footer.get_by_role("button", name="Schrift vergrössern").click()
    assert page.evaluate(ROOT_FONT_SIZE) == "18px"
    expect(footer.get_by_role("button", name="Schrift verkleinern")).to_be_enabled()
    # The (hidden) menu control follows, so both never disagree
    expect(page.locator('header [aria-label="Schrift verkleinern"]')).to_be_enabled()
    assert_clean(page)


@pytest.mark.parametrize("width", [375, 1280])
def test_font_size_change_keeps_footer_control_in_place(
    page: Page, server_url: str, width: int
) -> None:
    page.set_viewport_size({"width": width, "height": 800})
    page.goto(server_url + "/")
    footer = page.locator("footer")
    larger = footer.get_by_role("button", name="Schrift vergrössern")
    larger.scroll_into_view_if_needed()
    page.wait_for_timeout(300)  # let smooth scrolling settle
    top_before = larger.bounding_box()["y"]  # type: ignore[index]
    larger.click()
    page.wait_for_timeout(300)
    assert page.evaluate(ROOT_FONT_SIZE) == "18px"
    # The page got longer, but the control stays where it was clicked (no jump)
    assert abs(larger.bounding_box()["y"] - top_before) <= POSITION_TOLERANCE_PX  # type: ignore[index]
    # Dots show the step: two of three filled
    expect(footer.locator('[role="group"] .opacity-90')).to_have_count(2)
    assert_clean(page)


def test_theme_colour_opacity_steps_apply(page: Page, server_url: str) -> None:
    """``hover:bg-theme-secondary/30`` needs theme colours as RGB channels (tailwind.config.js)."""
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(server_url + "/")
    page.get_by_role("button", name="Menü öffnen").click()
    link = page.get_by_role("link", name="Kontakt & Standort").filter(visible=True)
    link.hover()
    expect(link).to_have_css("background-color", "rgba(206, 222, 207, 0.3)")
    assert_clean(page)


def test_header_is_frosted_glass(page: Page, server_url: str) -> None:
    """Default header: 60 % theme background plus blur, so content shimmers through."""
    page.goto(server_url + "/")
    header = page.locator("header").first
    # Colour depends on the active palette (other tests switch presets) – the alpha is what counts
    expect(header).to_have_css("background-color", re.compile(r"rgba\(\d+, \d+, \d+, 0\.6\)"))
    assert "blur" in header.evaluate("el => getComputedStyle(el).backdropFilter")
    assert_clean(page)


SWIPE = """
(el, [fromX, toX, y]) => {
  const touch = (x) => new Touch({ identifier: 1, target: el, clientX: x, clientY: y });
  el.dispatchEvent(new TouchEvent("touchstart", { changedTouches: [touch(fromX)], bubbles: true }));
  el.dispatchEvent(new TouchEvent("touchend", { changedTouches: [touch(toX)], bubbles: true }));
}
"""


def test_quotes_change_by_swipe_and_arrow_keys(page: Page, server_url: str) -> None:
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(server_url + "/")
    rotator = page.locator("#zitate [x-data='quoteRotator']")
    figures = page.locator("#zitate figure")
    rotator.scroll_into_view_if_needed()
    expect(figures.nth(0)).to_be_visible()

    rotator.evaluate(SWIPE, [300, 120, 400])
    expect(figures.nth(1)).to_be_visible()
    expect(figures.nth(0)).to_be_hidden()

    rotator.evaluate(SWIPE, [120, 300, 400])
    expect(figures.nth(0)).to_be_visible()

    # A short or mostly vertical gesture keeps the quote (scrolling must not switch)
    rotator.evaluate(SWIPE, [200, 180, 400])
    expect(figures.nth(0)).to_be_visible()

    rotator.focus()
    page.keyboard.press("ArrowRight")
    expect(figures.nth(1)).to_be_visible()
    page.keyboard.press("ArrowLeft")
    expect(figures.nth(0)).to_be_visible()
    assert_clean(page)
