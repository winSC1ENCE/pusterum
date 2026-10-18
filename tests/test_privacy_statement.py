"""Privacy statement after the EDÖB guidance (tech-debt #6, ADR-0006, Art. 19 DSG)."""

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

from litestar import Litestar
from litestar.testing import AsyncTestClient

from atem.infrastructure.database.seed.content_defaults import (
    DEFAULT_CONTENT_BLOCKS,
    count_numbered_keys,
)

ROOT = Path(__file__).resolve().parent.parent
DEFAULTS = {block["key"]: block["content"] for block in DEFAULT_CONTENT_BLOCKS}
PRIVACY_TEXT = " ".join(v for k, v in DEFAULTS.items() if k.startswith("datenschutz."))


def _migration() -> ModuleType:
    sys.path.insert(0, str(ROOT / "migrations"))  # migrations import _helpers like alembic does
    path = next((ROOT / "migrations/versions").glob("*-0020_privacy_statement.py"))
    spec = importlib.util.spec_from_file_location("privacy_migration", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_statement_covers_the_information_duty() -> None:
    """EDÖB: controller and contact, purpose, recipients and countries, retention, rights."""
    for required in (
        "Verantwortliche Stelle",
        "info@pusterum.be",
        "nur, um Ihre Anfrage zu beantworten",
        "besonders schützenswerte Personendaten",
        "6 Monate nach Abschluss",
        "Spam nach 7 Tagen",
        "spätestens 12 Monate nach Eingang",
        "nach 7 Tagen gelöscht",  # IP addresses
        "bis zu 6 Monate",  # backups
        "Auftragsbearbeiter",
        "Deutschland",
        "angemessenes Datenschutzniveau",
        "innert 30 Tagen",
        "EDÖB",
    ):
        assert required in PRIVACY_TEXT, required


def test_statement_names_no_providers() -> None:
    """Provider names only live in the encrypted runbook (CLAUDE.md)."""
    for provider in ("Hetzner", "Proton", "Finnland"):
        assert provider not in PRIVACY_TEXT


def test_migration_targets_the_current_defaults() -> None:
    changes = _migration().CHANGES
    assert {key: new for key, (_, new) in changes.items()} == {
        key: DEFAULTS[key] for key in changes
    }


async def test_page_has_summary_all_sections_and_form_link(
    app_client: AsyncTestClient[Litestar],
) -> None:
    page = (await app_client.get("/datenschutz")).text
    assert 'data-testid="privacy-summary"' in page
    sections = count_numbered_keys("datenschutz.sec", "_title")
    assert sections == 9
    for n in range(1, sections + 1):
        assert DEFAULTS[f"datenschutz.sec{n}_title"] in page
    assert "Keine Werbung, kein Tracking" in page

    home = (await app_client.get("/")).text
    assert 'href="/datenschutz" class="inline-block mt-2' in home
    assert "keine ausführlichen Gesundheitsangaben" in home
