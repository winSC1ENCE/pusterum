"""Smoke tests in a real browser: strict CSP, Alpine (CSP build), HTMX, ALTCHA, admin."""

import re

from playwright.sync_api import Page, expect

from tests_e2e.conftest import ADMIN_EMAIL, ADMIN_PASSWORD, assert_clean


def test_home_renders_without_csp_violations(page: Page, server_url: str) -> None:
    response = page.goto(server_url + "/")
    assert response is not None
    csp = response.headers["content-security-policy"]
    assert "script-src 'self'" in csp and "unsafe-eval" not in csp
    expect(page.locator("h1")).to_contain_text("PUSTERUM")
    # Compiled Tailwind + theme variables are applied
    primary = page.evaluate(
        "getComputedStyle(document.documentElement).getPropertyValue('--theme-primary').trim()"
    )
    assert re.fullmatch(r"#[0-9A-Fa-f]{6}", primary)
    # Self-hosted font is used
    assert "Lora" in page.evaluate("getComputedStyle(document.querySelector('h1')).fontFamily")
    assert_clean(page)


def test_quote_rotator_and_mobile_menu(page: Page, server_url: str) -> None:
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(server_url + "/")
    page.get_by_role("button", name="Zitat 2 anzeigen").click()
    expect(page.locator("#zitate figure").nth(1)).to_be_visible()
    expect(page.locator("#zitate figure").nth(0)).to_be_hidden()
    page.get_by_role("button", name="Menü öffnen").click()
    expect(page.get_by_role("link", name="Praxis", exact=True).last).to_be_visible()
    assert_clean(page)


def test_contact_form_with_altcha(page: Page, server_url: str) -> None:
    page.goto(server_url + "/#kontakt")
    page.fill("#sender_name", "Erika Muster")
    page.fill("#sender_email", "erika@example.ch")
    page.fill("#message", "Guten Tag, ich möchte gerne einen Termin vereinbaren.")
    page.locator("altcha-widget input[type=checkbox]").check()
    expect(page.locator('input[name="altcha"]')).to_have_value(re.compile(".+"), timeout=15000)
    page.get_by_role("button", name="Nachricht absenden").click()
    expect(page.get_by_text("Vielen Dank für Ihre Nachricht!")).to_be_visible()
    assert_clean(page)


def test_altcha_blocked_offers_email_fallback(page: Page, server_url: str) -> None:
    # Corporate web filters answer the challenge request with 403 (seen in the wild)
    page.route("**/altcha/challenge", lambda route: route.fulfill(status=403, body="Forbidden"))
    page.goto(server_url + "/#kontakt")
    fallback = page.locator("#altcha-fallback")
    expect(fallback).to_be_hidden()
    page.locator("altcha-widget input[type=checkbox]").click()  # unchecks itself on error
    expect(fallback).to_be_visible(timeout=15000)
    expect(fallback.locator('a[href^="mailto:"]')).to_have_count(1)
    # The widget itself logs the 403 to the console, so only CSP is checked here
    assert page.evaluate("window.__cspViolations || []") == []


def test_admin_login_and_inline_edit(page: Page, server_url: str) -> None:
    page.goto(server_url + "/admin/login")
    page.fill("#email", ADMIN_EMAIL)
    page.fill("#password", ADMIN_PASSWORD)
    page.get_by_role("button", name="Anmelden").click()
    expect(page).to_have_url(re.compile(r"/admin$"))
    assert_clean(page)

    page.goto(server_url + "/")
    title = page.locator("#content-block-hero-title")
    title.dblclick()
    field = title.locator("input[name=content]")
    field.fill("PUSTERUM – E2E")
    field.press("Alt+s")
    expect(page.locator("#content-block-hero-title")).to_contain_text("PUSTERUM – E2E")
    assert_clean(page)


