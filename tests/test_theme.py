import itertools

import pytest
from litestar import Litestar
from litestar.testing import AsyncTestClient
from sqlalchemy.ext.asyncio import AsyncSession

from atem.application.dto.theme import ThemeConfigDTO, UpdateThemeRequestDTO
from atem.application.services.theme_service import ThemeService
from atem.domain.models.theme import (
    ColorPresetKey,
    DandelionEffectMode,
    PageSection,
    ShapeType,
    hex_to_rgb_channels,
)
from atem.infrastructure.database.models.theme import ThemeConfigModel
from atem.infrastructure.database.repositories.sqlalchemy_theme_repository import (
    SqlAlchemyThemeRepository,
)
from tests.conftest import refresh_csrf


@pytest.mark.asyncio
async def test_default_theme_initialization(theme_service: ThemeService) -> None:
    """Verify default active theme is initialized correctly with Salbei & Sand."""
    theme = await theme_service.get_active_theme()

    assert theme.preset_key == ColorPresetKey.SALBEI_SAND
    assert theme.primary_color == "#4A6C50"
    assert theme.active_shape == ShapeType.DANDELION_SEED
    assert theme.heading_font == "Lora"
    assert theme.body_font == "Plus Jakarta Sans"
    assert theme.dandelion_modes == [DandelionEffectMode.DISABLED]


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
async def test_apply_all_dandelion_modes(theme_service: ThemeService) -> None:
    """Verify switching between all 6 ambient dandelion effect modes."""
    modes = [
        DandelionEffectMode.DISABLED,
        DandelionEffectMode.BREATHING_FLOW,
        DandelionEffectMode.SCROLL_JOURNEY,
        DandelionEffectMode.WATERMARK_ACCENTS,
        DandelionEffectMode.BREATH_WIDGET,
        DandelionEffectMode.WHISPER_TRAIL,
    ]

    for mode in modes:
        theme = await theme_service.apply_dandelion_modes([mode])
        assert theme.dandelion_modes == [mode]


@pytest.mark.asyncio
async def test_apply_multiple_dandelion_modes(theme_service: ThemeService) -> None:
    """Verify combining multiple ambient effect modes simultaneously."""
    combined_modes = [
        DandelionEffectMode.BREATHING_FLOW,
        DandelionEffectMode.BREATH_WIDGET,
    ]
    theme = await theme_service.apply_dandelion_modes(
        modes=combined_modes,
        seed_size=56,
        seed_opacity=85,
    )

    assert theme.has_dandelion_mode(DandelionEffectMode.BREATHING_FLOW)
    assert theme.has_dandelion_mode(DandelionEffectMode.BREATH_WIDGET)
    assert not theme.has_dandelion_mode(DandelionEffectMode.SCROLL_JOURNEY)
    assert "breathing_flow" in theme.dandelion_modes_list
    assert "breath_widget" in theme.dandelion_modes_list
    assert theme.dandelion_seed_size == 56
    assert theme.dandelion_seed_opacity == 85


@pytest.mark.asyncio
async def test_dandelion_sliders_are_clamped(theme_service: ThemeService) -> None:
    """Seed size and opacity are clamped to their domain limits."""
    theme = await theme_service.apply_dandelion_modes(
        [DandelionEffectMode.WATERMARK_ACCENTS], seed_size=500, seed_opacity=1
    )
    assert theme.dandelion_modes == [DandelionEffectMode.WATERMARK_ACCENTS]
    assert theme.dandelion_seed_size == 120
    assert theme.dandelion_seed_opacity == 10


def test_theme_dto_mode_helpers() -> None:
    """ThemeConfigDTO helpers used by the templates."""
    dto = ThemeConfigDTO(
        dandelion_modes=[DandelionEffectMode.BREATHING_FLOW, DandelionEffectMode.BREATH_WIDGET]
    )
    assert dto.has_dandelion_mode("breathing_flow")
    assert dto.has_dandelion_mode(DandelionEffectMode.BREATH_WIDGET)
    assert not dto.has_dandelion_mode("disabled")
    assert dto.dandelion_modes_list == ["breathing_flow", "breath_widget"]


