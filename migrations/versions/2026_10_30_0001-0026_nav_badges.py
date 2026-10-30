"""Section badges become short defaults: the navigation now shows them as menu labels.

Data-only migration (see TDR-0003). Only blocks that still hold the previous default are
replaced; badges edited by the practice owner stay as they are.

Revision ID: 0026_nav_badges
Revises: 0025_links_about
Create Date: 2026-10-30 00:01:00 UTC

"""

from collections.abc import Sequence

from _helpers import replace_default_texts
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0026_nav_badges"
down_revision: str | None = "0025_links_about"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CHANGES = {
    "competencies.badge": ("Methode & Wirkung", "Methode"),
    "services.badge": ("Transparente Tarife & Behandlungsablauf", "Angebot"),
    "practice.setting": ("Gemeinschaftspraxis • Raum für Ruhe & Ankommen", "Praxis"),
}


def upgrade() -> None:
    replace_default_texts(op.get_bind(), CHANGES, "Kurze Abschnittsnamen für das Menü")


def downgrade() -> None:
    replace_default_texts(
        op.get_bind(),
        {key: (new, old) for key, (old, new) in CHANGES.items()},
        "Abschnittsnamen zurückgesetzt",
    )