def test_rich_text_toolbar_formats_directions(page: Page, server_url: str) -> None:
    page.goto(server_url + "/admin/login")
    page.fill("#email", ADMIN_EMAIL)
    page.fill("#password", ADMIN_PASSWORD)
    page.get_by_role("button", name="Anmelden").click()
    expect(page).to_have_url(re.compile(r"/admin$"))

    page.goto(server_url + "/#praxis")
    block = page.locator("#content-block-practice-directions")
    block.dblclick()
    field = block.locator("textarea[name=content]")
    field.fill("Bus")
    field.select_text()
    block.get_by_role("button", name="B", exact=True).click()
    expect(field).to_have_value("**Bus**")
    field.press("End")
    field.press("Enter")
    field.press_sequentially("Linie 1")
    block.get_by_role("button", name="• Liste").click()
    expect(field).to_have_value("**Bus**\n- Linie 1")
    field.press("Alt+s")
    saved = page.locator("#content-block-practice-directions")
    expect(saved.locator("li")).to_have_count(1)  # waits for the HTMX swap
    expect(saved.locator("strong")).to_have_text("Bus")
    expect(saved.locator("li")).to_have_text("Linie 1")
    assert_clean(page)


def test_design_studio_without_violations(page: Page, server_url: str) -> None:
    page.goto(server_url + "/admin/login")
    page.fill("#email", ADMIN_EMAIL)
    page.fill("#password", ADMIN_PASSWORD)
    page.get_by_role("button", name="Anmelden").click()
    page.goto(server_url + "/admin/design")
    expect(page.get_by_text("Corporate Design Studio")).to_be_visible()
    assert_clean(page)


def _login(page: Page, server_url: str) -> None:
    page.goto(server_url + "/admin/login")
    page.fill("#email", ADMIN_EMAIL)
    page.fill("#password", ADMIN_PASSWORD)
    page.get_by_role("button", name="Anmelden").click()


def test_all_dandelion_effects_run_under_csp(page: Page, server_url: str) -> None:
    _login(page, server_url)
    page.goto(server_url + "/admin/design")
    token = page.locator('meta[name="csrf-token"]').get_attribute("content")
    response = page.request.post(
        server_url + "/admin/design/dandelion",
        form={
            "dandelion_modes": "breathing_flow,scroll_journey,watermark_accents,"
            "breath_widget,whisper_trail,kids_flower"
        },
        headers={"x-csrftoken": token or "", "hx-request": "true"},
    )
    assert response.ok
    page.set_viewport_size({"width": 1440, "height": 900})
    page.goto(server_url + "/")
    page.mouse.move(300, 300)
    page.mouse.move(600, 400)
    page.mouse.wheel(0, 1500)
    page.get_by_title("Geführte Atem-Pause starten").click()
    expect(page.get_by_role("heading", name="Geführte Atem-Pause")).to_be_visible()
    expect(page.get_by_text("EINATMEN", exact=True)).to_be_visible()
    assert_clean(page)


def test_two_factor_setup_page_renders_qr_code(page: Page, server_url: str) -> None:
    _login(page, server_url)
    page.goto(server_url + "/admin/security")
    page.get_by_role("button", name="Einrichtung starten").click()
    expect(page.locator("[aria-label='QR-Code für die Authenticator-App'] svg")).to_be_visible()
    assert_clean(page)


def test_offering_button_preselects_contact_subject(page: Page, server_url: str) -> None:
    _login(page, server_url)
    page.goto(server_url + "/admin/services")
    page.fill("#new-title", "Atemtherapie E2E")
    page.fill("#new-description", "Begleitung mit Atem, Berührung und Bewegung.")
    page.fill("#new-price", "80")
    page.get_by_role("button", name="Angebot hinzufügen").click()
    expect(page.get_by_text("Gespeichert.")).to_be_visible()

    page.goto(server_url + "/")
    page.locator('[data-contact-subject="Terminanfrage: Atemtherapie E2E"]').click()
    expect(page.locator("#subject")).to_have_value("Terminanfrage: Atemtherapie E2E")
    assert_clean(page)