@pytest.mark.asyncio
async def test_theme_repository_persistence(db_session: AsyncSession) -> None:
    """The repository stores the modes as text and parses malformed values safely."""
    repo = SqlAlchemyThemeRepository(db_session)
    theme = await repo.get_active_theme()
    theme.dandelion_modes = [DandelionEffectMode.BREATHING_FLOW, DandelionEffectMode.WHISPER_TRAIL]
    saved = await repo.save_theme(theme)
    assert saved.dandelion_modes == theme.dandelion_modes
    assert (await repo.get_active_theme()).id == saved.id

    raw_model = ThemeConfigModel(
        dandelion_mode=",,unknown_mode,breath_widget,,",
        dandelion_seed_size=50,
        dandelion_seed_opacity=80,
    )
    assert repo._to_entity(raw_model).dandelion_modes == [DandelionEffectMode.BREATH_WIDGET]
    empty_model = ThemeConfigModel(dandelion_mode="invalid1,invalid2")
    assert repo._to_entity(empty_model).dandelion_modes == [DandelionEffectMode.DISABLED]


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
        dandelion_modes=[DandelionEffectMode.BREATHING_FLOW],
    )
    saved = await theme_service.update_theme(dto)

    assert saved.primary_color == "#123456"
    assert saved.heading_font == "Playfair Display"
    assert saved.body_font == "Rubik"
    assert saved.active_shape == ShapeType.SOFT_PEBBLE
    assert saved.dandelion_modes == [DandelionEffectMode.BREATHING_FLOW]
    assert saved.name == "Individuelles Design"


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
    # RGB channels for Tailwind opacity steps (bg-theme-primary/20 …)
    assert "--theme-primary-rgb: 74 108 80;" in css
    assert "--theme-text-main-rgb: 30 41 59;" in css
    assert css.count("-rgb:") == 10


@pytest.mark.parametrize(
    ("value", "channels"),
    [
        ("#4A6C50", "74 108 80"),
        ("#fff", "255 255 255"),
        ("#0F0A", "0 255 0"),
        ("#00000080", "0 0 0"),
    ],
)
def test_hex_to_rgb_channels(value: str, channels: str) -> None:
    assert hex_to_rgb_channels(value) == channels


def test_hex_to_rgb_channels_rejects_non_hex() -> None:
    with pytest.raises(ValueError, match="hex"):
        hex_to_rgb_channels("red; }")


@pytest.mark.asyncio
async def test_admin_design_routes_and_presets(
    app_client: AsyncTestClient[Litestar],
) -> None:
    """Verify GET, preset switching, shapes, and mode activation in Design Studio."""
    # 1. Unauthenticated GET /admin/design redirects to login
    res = await app_client.get("/admin/design", follow_redirects=False)
    assert res.status_code in [302, 307]
    assert "/admin/login" in res.headers.get("location", "")

    # 2. Public page / includes theme CSS
    pub_res = await app_client.get("/")
    assert pub_res.status_code == 200
    assert "dandelion_hero.png" in pub_res.text
    assert 'href="/theme.css?v=' in pub_res.text
    theme_css = await app_client.get("/theme.css")
    assert theme_css.headers["content-type"].startswith("text/css")
    assert "--theme-primary" in theme_css.text
    assert "Atem" in pub_res.text

    # 3. Authenticate as Admin
    login_data = {
        "email": "entwicklung@pusterum.be",
        "password": "admin-secure-init-pass-change-me",
    }
    login_res = await app_client.post("/admin/login", data=login_data, follow_redirects=False)
    assert login_res.status_code == 302

    # 4. Access Design Studio with session cookies
    design_page = await app_client.get("/admin/design")
    assert design_page.status_code == 200
    assert "Corporate Design Studio" in design_page.text
    assert "Lavendel &amp; Nebel" in design_page.text or "Lavendel & Nebel" in design_page.text
    assert "Pusteblumen- &amp; Samen-Aesthetik" in design_page.text

    # 5. Apply a preset theme via POST
    preset_post = await app_client.post(
        "/admin/design/preset",
        data={"preset_key": "lavendel_nebel"},
        follow_redirects=True,
    )
    assert preset_post.status_code == 200

    # 6. Apply a shape via POST
    shape_post = await app_client.post(
        "/admin/design/shape",
        data={"shape_type": "soft_pebble"},
        follow_redirects=True,
    )
    assert shape_post.status_code == 200

    # 7. Apply a dandelion ambient effect mode and slider settings via POST
    dandelion_post = await app_client.post(
        "/admin/design/dandelion",
        data={
            "dandelion_mode": "breathing_flow",
            "dandelion_seed_size": "56",
            "dandelion_seed_opacity": "90",
        },
        follow_redirects=True,
    )
    assert dandelion_post.status_code == 200

    # 8. Check public page has active dandelion engine and correct size/opacity
    pub_active_res = await app_client.get("/")
    assert pub_active_res.status_code == 200
    assert 'data-mode="breathing_flow"' in pub_active_res.text
    theme_css = (await app_client.get("/theme.css")).text
    assert "--dandelion-seed-size: 56px;" in theme_css
    assert "--dandelion-seed-opacity: 0.90;" in theme_css


