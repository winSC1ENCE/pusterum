"""Contact defaults: public address info@pusterum.be and a fictitious phone placeholder.

Data-only migration (see TDR-0003). The former placeholder number could exist in the Bern
area; the new one has a subscriber part starting with 0, which no Swiss number can have.
Replaces only untouched default texts (see migrations/_helpers.py).

Revision ID: 0013_contact_placeholders
Revises: 0012_kids_photo_opacity
Create Date: 2026-10-10 00:00:00 UTC

"""

from collections.abc import Sequence

from _helpers import replace_default_texts
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0013_contact_placeholders"
down_revision: str | None = "0012_kids_photo_opacity"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# key -> (old default, new default)
CHANGES: dict[str, tuple[str, str]] = {
    "practice.email": ("kontakt@pusterum.be", "info@pusterum.be"),
    "practice.phone": ("+41 31 310 00 00", "+41 31 000 00 00"),
}


def upgrade() -> None:
    replace_default_texts(op.get_bind(), CHANGES, "Kontaktangaben (Platzhalter)")


def downgrade() -> None:
    replace_default_texts(
        op.get_bind(),
        {key: (new, old) for key, (old, new) in CHANGES.items()},
        "Kontaktangaben zurückgesetzt",
    )
