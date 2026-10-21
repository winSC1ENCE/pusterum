"""Tests for Live In-Context Content Management and Versioning (ADR-0002)."""

import re

import pytest
from litestar import Litestar
from litestar.testing import AsyncTestClient

from atem.application.dto.content import SaveContentBlockRequestDTO
from atem.application.services.content_service import ContentService
from atem.domain.exceptions import EntityNotFoundException, ValidationException


@pytest.mark.asyncio
async def test_content_service_default_blocks_and_retrieval(
    content_service: ContentService,
) -> None:
    """Test that default seed blocks are properly retrieved."""
    content_map = await content_service.get_content_map()
    assert "hero.title" in content_map
    assert "hero.image" in content_map
    assert "about.bio" in content_map
    assert content_map["hero.title"].current_version_number == 1
    assert content_map["hero.title"].current_content == "PUSTERUM."


@pytest.mark.asyncio
async def test_content_service_save_version_and_history(
    content_service: ContentService,
) -> None:
    """Test saving a new version and inspecting version history."""
    # 1. Initial version is v1
    initial = await content_service.get_block("hero.title")
    assert initial.current_version_number == 1

    # 2. Save new version (v2)
    save_dto = SaveContentBlockRequestDTO(
        content="PUSTERUM Atemraum",
        change_summary="Titel optimiert",
    )
    updated = await content_service.save_block_content(
        key="hero.title",
        dto=save_dto,
        author_name="Therapeutin",
    )
    assert updated.current_version_number == 2
    assert updated.current_content == "PUSTERUM Atemraum"

    # 3. Save identical content (no-op, version remains v2)
    no_op = await content_service.save_block_content(
        key="hero.title",
        dto=save_dto,
        author_name="Therapeutin",
    )
    assert no_op.current_version_number == 2

    # 4. Inspect audit trail history
    history = await content_service.get_block_history("hero.title")
    assert history.block_key == "hero.title"
    assert history.current_version == 2
    assert len(history.versions) == 2
    assert history.versions[0].version_number == 2
    assert history.versions[0].content == "PUSTERUM Atemraum"
    assert history.versions[0].is_current is True
    assert history.versions[1].version_number == 1
    assert history.versions[1].is_current is False


@pytest.mark.asyncio
async def test_content_service_rollback_creates_next_version(
    content_service: ContentService,
) -> None:
    """Test that restoring v1 creates v3 with v1's content (Append-Only)."""
    # Create v2
    await content_service.save_block_content(
        key="hero.title",
        dto=SaveContentBlockRequestDTO(content="Version 2 Text"),
        author_name="Admin",
    )

    # Restore v1 -> produces v3
    restored = await content_service.restore_block_version(
        key="hero.title",
        target_version_number=1,
        author_name="Admin",
    )
    assert restored.current_version_number == 3
    assert restored.current_content == "PUSTERUM."

    # History should contain 3 versions
    history = await content_service.get_block_history("hero.title")
    assert len(history.versions) == 3
    assert history.versions[0].version_number == 3
    assert history.versions[0].content == "PUSTERUM."
    assert history.versions[0].is_current is True


@pytest.mark.asyncio
async def test_content_service_validation_errors(
    content_service: ContentService,
) -> None:
    """Test validation errors for empty image content and unknown keys."""
    with pytest.raises(ValidationException):
        await content_service.save_block_content(
            key="hero.image",
            dto=SaveContentBlockRequestDTO(content="   "),
            author_name="Admin",
        )

    with pytest.raises(EntityNotFoundException):
        await content_service.get_block("non_existent_key")

    with pytest.raises(EntityNotFoundException):
        await content_service.restore_block_version(
            key="hero.title",
            target_version_number=999,
            author_name="Admin",
        )


