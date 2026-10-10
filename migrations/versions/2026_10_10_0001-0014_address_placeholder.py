"""Address default: fictitious placeholder instead of a real street in Bern.

Data-only migration (see TDR-0003). House number 0 does not exist, so the placeholder
cannot point to a real building. Replaces only the untouched default text
(see migrations/_helpers.py).

Revision ID: 0014_address_placeholder
Revises: 0013_contact_placeholders
Create Date: 2026-10-10 00:01:00 UTC

"""

from collections.abc import Sequence

from _helpers import replace_default_texts
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0014_address_placeholder"
down_revision: str | None = "0013_contact_placeholders"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# key -> (old default, new default)
CHANGES: dict[str, tuple[str, str]] = {
    "practice.address": ("Kramgasse 42, 3011 Bern", "Beispielweg 0, 3000 Bern"),
}


def upgrade() -> None:
    replace_default_texts(op.get_bind(), CHANGES, "Adresse (Platzhalter)")


def downgrade() -> None:
    replace_default_texts(
        op.get_bind(),
        {key: (new, old) for key, (old, new) in CHANGES.items()},
        "Adresse zurückgesetzt",
    )
