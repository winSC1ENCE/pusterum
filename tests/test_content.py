"""Tests for Live In-Context Content Management and Versioning (ADR-0002)."""

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
    assert content_map["hero.title"].current_content == "Hā Ola."


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
        content="Hā Ola Atemzentrum",
        change_summary="Titel optimiert",
    )
    updated = await content_service.save_block_content(
        key="hero.title",
        dto=save_dto,
        author_name="Therapeutin",
    )
    assert updated.current_version_number == 2
    assert updated.current_content == "Hā Ola Atemzentrum"

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
    assert history.versions[0].content == "Hā Ola Atemzentrum"
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
    assert restored.current_content == "Hā Ola."

    # History should contain 3 versions
    history = await content_service.get_block_history("hero.title")
    assert len(history.versions) == 3
    assert history.versions[0].version_number == 3
    assert history.versions[0].content == "Hā Ola."
    assert history.versions[0].is_current is True


@pytest.mark.asyncio
async def test_content_service_validation_errors(
    content_service: ContentService,
) -> None:
    """Test validation errors for empty content and unknown keys."""
    with pytest.raises(ValidationException):
        await content_service.save_block_content(
            key="hero.title",
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
        data={"username": "admin", "password": "admin-secure-init-pass-change-me"},
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
    assert "Hā Ola." in restore_resp.text
    assert "v3" in restore_resp.text

    # 6. Test GET /admin/images/list
    img_list_resp = await app_client.get("/admin/images/list")
    assert img_list_resp.status_code == 200
    images = img_list_resp.json()
    assert isinstance(images, list)
    assert len(images) > 0
    assert any("filename" in img and "url" in img for img in images)

    # 7. Test POST /admin/images/upload (with valid PNG into persistent /media/)
    sample_png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00"
        b"\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4"
        b"\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    upload_resp = await app_client.post(
        "/admin/images/upload",
        files={"data": ("test_upload.png", sample_png, "image/png")},
    )
    assert upload_resp.status_code in {200, 201}
    upload_data = upload_resp.json()
    assert "url" in upload_data
    assert upload_data["url"].startswith("/media/test_upload")

    # 8. Test GET /media/... to verify serving from persistent media router
    media_fetch_resp = await app_client.get(upload_data["url"])
    assert media_fetch_resp.status_code == 200
    assert media_fetch_resp.content == sample_png

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
        "competencies.1.title",
        "services.badge",
        "services.insurance_title",
        "contact.badge",
        "contact.phone_label",
        "impressum.title",
        "impressum.responsible_title",
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

    ds_resp = await app_client.get("/datenschutz")
    assert ds_resp.status_code == 200
    assert "Datenschutzerklärung" in ds_resp.text


@pytest.mark.asyncio
async def test_image_upload_save_and_immediate_live_render(
    app_client: AsyncTestClient[Litestar],
) -> None:
    """Verify that uploaded images for practice, portrait, and hero are rendered live."""
    # 1. Login as admin
    await app_client.post(
        "/admin/login",
        data={"username": "admin", "password": "admin-secure-init-pass-change-me"},
        follow_redirects=True,
    )

    sample_png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00"
        b"\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4"
        b"\x00\x00\x00\x00IEND\xaeB`\x82"
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