@pytest.mark.asyncio
async def test_content_admin_endpoints_and_auth_guard(
    app_client: AsyncTestClient[Litestar],
    sample_png: bytes,
) -> None:
    """Test HTMX content routes with unauthorized and authorized requests."""
    # 1. Unauthorized request without session -> 401
    resp_unauth = await app_client.post(
        "/admin/content/hero.title/save",
        data={"content": "Hacker Edit"},
    )
    assert resp_unauth.status_code == 401

    # 2. Login as admin (automatically sets cookie in client)
    login_resp = await app_client.post(
        "/admin/login",
        data={"email": "entwicklung@pusterum.be", "password": "admin-secure-init-pass-change-me"},
        follow_redirects=True,
    )
    assert login_resp.status_code == 200

    # 3. Save new version as authenticated admin
    save_resp = await app_client.post(
        "/admin/content/hero.title/save",
        data={"content": "Neuer Admin Titel", "tag": "h1"},
    )
    assert save_resp.status_code == 200
    assert "Neuer Admin Titel" in save_resp.text
    assert "v2" in save_resp.text

    # 4. Fetch history modal content
    history_resp = await app_client.get("/admin/content/hero.title/history")
    assert history_resp.status_code == 200
    assert "Element-Schlüssel:" in history_resp.text
    assert "hero.title" in history_resp.text
    assert "Neuer Admin Titel" in history_resp.text

    # 5. Restore version 1
    restore_resp = await app_client.post("/admin/content/hero.title/restore/1")
    assert restore_resp.status_code == 200
    assert "PUSTERUM." in restore_resp.text
    assert "v3" in restore_resp.text

    # 6. Test GET /admin/images/list
    img_list_resp = await app_client.get("/admin/images/list")
    assert img_list_resp.status_code == 200
    images = img_list_resp.json()
    assert isinstance(images, list)
    assert len(images) > 0
    assert any("filename" in img and "url" in img for img in images)

    # 7. Test POST /admin/images/upload (with valid PNG into persistent /media/)
    upload_resp = await app_client.post(
        "/admin/images/upload",
        files={"data": ("test_upload.png", sample_png, "image/png")},
    )
    assert upload_resp.status_code in {200, 201}
    upload_data = upload_resp.json()
    assert "url" in upload_data
    assert re.fullmatch(r"/media/[0-9a-f]{32}\.png", upload_data["url"])

    # 8. Test GET /media/... to verify serving from persistent media router
    media_fetch_resp = await app_client.get(upload_data["url"])
    assert media_fetch_resp.status_code == 200
    assert media_fetch_resp.content.startswith(b"\x89PNG")  # re-encoded, metadata stripped

    # 9. Test saving practice.interior_image with uploaded URL (multipart and form data)
    save_img_resp = await app_client.post(
        "/admin/content/practice.interior_image/save",
        data={
            "content": upload_data["url"],
            "img_alt": "Neuer Praxisraum",
            "img_class": "w-full h-full object-cover",
        },
    )
    assert save_img_resp.status_code == 200
    assert upload_data["url"] in save_img_resp.text
    assert "v2" in save_img_resp.text

    # 10. Verify that GET / (landing page) immediately reflects the updated practice image
    landing_resp = await app_client.get("/")
    assert landing_resp.status_code == 200
    assert upload_data["url"] in landing_resp.text


@pytest.mark.asyncio
async def test_universal_content_blocks_seeded(
    content_service: ContentService,
) -> None:
    """Test that universal content blocks for all sections are seeded."""
    content_map = await content_service.get_content_map()
    universal_keys = [
        "hero.trust_1",
        "hero.trust_2",
        "about.badge_title",
        "about.badge_subtitle",
        "about.credential_1",
        "about.interdisciplinary",
        "competencies.badge",
        "competencies.title",
        "competencies.bridge_p1",
        "competencies.for_whom_1",
        "competencies.for_whom_8",
        "quotes.1.text",
        "quotes.6.author",
        "services.badge",
        "services.insurance_title",
        "contact.badge",
        "contact.phone_label",
        "contact.availability_label",
        "contact.availability",
        "impressum.title",
        "impressum.responsible_title",
        "impressum.webdesign_title",
        "impressum.webdesign_by",
        "impressum.webdesign_notice",
        "footer.tagline",
        "footer.webdesign",
        "footer.trademark_notice",
        "datenschutz.title",
        "datenschutz.sec1_title",
    ]
    for key in universal_keys:
        assert key in content_map, f"Missing expected content block key: {key}"


@pytest.mark.asyncio
async def test_impressum_and_datenschutz_public_routes(
    app_client: AsyncTestClient[Litestar],
) -> None:
    """Verify Impressum and Datenschutz public pages render with content and HTTP 200."""
    imp_resp = await app_client.get("/impressum")
    assert imp_resp.status_code == 200
    assert "Impressum" in imp_resp.text
    assert "Webdesign bynico." in imp_resp.text
    assert "Nicolas Mischler" in imp_resp.text

    ds_resp = await app_client.get("/datenschutz")
    assert ds_resp.status_code == 200
    assert "Datenschutzerklärung" in ds_resp.text

    # Test that landing page footer contains webdesign & trademark credits
    landing_resp = await app_client.get("/")
    assert landing_resp.status_code == 200
    assert "Webdesign bynico." in landing_resp.text
    assert "Nicolas Mischler" in landing_resp.text

    # Test editing impressum webdesign block
    await app_client.post(
        "/admin/login",
        data={"email": "entwicklung@pusterum.be", "password": "admin-secure-init-pass-change-me"},
        follow_redirects=True,
    )
    edit_resp = await app_client.post(
        "/admin/content/impressum.webdesign_by/save",
        data={"content": "Design & Code bynico."},
    )
    assert edit_resp.status_code == 200
    assert "Design &amp; Code bynico." in edit_resp.text


