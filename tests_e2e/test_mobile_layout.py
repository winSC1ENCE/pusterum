"""Mobile layout: menu reachable without zooming, anchor jumps land below the header, contrast."""

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