@pytest.mark.asyncio
async def test_admin_design_autosave_and_guards(
    app_client: AsyncTestClient[Litestar], theme_service: ThemeService
) -> None:
    """Verify custom theme autosave, preset preservation, HTMX responses, and guards."""
    login_data = {
        "email": "entwicklung@pusterum.be",
        "password": "admin-secure-init-pass-change-me",
    }
    login_res = await app_client.post("/admin/login", data=login_data, follow_redirects=False)
    assert login_res.status_code == 302  # client keeps the session cookie

    # 1. Apply custom design including sliders
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
            "dandelion_seed_size": "60",
            "dandelion_seed_opacity": "85",
        },
        follow_redirects=True,
    )
    assert custom_post.status_code == 200

    # 2. HTMX background autosave returns 204 No Content for multi-modes
    htmx_post = await app_client.post(
        "/admin/design/dandelion",
        data={
            "dandelion_modes": "breathing_flow,breath_widget",
            "dandelion_seed_size": "64",
            "dandelion_seed_opacity": "88",
        },
        headers={"hx-request": "true"},
    )
    assert htmx_post.status_code == 204
    active_theme = await theme_service.get_active_theme()
    assert active_theme.has_dandelion_mode(DandelionEffectMode.BREATHING_FLOW)
    assert active_theme.has_dandelion_mode(DandelionEffectMode.BREATH_WIDGET)

    # 3. Preset preservation when editing typography on an active preset
    await app_client.post(
        "/admin/design/preset",
        data={"preset_key": "salbei_sand"},
    )
    salbei_post = await app_client.post(
        "/admin/design/custom",
        data={
            "primary_color": "#4A6C50",
            "secondary_color": "#CEDECF",
            "accent_color": "#7FA485",
            "background_color": "#FAF8F5",
            "surface_color": "#FFFFFF",
            "border_color": "#E6DED1",
            "heading_font": "Playfair Display",
            "body_font": "Rubik",
        },
        headers={"hx-request": "true"},
    )
    assert salbei_post.status_code == 204
    active_theme = await theme_service.get_active_theme()
    assert active_theme.preset_key == ColorPresetKey.SALBEI_SAND
    assert active_theme.heading_font == "Playfair Display"

    # 4. HTMX autosave for preset and shape returning 204
    preset_htmx = await app_client.post(
        "/admin/design/preset",
        data={"preset_key": "lavendel_nebel"},
        headers={"hx-request": "true"},
    )
    assert preset_htmx.status_code == 204

    shape_htmx = await app_client.post(
        "/admin/design/shape",
        data={"shape_type": "zen_circle"},
        headers={"hx-request": "true"},
    )
    assert shape_htmx.status_code == 204

    # 5. Invalid inputs graceful fallback
    invalid_preset = await app_client.post(
        "/admin/design/preset",
        data={"preset_key": "invalid_key"},
        headers={"hx-request": "true"},
    )
    assert invalid_preset.status_code == 204

    invalid_shape = await app_client.post(
        "/admin/design/shape",
        data={"shape_type": "invalid_shape"},
        headers={"hx-request": "true"},
    )
    assert invalid_shape.status_code == 204

    invalid_dandelion = await app_client.post(
        "/admin/design/dandelion",
        data={
            "dandelion_mode": "invalid_mode",
            "dandelion_seed_size": "not_an_int",
            "dandelion_seed_opacity": "not_an_int",
        },
        headers={"hx-request": "true"},
    )
    assert invalid_dandelion.status_code == 204

    # 6. Unauthenticated POST guards (valid CSRF token, but no session)
    app_client.cookies.clear()
    await app_client.get("/")
    app_client.headers["x-csrftoken"] = app_client.cookies["csrftoken"]
    unauth_preset = await app_client.post(
        "/admin/design/preset",
        data={"preset_key": "salbei_sand"},
        follow_redirects=False,
    )
    assert unauth_preset.status_code == 302
    assert "/admin/login" in unauth_preset.headers.get("location", "")

    unauth_shape = await app_client.post(
        "/admin/design/shape",
        data={"shape_type": "zen_circle"},
        follow_redirects=False,
    )
    assert unauth_shape.status_code == 302
    assert "/admin/login" in unauth_shape.headers.get("location", "")

    unauth_dandelion = await app_client.post(
        "/admin/design/dandelion",
        data={"dandelion_mode": "breathing_flow"},
        follow_redirects=False,
    )
    assert unauth_dandelion.status_code == 302
    assert "/admin/login" in unauth_dandelion.headers.get("location", "")

    unauth_custom = await app_client.post(
        "/admin/design/custom",
        data={"primary_color": "#112233"},
        follow_redirects=False,
    )
    assert unauth_custom.status_code == 302
    assert "/admin/login" in unauth_custom.headers.get("location", "")


