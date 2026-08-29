"""Tests for Corporate Design, 5 Pastel Themes, 5 Shapes, and Design Studio."""

import pytest
from litestar import Litestar
from litestar.testing import AsyncTestClient

from atem.application.dto.theme import ThemeConfigDTO, UpdateThemeRequestDTO
from atem.application.services.theme_service import ThemeService
from atem.domain.models.theme import ColorPresetKey, ShapeType


@pytest.mark.asyncio
async def test_default_theme_initialization(theme_service: ThemeService) -> None:
    """Verify default active theme is initialized correctly with Salbei & Sand."""
    theme = await theme_service.get_active_theme()

    assert theme.preset_key == ColorPresetKey.SALBEI_SAND
    assert theme.primary_color == "#4A6C50"
    assert theme.active_shape == ShapeType.DANDELION_SEED
    assert theme.heading_font == "Lora"
    assert theme.body_font == "Plus Jakarta Sans"


@pytest.mark.asyncio
async def test_apply_all_5_color_presets(theme_service: ThemeService) -> None:
    """Verify switching between all 5 pastel themes."""
    presets = [
        ColorPresetKey.SALBEI_SAND,
        ColorPresetKey.LAVENDEL_NEBEL,
        ColorPresetKey.TERRAKOTTA_PUDER,
        ColorPresetKey.OZEAN_KIESEL,
        ColorPresetKey.SONNE_WEIZEN,
    ]

    for preset_key in presets:
        theme = await theme_service.set_preset(preset_key)
        assert theme.preset_key == preset_key
        assert len(theme.primary_color) >= 4
        assert len(theme.background_color) >= 4


@pytest.mark.asyncio
async def test_apply_all_5_shapes(theme_service: ThemeService) -> None:
    """Verify switching between all 5 geometric and organic shapes."""
    shapes = [
        ShapeType.DANDELION_SEED,
        ShapeType.SOFT_PEBBLE,
        ShapeType.BREATH_WAVE,
        ShapeType.ZEN_CIRCLE,
        ShapeType.FLUID_CAPSULE,
    ]

    for shape_type in shapes:
        theme = await theme_service.set_shape(shape_type)
        assert theme.active_shape == shape_type


@pytest.mark.asyncio
async def test_custom_theme_update(theme_service: ThemeService) -> None:
    """Verify updating custom colors and typography."""
    dto = UpdateThemeRequestDTO(
        preset_key=ColorPresetKey.CUSTOM,
        primary_color="#123456",
        primary_hover="#0A1E2F",
        secondary_color="#654321",
        accent_color="#AABBCC",
        background_color="#FAF8F5",
        surface_color="#FFFFFF",
        surface_muted="#F0F0F0",
        text_main_color="#111111",
        text_muted_color="#555555",
        border_color="#DDDDDD",
        heading_font="Playfair Display",
        body_font="Rubik",
        active_shape=ShapeType.SOFT_PEBBLE,
        motif_enabled=True,
        motif_animation_speed="slow",
    )
    saved = await theme_service.update_theme(dto)

    assert saved.primary_color == "#123456"
    assert saved.heading_font == "Playfair Display"
    assert saved.body_font == "Rubik"
    assert saved.active_shape == ShapeType.SOFT_PEBBLE


def test_theme_css_variable_generation(theme_service: ThemeService) -> None:
    """Verify dynamic CSS variable block generation for Jinja2."""
    presets = theme_service.get_all_color_presets()
    shapes = theme_service.get_all_shapes()
    assert len(presets) == 5
    assert len(shapes) == 5

    sample_dto = ThemeConfigDTO(
        primary_color="#4A6C50",
        primary_hover="#3C5641",
        secondary_color="#CEDECF",
        accent_color="#7FA485",
        background_color="#FAF8F5",
        surface_color="#FFFFFF",
        surface_muted="#F3EFE8",
        text_main_color="#1E293B",
        text_muted_color="#64748B",
        border_color="#E6DED1",
        heading_font="Lora",
        body_font="Plus Jakarta Sans",
        active_shape=ShapeType.DANDELION_SEED,
    )
    css = theme_service.generate_css_variables(sample_dto)

    assert "--theme-primary: #4A6C50" in css
    assert "--theme-bg: #FAF8F5" in css
    assert "--font-heading: 'Lora', serif" in css
    assert "--theme-shape-radius:" in css


@pytest.mark.asyncio
async def test_admin_design_routes(app_client: AsyncTestClient[Litestar]) -> None:
    """Verify GET and POST endpoints of the Design Studio."""
    # 1. Unauthenticated GET /admin/design redirects to login
    res = await app_client.get("/admin/design", follow_redirects=False)
    assert res.status_code in [302, 307]
    assert "/admin/login" in res.headers.get("location", "")

    # 2. Public page / includes theme CSS and Pusteblume motif
    pub_res = await app_client.get("/")
    assert pub_res.status_code == 200
    assert "dandelion_hero.png" in pub_res.text
    assert "--theme-primary" in pub_res.text
    assert "Atem" in pub_res.text

    # 3. Authenticate as Admin
    login_data = {"username": "admin", "password": "admin-secure-init-pass-change-me"}
    login_res = await app_client.post("/admin/login", data=login_data, follow_redirects=False)
    assert login_res.status_code == 302
    session_cookies = login_res.cookies

    # 4. Access Design Studio with session cookies
    design_page = await app_client.get("/admin/design", cookies=session_cookies)
    assert design_page.status_code == 200
    assert "Corporate Design Studio" in design_page.text
    assert "Lavendel &amp; Nebel" in design_page.text or "Lavendel & Nebel" in design_page.text

    # 5. Apply a preset theme via POST
    preset_post = await app_client.post(
        "/admin/design/preset",
        data={"preset_key": "lavendel_nebel"},
        cookies=session_cookies,
        follow_redirects=True,
    )
    assert preset_post.status_code == 200

    # 6. Apply a shape via POST
    shape_post = await app_client.post(
        "/admin/design/shape",
        data={"shape_type": "soft_pebble"},
        cookies=session_cookies,
        follow_redirects=True,
    )
    assert shape_post.status_code == 200

    # 7. Apply custom design
    custom_post = await app_client.post(
        "/admin/design/custom",
        data={
            "primary_color": "#223344",
            "secondary_color": "#AABBCC",
            "accent_color": "#556677",
            "background_color": "#FAFAFA",
            "surface_color": "#FFFFFF",
            "surface_muted": "#F0F0F0",
            "text_main_color": "#111111",
            "text_muted_color": "#666666",
            "border_color": "#E0E0E0",
            "heading_font": "Playfair Display",
            "body_font": "Rubik",
            "active_shape": "breath_wave",
            "motif_enabled": "true",
            "motif_animation_speed": "slow",
        },
        cookies=session_cookies,
        follow_redirects=True,
    )
    assert custom_post.status_code == 200
