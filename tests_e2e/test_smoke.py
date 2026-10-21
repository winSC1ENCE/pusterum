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
    field = title.locator("textarea[name=content]")  # single-line blocks grow (TDR-0011)
    field.fill("PUSTERUM – E2E")
    field.press("Alt+s")
    expect(page.locator("#content-block-hero-title")).to_contain_text("PUSTERUM – E2E")
    assert_clean(page)


def test_line_break_in_title_renders_as_br(page: Page, server_url: str) -> None:
    """TDR-0011: Enter in a single-line block inserts a line break, the page shows <br>."""
    _login(page, server_url)
    page.goto(server_url + "/")
    title = page.locator("#content-block-hero-title")
    title.dblclick()
    field = title.locator("textarea[name=content]")
    field.fill("PUSTERUM")
    field.press("End")
    height_one_line = field.evaluate("el => el.offsetHeight")
    field.press("Enter")  # new line, not submit
    field.type("Raum zum Atmen")
    expect(field).to_be_visible()
    assert field.evaluate("el => el.offsetHeight") > height_one_line  # the field grew
    field.press("Alt+s")
    expect(title).to_contain_text("Raum zum Atmen")
    assert "PUSTERUM<br>Raum zum Atmen" in title.inner_html()

    page.context.clear_cookies()
    page.goto(server_url + "/")
    assert "PUSTERUM<br>Raum zum Atmen" in page.locator("h1").first.inner_html()
    assert_clean(page)

    _login(page, server_url)  # restore a plain title for the other tests
    page.goto(server_url + "/")
    page.locator("#content-block-hero-title").dblclick()
    page.locator("#content-block-hero-title textarea[name=content]").fill("PUSTERUM")
    page.locator("#content-block-hero-title textarea[name=content]").press("Alt+s")
    expect(page.locator("#content-block-hero-title")).not_to_contain_text("Raum zum Atmen")


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


def test_section_order_buttons_reorder_the_page(page: Page, server_url: str) -> None:
    _login(page, server_url)
    page.goto(server_url + "/admin/design#section-order")
    page.locator("#move-practice-up").scroll_into_view_if_needed()
    scroll_before = page.evaluate("window.scrollY")
    assert scroll_before > 0
    page.get_by_role("button", name="Praxis: Nach oben schieben").click()
    expect(page.locator("#section-order li").nth(5)).to_contain_text("Praxis")
    # HTMX swaps only the card: no reload, no jump, focus stays on the moved section's button
    assert page.evaluate("window.scrollY") == scroll_before
    expect(page.locator("#move-practice-up")).to_be_focused()
    assert_clean(page)
    page.goto(server_url + "/")
    praxis = page.locator("#praxis").bounding_box()
    quotes = page.locator("#zitate").bounding_box()
    assert praxis and quotes and praxis["y"] < quotes["y"]
    # Restore the default order for the other tests
    page.goto(server_url + "/admin/design")
    page.get_by_role("button", name="Praxis: Nach unten schieben").click()
    expect(page.locator("#section-order li").nth(6)).to_contain_text("Praxis")


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


def test_accounts_overview_from_dashboard(page: Page, server_url: str) -> None:
    _login(page, server_url)
    page.goto(server_url + "/admin")
    page.get_by_role("link", name="Admin-Konten").click()
    table = page.get_by_test_id("accounts-table")
    expect(table.get_by_text(ADMIN_EMAIL)).to_be_visible()
    expect(table.get_by_text("(Sie)")).to_be_visible()
    page.set_viewport_size({"width": 390, "height": 844})
    expect(table.get_by_text("Letzte Anmeldung:")).to_be_visible()  # card layout on phones
    assert_clean(page)


def test_contact_message_workflow(page: Page, server_url: str) -> None:
    """TDR-0010: find a message, open it, close it and delete it."""
    page.goto(server_url + "/#kontakt")
    page.fill("#sender_name", "Workflow Test")
    page.fill("#sender_email", "workflow@example.ch")
    page.fill("#message", "Guten Tag, das ist eine Testanfrage für den Ablauf.")
    page.locator("altcha-widget input[type=checkbox]").check()
    expect(page.locator('input[name="altcha"]')).to_have_value(re.compile(".+"), timeout=15000)
    page.get_by_role("button", name="Nachricht absenden").click()
    expect(page.get_by_text("Vielen Dank für Ihre Nachricht!")).to_be_visible()

    _login(page, server_url)
    page.goto(server_url + "/admin")
    page.get_by_test_id("all-messages-link").click()
    page.set_viewport_size({"width": 390, "height": 844})
    page.get_by_label("Suche (Name, E-Mail, Betreff)").fill("workflow@example.ch")
    page.get_by_role("button", name="Anzeigen").click()
    expect(page.get_by_test_id("message-total")).to_contain_text("1 Anfrage")
    page.get_by_test_id("message-list").get_by_text("Workflow Test").click()

    expect(page.get_by_test_id("message-status")).to_contain_text("In Bearbeitung")
    expect(page.get_by_test_id("message-text")).to_contain_text("Testanfrage")
    page.get_by_role("button", name="Erledigt").click()
    expect(page.get_by_test_id("message-status")).to_contain_text("Erledigt")
    expect(page.get_by_test_id("message-history")).to_contain_text("In Bearbeitung → Erledigt")
    assert_clean(page)

    page.get_by_label("Diese Anfrage endgültig löschen").check()
    page.get_by_role("button", name="Löschen", exact=True).click()
    expect(page).to_have_url(re.compile(r"/admin/messages$"))
    page.goto(server_url + "/admin/messages?status=all&q=workflow%40example.ch")
    expect(page.get_by_test_id("message-total")).to_contain_text("0 Anfragen")
    assert_clean(page)