@pytest.mark.asyncio
async def test_all_dandelion_mode_combinations_and_rendering(
    app_client: AsyncTestClient[Litestar],
) -> None:
    """Exhaustive integration test verifying all 32 dandelion mode combinations (2^5)."""
    # 1. Login
    login_res = await app_client.post(
        "/admin/login",
        data={"email": "entwicklung@pusterum.be", "password": "admin-secure-init-pass-change-me"},
        follow_redirects=True,
    )
    assert login_res.status_code == 200

    modes = [
        DandelionEffectMode.BREATHING_FLOW,
        DandelionEffectMode.SCROLL_JOURNEY,
        DandelionEffectMode.WATERMARK_ACCENTS,
        DandelionEffectMode.BREATH_WIDGET,
        DandelionEffectMode.WHISPER_TRAIL,
    ]

    # 2. Test 'disabled' single mode
    res_dis = await app_client.post(
        "/admin/design/dandelion",
        data={
            "dandelion_modes": "disabled",
            "dandelion_seed_size": "50",
            "dandelion_seed_opacity": "80",
        },
        headers={"hx-request": "true"},
    )
    assert res_dis.status_code == 204

    res_land_dis = await app_client.get("/")
    assert res_land_dis.status_code == 200

    # 3. Test all 31 active combinations
    for r in range(1, len(modes) + 1):
        for combo in itertools.combinations(modes, r):
            combo_str = ",".join(m.value for m in combo)
            res_save = await app_client.post(
                "/admin/design/dandelion",
                data={
                    "dandelion_modes": combo_str,
                    "dandelion_seed_size": "52",
                    "dandelion_seed_opacity": "85",
                },
                headers={"hx-request": "true"},
            )
            assert res_save.status_code == 204

            res_land = await app_client.get("/")
            assert res_land.status_code == 200
            html = res_land.text

            for m in combo:
                if m == DandelionEffectMode.BREATHING_FLOW:
                    assert "seedBreathFloat1" in html
                elif m == DandelionEffectMode.SCROLL_JOURNEY:
                    assert "Reisender Pusteblumen-Samen" in html
                elif m == DandelionEffectMode.WATERMARK_ACCENTS:
                    assert "Wasserzeichen Samen" in html
                elif m == DandelionEffectMode.BREATH_WIDGET:
                    assert "Geführte Atem-Pause" in html
                elif m == DandelionEffectMode.WHISPER_TRAIL:
                    assert 'x-data="whisperTrail"' in html


