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
