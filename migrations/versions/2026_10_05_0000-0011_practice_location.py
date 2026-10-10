"""Practice location in Biel: directions become a formatted rich-text block.

Data-only migration (see TDR-0003). ``practice.directions`` switches to the block type
``rich_text`` (bold, italic, underline, bullet lists). The former directions/accessibility
defaults described a fictitious location in Bern – untouched blocks get the new directions
text or are emptied (hidden publicly). The new ``practice.location_*`` blocks (partner
practice Physio La Fontaine) are seeded automatically at startup.

Revision ID: 0011_practice_location
Revises: 0010_email_login
Create Date: 2026-10-05 00:00:00 UTC

"""

# ruff: noqa: E501  (frozen default-text snapshots)

from collections.abc import Sequence

import sqlalchemy as sa
from _helpers import has_content_tables, replace_default_texts
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0011_practice_location"
down_revision: str | None = "0010_email_login"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DIRECTIONS_KEY = "practice.directions"

# key -> (old default, new default)
CHANGES: dict[str, tuple[str, str]] = {
    DIRECTIONS_KEY: (
        "Zentral in der Berner Altstadt gelegen, ca. 8 Gehminuten vom Hauptbahnhof Bern entfernt. Tram 6, 7, 8 oder 9 bis Haltestelle Zytglogge. Parkmöglichkeiten im Parkhaus Rathaus (3 Min. Fussweg).",
        "**Anreise mit dem ÖV ab Bahnhof Biel**\nDie Anreise vom Hauptbahnhof Biel/Bienne dauert nur ca. 5 bis 7 Minuten.\n\n- **Bus nehmen:** Am Bahnhofplatz Biel in den Bus (Linie 1, 5, 6 oder 8) Richtung Innenstadt / Altstadt einsteigen.\n- **Aussteigen:** An der Haltestelle Biel/Bienne, Altstadt (Vieille Ville) oder Zentralplatz aussteigen.\n- **Fussweg (ca. 2 Minuten):** Von der Haltestelle sind es nur wenige Schritte in die Rüschlistrasse 9.\n\n*Alternativ ist die Praxis vom Bahnhof aus auch zu Fuss in ca. 10 bis 12 Minuten bequem erreichbar.*",
    ),
    "practice.accessibility": (
        "Die Praxisräume befinden sich im 1. Stock eines historischen Altstadthauses. Ein rollstuhlgängiger Lift und ein barrierefreier Zugang sind vorhanden.",
        "",
    ),
}

_BLOCKS = sa.table(
    "content_blocks", sa.column("key", sa.String), sa.column("block_type", sa.String)
)


def _set_directions_type(block_type: str) -> None:
    bind = op.get_bind()
    if has_content_tables(bind):
        bind.execute(
            sa.update(_BLOCKS).where(_BLOCKS.c.key == DIRECTIONS_KEY).values(block_type=block_type)
        )


def upgrade() -> None:
    _set_directions_type("rich_text")
    replace_default_texts(op.get_bind(), CHANGES, "Anreise Biel (formatierbar)")


def downgrade() -> None:
    # Texts stay restorable via the admin version history; only the block type is reverted.
    _set_directions_type("textarea")
