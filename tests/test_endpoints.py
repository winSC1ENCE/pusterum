"""Integration tests for HTTP and HTMX endpoints."""

import pytest
from litestar import Litestar
from litestar.testing import AsyncTestClient


@pytest.mark.asyncio
async def test_health_endpoints(app_client: AsyncTestClient[Litestar]) -> None:
    """Test health and readiness probes."""
    res = await app_client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok", "service": "atem-web"}

    res_ready = await app_client.get("/health/ready")
    assert res_ready.status_code == 200


@pytest.mark.asyncio
async def test_public_pages(app_client: AsyncTestClient[Litestar]) -> None:
    """Test rendering of public pages."""
    # Index Landing page
    res_index = await app_client.get("/")
    assert res_index.status_code == 200
    assert "PUSTERUM" in res_index.text
    assert "Hā Ola" not in res_index.text
    # Indication checklist and rotating quote band are rendered from content blocks
    assert "Schlafproblemen" in res_index.text
    assert 'id="zitate"' in res_index.text
    assert "James Nestor" in res_index.text

    # Impressum
    res_imp = await app_client.get("/impressum")
    assert res_imp.status_code == 200
    assert "Impressum" in res_imp.text

    # Datenschutz
    res_dat = await app_client.get("/datenschutz")
    assert res_dat.status_code == 200
    assert "Datenschutzerklärung" in res_dat.text


@pytest.mark.asyncio
async def test_htmx_contact_form_submission(app_client: AsyncTestClient[Litestar]) -> None:
    """Test HTMX contact form submission."""
    # Successful submission
    payload = {
        "sender_name": "Erika Muster",
        "sender_email": "erika@muster.ch",
        "sender_phone": "+41 79 123 45 67",
        "subject": "Terminanfrage Einzelsitzung",
        "message": "Guten Tag, ich möchte einen Kennenlerntermin vereinbaren.",
        "website_url": "",
    }
    res = await app_client.post("/contact", data=payload)
    assert res.status_code == 200
    assert "Vielen Dank für Ihre Nachricht" in res.text

    # Validation failure submission (missing message)
    invalid_payload = {
        "sender_name": "Erika Muster",
        "sender_email": "invalid-email",
        "message": "",
    }
    res_err = await app_client.post("/contact", data=invalid_payload)
    assert res_err.status_code == 200
    assert "Bitte überprüfen Sie Ihre Eingaben" in res_err.text


@pytest.mark.asyncio
async def test_admin_flow(app_client: AsyncTestClient[Litestar]) -> None:
    """Test admin authentication and dashboard access."""
    # Unauthorized redirect to login
    res_dash = await app_client.get("/admin", follow_redirects=False)
    assert res_dash.status_code in [302, 307]

    # Render login page
    res_login_page = await app_client.get("/admin/login")
    assert res_login_page.status_code == 200

    # Successful login
    login_data = {"username": "admin", "password": "admin-secure-init-pass-change-me"}
    res_login = await app_client.post("/admin/login", data=login_data, follow_redirects=True)
    assert res_login.status_code == 200
    assert "Praxis Dashboard" in res_login.text

    # Access Design Studio
    res_design = await app_client.get("/admin/design")
    assert res_design.status_code == 200
    assert "Corporate Design Studio" in res_design.text
    assert "3. Pusteblumen- &amp; Samen-Aesthetik" in res_design.text

    # Apply multi-select dandelion modes
    res_dandelion = await app_client.post(
        "/admin/design/dandelion",
        data={
            "dandelion_modes": "breathing_flow,breath_widget",
            "dandelion_seed_size": "52",
            "dandelion_seed_opacity": "85",
        },
        headers={"hx-request": "true"},
    )
    assert res_dandelion.status_code == 204

    # Verify public landing page renders properly with active modes
    res_landing = await app_client.get("/")
    assert res_landing.status_code == 200
    assert "dandelion-ambient-engine" in res_landing.text

    # Logout
    res_logout = await app_client.get("/admin/logout", follow_redirects=True)
    assert res_logout.status_code == 200
