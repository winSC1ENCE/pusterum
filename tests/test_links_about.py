"""Links in the training entries and the practice description (migration 0025)."""

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import sqlalchemy as sa
from litestar import Litestar
from litestar.testing import AsyncTestClient

from atem.infrastructure.database.seed.content_defaults import DEFAULT_CONTENT_BLOCKS

ROOT = Path(__file__).resolve().parent.parent
BLOCKS = {block["key"]: block for block in DEFAULT_CONTENT_BLOCKS}


def _migration() -> ModuleType:
    sys.path.insert(0, str(ROOT / "migrations"))  # migrations import _helpers like alembic does
    path = next((ROOT / "migrations/versions").glob("*-0025_links_about.py"))
    spec = importlib.util.spec_from_file_location("links_migration", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MIGRATION = _migration()
HELPERS = sys.modules["_helpers"]

# Texts as edited by the practice owner on production (2026-10-30)
LIVE_CREDENTIALS = {
    "about.credential_1": (
        "2023 – heute: Ausbildung Ganzheitlich integrative Atemtherapie,"
        " Institut für Körperzentrierte Psychotherapie IKP"
    ),
    "about.credential_2": "2026: Mitglied beim Atemfachverband AFS",
    "about.credential_3": "2014: Diplom Yogalehrerin, International Sivananda Yoga Vedanta Centre",
    "about.credential_4": "2006 – 2007: Diplom ErnährungsCoach, Klubschule Migros",
}
LIVE_DESCRIPTION = (
    "Die Praxis PUSTERUM ist eingebettet in die modern ausgestattete Gemeinschaftspraxis"
    " LaFontaine. Ein geschützter, ruhiger Raum."
)


def test_live_texts_get_all_five_links() -> None:
    linked = {
        key: HELPERS.add_links(text, MIGRATION.CHANGES[key])
        for key, text in LIVE_CREDENTIALS.items()
    }
    assert linked["about.credential_1"].endswith(
        "[Institut für Körperzentrierte Psychotherapie IKP](https://www.ikp-therapien.com/)"
    )
    assert "[Atemfachverband AFS](https://www.atem-schweiz.ch/)" in linked["about.credential_2"]
    assert "](https://sivananda.org.in/)" in linked["about.credential_3"]
    assert "[Klubschule Migros](https://www.klubschule.ch/)" in linked["about.credential_4"]
    description = HELPERS.add_links(LIVE_DESCRIPTION, MIGRATION.DESCRIPTION_LINKS)
    assert "Gemeinschaftspraxis [LaFontaine](https://physio-lafontaine.ch/)." in description


def test_add_links_is_idempotent_and_keeps_unknown_texts() -> None:
    once = HELPERS.add_links(LIVE_CREDENTIALS["about.credential_1"], MIGRATION.CREDENTIAL_LINKS)
    assert HELPERS.add_links(once, MIGRATION.CREDENTIAL_LINKS) == once
    assert HELPERS.add_links("Ohne Bezug", MIGRATION.CREDENTIAL_LINKS) == "Ohne Bezug"


def test_old_defaults_become_the_current_defaults() -> None:
    """Untouched blocks end up exactly like a freshly seeded database."""
    old_defaults = {
        "about.credential_1": (
            "2023 – heute: Ausbildung Ganzheitlich integrative Atemtherapie,"
            " IKP Institut für Körperzentrierte Psychotherapie"
        ),
        "about.credential_2": (
            "2014: Diplom Yogalehrerin, International Sivananda Yoga Vedanta Centre"
        ),
        "about.credential_3": "2006 – 2007: Diplom ErnährungsCoach, Klubschule Migros",
    }
    for key, old in old_defaults.items():
        assert HELPERS.add_links(old, MIGRATION.CHANGES[key]) == BLOCKS[key]["content"]
    for key in [*old_defaults, "about.credential_4", "practice.description"]:
        assert BLOCKS[key]["type"] == "rich_text"


def test_link_phrases_writes_a_new_version() -> None:
    engine = sa.create_engine("sqlite://")
    meta = sa.MetaData()
    blocks = sa.Table(
        "content_blocks",
        meta,
        sa.Column("key", sa.String, primary_key=True),
        sa.Column("current_version_number", sa.Integer),
        sa.Column("current_content", sa.Text),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
    )
    versions = sa.Table(
        "content_block_versions",
        meta,
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("block_key", sa.String),
        sa.Column("version_number", sa.Integer),
        sa.Column("content", sa.Text),
        sa.Column("author_name", sa.String),
        sa.Column("change_summary", sa.String),
        sa.Column("created_at", sa.DateTime(timezone=True)),
    )
    meta.create_all(engine)
    with engine.begin() as bind:
        bind.execute(
            sa.insert(blocks),
            [
                {"key": k, "current_version_number": 3, "current_content": v}
                for k, v in {**LIVE_CREDENTIALS, "practice.description": "Ohne Namen"}.items()
            ],
        )
        assert HELPERS.link_phrases(bind, MIGRATION.CHANGES, "Links") == 4
        assert HELPERS.link_phrases(bind, MIGRATION.CHANGES, "Links") == 0
        row = bind.execute(sa.select(blocks).where(blocks.c.key == "about.credential_2")).one()
        assert row.current_version_number == 4
        assert row.current_content.endswith("(https://www.atem-schweiz.ch/)")
        history = bind.execute(sa.select(versions.c.author_name, versions.c.content)).all()
        assert len(history) == 4
        assert {author for author, _ in history} == {"System Migration"}
        unchanged = bind.execute(
            sa.select(blocks.c.current_version_number).where(blocks.c.key == "practice.description")
        ).scalar_one()
        assert unchanged == 3


async def test_page_renders_links_badge_and_navigation(
    app_client: AsyncTestClient[Litestar],
) -> None:
    page = (await app_client.get("/")).text
    assert (
        '<a href="https://www.ikp-therapien.com/" target="_blank" rel="noopener noreferrer">'
        in page
    )
    assert "Über mich" in page and "Philosophie &amp; Praxis" not in page
    assert 'href="/#kompetenzen" class="hover:text-theme-primary' in page
    assert ">Methode</a>" in page and ">Angebot</a>" in page
    assert ">Kompetenzen</a>" not in page