async def test_header_opacity_is_adjustable_clamped_and_kept(
    app_client: AsyncTestClient[Litestar],
) -> None:
    """Design Studio slider «Kopfzeile: Deckkraft» drives the glass effect of the sticky header."""
    assert "--header-bg-opacity: 0.60;" in (await app_client.get("/theme.css")).text  # default
    home = (await app_client.get("/")).text
    assert "bg-theme-main/[var(--header-bg-opacity,0.6)] backdrop-blur-md" in home

    await app_client.post(
        "/admin/login",
        data={"email": "entwicklung@pusterum.be", "password": "admin-secure-init-pass-change-me"},
    )
    assert 'name="header_opacity"' in (await app_client.get("/admin/design")).text

    await app_client.post("/admin/design/custom", data={"header_opacity": "20"})
    assert "--header-bg-opacity: 0.20;" in (await app_client.get("/theme.css")).text

    # Out-of-range values are clamped instead of failing the auto-save
    await app_client.post("/admin/design/custom", data={"header_opacity": "150"})
    assert "--header-bg-opacity: 1.00;" in (await app_client.get("/theme.css")).text

    # Presets, ambient modes and colour saves without the field keep the value
    await app_client.post("/admin/design/custom", data={"header_opacity": "35"})
    await app_client.post("/admin/design/preset", data={"preset_key": "lavendel_nebel"})
    await app_client.post("/admin/design/dandelion", data={"dandelion_modes": "disabled"})
    await app_client.post("/admin/design/custom", data={"primary_color": "#4A6C50"})
    assert "--header-bg-opacity: 0.35;" in (await app_client.get("/theme.css")).text


async def test_phone_can_be_hidden_publicly_and_stays_editable(
    app_client: AsyncTestClient[Litestar],
) -> None:
    """Switch «Telefonnummer anzeigen»: hidden publicly, kept and labelled for admins."""
    admin = {"email": "entwicklung@pusterum.be", "password": "admin-secure-init-pass-change-me"}
    assert 'href="tel:' in (await app_client.get("/")).text  # default: visible
    assert 'href="tel:' in (await app_client.get("/impressum")).text

    await app_client.post("/admin/login", data=admin)
    assert 'name="show_phone"' in (await app_client.get("/admin/design")).text
    # Unchecked checkbox: only the marker is submitted
    await app_client.post("/admin/design/custom", data={"show_phone_field": "1"})
    admin_home = (await app_client.get("/")).text
    assert "data-phone-hidden" in admin_home
    assert "Öffentlich ausgeblendet" in admin_home

    # Other forms without the field (presets, ambient modes, colours) keep the setting
    await app_client.post("/admin/design/preset", data={"preset_key": "lavendel_nebel"})
    await app_client.post("/admin/design/dandelion", data={"dandelion_modes": "disabled"})
    await app_client.post("/admin/design/custom", data={"primary_color": "#4A6C50"})

    app_client.cookies.clear()  # visitor view
    for path in ("/", "/impressum"):
        page = (await app_client.get(path)).text
        assert 'href="tel:' not in page, path
        assert "Öffentlich ausgeblendet" not in page
    assert 'href="mailto:' in (await app_client.get("/")).text  # e-mail card stays

    await refresh_csrf(app_client)
    await app_client.post("/admin/login", data=admin)
    await app_client.post("/admin/design/custom", data={"show_phone_field": "1", "show_phone": "1"})
    app_client.cookies.clear()
    assert 'href="tel:' in (await app_client.get("/")).text


DEFAULT_SECTIONS = ["competencies", "services", "kids", "about", "quotes", "practice"]


