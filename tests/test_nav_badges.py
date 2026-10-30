"""Menu labels follow the section badges edited by the practice owner (migration 0026)."""

import importlib.util
import sys
from pathlib import Path

from litestar import Litestar
from litestar.testing import AsyncTestClient

from atem.infrastructure.database.seed.content_defaults import DEFAULT_CONTENT_BLOCKS
from atem.presentation.templating import nav_sections

ROOT = Path(__file__).resolve().parent.parent
DEFAULTS = {block["key"]: block["content"] for block in DEFAULT_CONTENT_BLOCKS}


def test_migration_targets_the_current_defaults() -> None:
    sys.path.insert(0, str(ROOT / "migrations"))  # migrations import _helpers like alembic does
    path = next((ROOT / "migrations/versions").glob("*-0026_nav_badges.py"))
    spec = importlib.util.spec_from_file_location("nav_badges_migration", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert {key: new for key, (_, new) in module.CHANGES.items()} == {
        key: DEFAULTS[key] for key in module.CHANGES
    }


class _Block:
    def __init__(self, content: str) -> None:
        self.current_content = content


def test_labels_come_from_badges_with_fallback() -> None:
    blocks = {"about.badge": _Block("  Ich \n "), "services.badge": _Block("")}
    links = {link["key"]: link for link in nav_sections(None, blocks)}
    assert links["about"]["short"] == links["about"]["label"] == "Ich"
    assert links["services"]["short"] == "Angebot"  # empty badge → fallback
    assert links["services"]["label"] == "Angebot & Tarife"
    assert links["competencies"]["short"] == DEFAULTS["competencies.badge"]  # not edited yet
    assert links["practice"]["anchor"] == "praxis"


async def test_edited_badge_renames_the_menu(app_client: AsyncTestClient[Litestar]) -> None:
    await app_client.post(
        "/admin/login",
        data={"email": "entwicklung@pusterum.be", "password": "admin-secure-init-pass-change-me"},
        follow_redirects=True,
    )
    saved = await app_client.post("/admin/content/about.badge/save", data={"content": "Ich"})
    assert saved.status_code == 200
    app_client.cookies.clear()
    page = (await app_client.get("/")).text
    assert 'href="/#ueber-mich" class="hover:text-theme-primary transition-colors py-1' in page
    assert ">Ich</a>" in page  # desktop, mobile menu and footer
    assert ">Über mich</a>" not in page
    assert "Über mich &amp; PUSTERUM</a>" not in page
