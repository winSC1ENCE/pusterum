"""Tests for input hardening: theme XSS, content keys/render hints, image uploads, errors."""

import io
import re

import pytest
from litestar import Litestar
from litestar.testing import AsyncTestClient
from PIL import Image

from atem.application.dto.theme import ThemeConfigDTO
from atem.application.services.media_service import MAX_UPLOAD_BYTES, MediaService
from atem.application.services.theme_service import ThemeService
from atem.domain.exceptions import ValidationException
from atem.infrastructure.media.pillow_image_sanitizer import MAX_DIMENSION, PillowImageSanitizer
from tests.conftest import make_image_bytes

ADMIN = {"username": "admin", "password": "admin-secure-init-pass-change-me"}
VALID_THEME = {
    "primary_color": "#112233",
    "secondary_color": "#445566",
    "accent_color": "#778899",
    "background_color": "#FAF8F5",
    "border_color": "#E6DED1",
    "heading_font": "Lora",
    "body_font": "Rubik",
}


async def _login(client: AsyncTestClient[Litestar]) -> None:
    await client.post("/admin/login", data=ADMIN, follow_redirects=False)


# ------------------------------------------------------------------------------ theme
@pytest.mark.parametrize(
    "override",
    [
        {"heading_font": "x</style><script>alert(1)</script>"},
        {"body_font": "Comic Sans"},
        {"primary_color": "red;}</style><script>alert(1)</script>"},
        {"primary_hover": "#12345678901234567890123"},
        {"accent_color": "rgb(1,2,3)"},
    ],
)
async def test_custom_theme_rejects_injection(
    app_client: AsyncTestClient[Litestar], override: dict[str, str]
) -> None:
    await _login(app_client)
    response = await app_client.post(
        "/admin/design/custom", data={**VALID_THEME, **override}, headers={"hx-request": "true"}
    )
    assert response.status_code == 400
    page = await app_client.get("/")
    assert "<script>alert(1)</script>" not in page.text


async def test_custom_theme_accepts_valid_values(app_client: AsyncTestClient[Litestar]) -> None:
    await _login(app_client)
    response = await app_client.post(
        "/admin/design/custom", data=VALID_THEME, headers={"hx-request": "true"}
    )
    assert response.status_code == 204
    assert "--theme-primary: #112233" in (await app_client.get("/")).text


def test_css_generation_falls_back_for_invalid_stored_values(theme_service: ThemeService) -> None:
    poisoned = ThemeConfigDTO(
        primary_color="x;}</style><script>",
        heading_font="Evil</style>",
        dandelion_seed_size=48,
    )
    css = theme_service.generate_css_variables(poisoned)
    assert "</style>" not in css
    assert "--theme-primary: #4A6C50" in css
    assert "--font-heading: 'Lora'" in css


# ---------------------------------------------------------------------------- content
async def test_unknown_or_malformed_content_keys_are_rejected(
    app_client: AsyncTestClient[Litestar],
) -> None:
    await _login(app_client)
    unknown = await app_client.post(
        "/admin/content/hero.does_not_exist/save", data={"content": "x"}
    )
    assert unknown.status_code == 404
    malformed = await app_client.post(
        "/admin/content/x');alert(1)%2F%2F/save", data={"content": "x"}
    )
    assert malformed.status_code in {400, 404}


async def test_image_block_requires_safe_path(app_client: AsyncTestClient[Litestar]) -> None:
    await _login(app_client)
    for bad in ["javascript:alert(1)", "/media/../../etc/passwd", "x'+alert(1)+'", ""]:
        response = await app_client.post(
            "/admin/content/about.portrait/save", data={"content": bad}
        )
        assert response.status_code == 400, bad


async def test_content_length_is_limited(app_client: AsyncTestClient[Litestar]) -> None:
    await _login(app_client)
    response = await app_client.post(
        "/admin/content/hero.title/save", data={"content": "a" * 10001}
    )
    assert response.status_code == 400