def test_section_order_parse_is_always_complete() -> None:
    """Unknown values and duplicates are dropped, missing sections appended in default order."""
    assert PageSection.parse_order(None) == DEFAULT_SECTIONS
    assert PageSection.parse_order("about, hero,about,practice") == [
        "about",
        "practice",
        "competencies",
        "services",
        "kids",
        "quotes",
    ]


def test_section_move_is_clamped() -> None:
    order = list(PageSection)
    assert PageSection.move(order, PageSection.ABOUT, -1)[2] == PageSection.ABOUT
    assert PageSection.move(order, PageSection.COMPETENCIES, -1) == order
    assert PageSection.move(order, PageSection.PRACTICE, 1) == order
    assert PageSection.move(order, PageSection.COMPETENCIES, 1)[:2] == ["services", "competencies"]


@pytest.mark.asyncio
async def test_section_order_is_persisted(theme_service: ThemeService) -> None:
    theme = await theme_service.get_active_theme()
    assert theme.section_order == DEFAULT_SECTIONS
    await theme_service.move_section(PageSection.QUOTES, -4)
    theme = await theme_service.get_active_theme()
    assert theme.section_order[0] == PageSection.QUOTES
    # Other design changes keep the order
    await theme_service.set_preset(ColorPresetKey.LAVENDEL_NEBEL)
    assert (await theme_service.get_active_theme()).section_order[0] == PageSection.QUOTES


def _positions(page: str, *needles: str) -> list[int]:
    return [page.index(n) for n in needles]


async def test_section_order_drives_page_and_navigation(
    app_client: AsyncTestClient[Litestar],
) -> None:
    """Design studio ↑/↓ reorders the start page, desktop/mobile navigation and footer."""
    sections = ('id="kompetenzen"', 'id="angebote"', 'id="ueber-mich"', 'id="praxis"')
    page = (await app_client.get("/")).text
    assert _positions(page, *sections) == sorted(_positions(page, *sections))
    assert page.index('id="start"') < page.index('id="kompetenzen"')
    assert page.index('id="praxis"') < page.index('id="kontakt"')
    assert page.count('href="/#kinder"') == 0  # children's offer disabled by default

    await app_client.post(
        "/admin/login",
        data={"email": "entwicklung@pusterum.be", "password": "admin-secure-init-pass-change-me"},
    )
    design = (await app_client.get("/admin/design")).text
    assert "5. Reihenfolge der Abschnitte" in design
    for _ in range(5):  # «Über mich» to the top (clamped)
        moved = await app_client.post(
            "/admin/design/sections", data={"section": "about", "direction": "up"}
        )
        assert moved.status_code in (200, 302, 303)
    # HTMX gets only the card (no page reload)
    card = await app_client.post(
        "/admin/design/sections",
        data={"section": "about", "direction": "up"},
        headers={"hx-request": "true"},
    )
    assert card.status_code == 200
    assert 'id="section-order"' in card.text
    assert "<html" not in card.text
    assert 'hx-post="/admin/design/sections"' in card.text
    # Invalid input is ignored
    await app_client.post("/admin/design/sections", data={"section": "hero", "direction": "up"})
    await app_client.post("/admin/design/sections", data={"section": "about", "direction": "x"})

    app_client.cookies.clear()
    page = (await app_client.get("/")).text
    assert page.index('id="ueber-mich"') < page.index('id="kompetenzen"')
    assert page.index('id="start"') < page.index('id="ueber-mich"')
    nav = [page.index('href="/#ueber-mich"'), page.index('href="/#kompetenzen"')]
    assert nav == sorted(nav)
    footer = page[page.index("<footer") :]
    assert footer.index('href="/#ueber-mich"') < footer.index('href="/#kompetenzen"')


async def test_section_route_requires_admin(app_client: AsyncTestClient[Litestar]) -> None:
    response = await app_client.post(
        "/admin/design/sections", data={"section": "about", "direction": "up"}
    )
    assert response.status_code in (401, 403) or "/admin/login" in str(response.url)
    page = (await app_client.get("/")).text
    assert page.index('id="kompetenzen"') < page.index('id="ueber-mich"')  # unchanged