@pytest.mark.asyncio
async def test_image_upload_save_and_immediate_live_render(
    app_client: AsyncTestClient[Litestar],
    sample_png: bytes,
) -> None:
    """Verify that uploaded images for practice, portrait, and hero are rendered live."""
    # 1. Login as admin
    await app_client.post(
        "/admin/login",
        data={"email": "entwicklung@pusterum.be", "password": "admin-secure-init-pass-change-me"},
        follow_redirects=True,
    )

    # 2. Upload new practice room image
    upload_resp = await app_client.post(
        "/admin/images/upload",
        files={"data": ("praxis_neuer_raum.png", sample_png, "image/png")},
    )
    assert upload_resp.status_code in {200, 201}
    uploaded_url = upload_resp.json()["url"]

    # 3. Save as practice.interior_image
    save_resp = await app_client.post(
        "/admin/content/practice.interior_image/save",
        data={
            "content": uploaded_url,
            "img_alt": "Neuer Praxisraum Foto",
            "img_class": "w-full h-full aspect-square object-cover shape-organic shadow-inner",
        },
    )
    assert save_resp.status_code == 200
    assert uploaded_url in save_resp.text
    assert "content-block-practice-interior_image" in save_resp.text

    # 4. Verify landing page renders the new practice image immediately
    landing_resp = await app_client.get("/")
    assert landing_resp.status_code == 200
    assert uploaded_url in landing_resp.text

    # 5. Upload and save about.portrait
    upload_portrait = await app_client.post(
        "/admin/images/upload",
        files={"data": ("portrait_neu.png", sample_png, "image/png")},
    )
    portrait_url = upload_portrait.json()["url"]
    save_portrait_resp = await app_client.post(
        "/admin/content/about.portrait/save",
        data={"content": portrait_url, "img_alt": "Neues Porträt"},
    )
    assert save_portrait_resp.status_code == 200
    assert portrait_url in save_portrait_resp.text

    # 6. Verify landing page has both updated images
    landing_resp2 = await app_client.get("/")
    assert portrait_url in landing_resp2.text
    assert uploaded_url in landing_resp2.text


@pytest.mark.asyncio
async def test_optional_content_block_can_be_emptied_and_refilled(
    content_service: ContentService,
) -> None:
    """Text blocks accept empty content (hidden publicly); image blocks do not."""
    filled = await content_service.save_block_content(
        key="hero.text",
        dto=SaveContentBlockRequestDTO(content="Kurzer Einstieg"),
        author_name="Admin",
    )
    assert filled.current_content == "Kurzer Einstieg"

    cleared = await content_service.save_block_content(
        key="hero.text",
        dto=SaveContentBlockRequestDTO(content="   "),
        author_name="Admin",
    )
    assert cleared.current_content == ""

    cleared_title = await content_service.save_block_content(
        key="about.title",
        dto=SaveContentBlockRequestDTO(content=""),
        author_name="Admin",
    )
    assert cleared_title.current_content == ""

    with pytest.raises(ValidationException):
        await content_service.save_block_content(
            key="about.portrait",
            dto=SaveContentBlockRequestDTO(content=""),
            author_name="Admin",
        )


@pytest.mark.asyncio
async def test_empty_optional_hero_text_hidden_publicly_but_placeholder_for_admin(
    app_client: AsyncTestClient[Litestar],
) -> None:
    """An empty hero.text renders nothing publicly and a fillable placeholder for admins."""
    placeholder = "Optionales Feld – leer (öffentlich ausgeblendet)"

    public_resp = await app_client.get("/")
    assert public_resp.status_code == 200
    assert placeholder not in public_resp.text
    assert "content-block-hero-text" not in public_resp.text

    await app_client.post(
        "/admin/login",
        data={"email": "entwicklung@pusterum.be", "password": "admin-secure-init-pass-change-me"},
        follow_redirects=True,
    )
    admin_resp = await app_client.get("/")
    assert placeholder in admin_resp.text
    assert 'id="content-block-hero-text"' in admin_resp.text


@pytest.mark.asyncio
async def test_contact_phone_and_email_are_editable_blocks_without_links_for_admin(
    app_client: AsyncTestClient[Litestar],
) -> None:
    """Phone/e-mail render from content blocks; admins get edit fields instead of links."""
    public_resp = await app_client.get("/")
    assert 'href="tel:+41310000000"' in public_resp.text
    assert 'href="mailto:info@pusterum.be"' in public_resp.text

    await app_client.post(
        "/admin/login",
        data={"email": "entwicklung@pusterum.be", "password": "admin-secure-init-pass-change-me"},
        follow_redirects=True,
    )
    admin_resp = await app_client.get("/")
    assert 'id="content-block-practice-phone"' in admin_resp.text
    assert 'id="content-block-practice-email"' in admin_resp.text
    assert 'href="tel:' not in admin_resp.text
    assert 'href="mailto:info@pusterum.be"' not in admin_resp.text

    impressum_resp = await app_client.get("/impressum")
    assert 'id="content-block-practice-email"' in impressum_resp.text
    assert "mailto:info@pusterum.be" not in impressum_resp.text