async def test_render_hints_are_sanitised(app_client: AsyncTestClient[Litestar]) -> None:
    await _login(app_client)
    response = await app_client.post(
        "/admin/content/hero.title/save",
        data={
            "content": "Sicherer Titel",
            "tag": "img src=x onerror=alert(1)//",
            "css_class": 'x" onmouseover="alert(1)',
            "rows": "not-a-number",
        },
    )
    assert response.status_code == 200
    assert "onerror" not in response.text
    assert "onmouseover" not in response.text
    assert '<p class="">Sicherer Titel</p>' in response.text


async def test_editor_passes_values_to_javascript_as_json(
    app_client: AsyncTestClient[Litestar],
) -> None:
    await _login(app_client)
    page = await app_client.get("/")
    assert """x-data='inlineEditor("hero.title", "text")'""" in page.text


# ---------------------------------------------------------------------------- uploads
@pytest.fixture
def media_service(tmp_path: pytest.TempPathFactory) -> MediaService:
    return MediaService(PillowImageSanitizer(), tmp_path / "media", tmp_path / "static")  # type: ignore[operator]


def test_upload_rejects_svg_and_non_images(media_service: MediaService) -> None:
    svg = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'
    for raw in [svg, b"<html><script>alert(1)</script></html>", b"GIF89a" + b"\x00" * 20]:
        with pytest.raises(ValidationException):
            media_service.store_upload(raw)


def test_upload_rejects_oversized_files(media_service: MediaService) -> None:
    with pytest.raises(ValidationException, match="10 MB"):
        media_service.store_upload(b"\x00" * (MAX_UPLOAD_BYTES + 1))


def test_upload_reencodes_polyglot_and_strips_metadata(media_service: MediaService) -> None:
    polyglot = make_image_bytes("PNG") + b"<script>alert(1)</script>"
    stored = media_service.store_upload(polyglot)
    assert re.fullmatch(r"[0-9a-f]{32}\.png", stored.filename)
    data = (media_service._media_dir / stored.filename).read_bytes()
    assert b"<script>" not in data

    exif = Image.Exif()
    exif[0x8825] = {2: (47, 0, 0)}  # GPSInfo
    buffer = io.BytesIO()
    Image.new("RGB", (16, 16), "white").save(buffer, "JPEG", exif=exif.tobytes())
    jpeg = media_service.store_upload(buffer.getvalue())
    with Image.open(media_service._media_dir / jpeg.filename) as reopened:
        assert not reopened.getexif()


def test_upload_downscales_large_images(media_service: MediaService) -> None:
    stored = media_service.store_upload(make_image_bytes("WEBP", (MAX_DIMENSION + 400, 100)))
    with Image.open(media_service._media_dir / stored.filename) as image:
        assert image.width == MAX_DIMENSION
    assert stored.filename.endswith(".webp")


def test_media_listing_only_lists_raster_images(media_service: MediaService) -> None:
    media_service.store_upload(make_image_bytes("PNG"))
    (media_service._static_images_dir).mkdir(parents=True)
    (media_service._static_images_dir / "logo.svg").write_text("<svg/>")
    (media_service._static_images_dir / "photo.jpg").write_bytes(make_image_bytes("JPEG"))
    items = media_service.list_images()
    assert [item.source for item in items] == ["uploads", "theme"]
    assert all(not item.filename.endswith(".svg") for item in items)


async def test_upload_endpoint_rejects_svg(app_client: AsyncTestClient[Litestar]) -> None:
    await _login(app_client)
    response = await app_client.post(
        "/admin/images/upload",
        files={"data": ("evil.svg", b"<svg onload='alert(1)'/>", "image/svg+xml")},
    )
    assert response.status_code == 400


# ----------------------------------------------------------------------------- errors
async def test_unknown_page_renders_html_404(app_client: AsyncTestClient[Litestar]) -> None:
    response = await app_client.get("/gibt-es-nicht", headers={"accept": "text/html"})
    assert response.status_code == 404
    assert "Die Seite wurde nicht gefunden" in response.text
    api = await app_client.get("/gibt-es-nicht", headers={"accept": "application/json"})
    assert api.status_code == 404
    assert api.json()["detail"]
