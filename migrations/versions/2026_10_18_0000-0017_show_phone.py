"""Theme setting: show the practice phone number on the public site (Design Studio switch).

Revision ID: 0017_show_phone
Revises: 0016_header_opacity
Create Date: 2026-10-18 00:00:00 UTC

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0017_show_phone"
down_revision: str | None = "0016_header_opacity"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Existing theme rows keep the phone visible (unchanged public site).
    op.add_column(
        "theme_configs",
        sa.Column("show_phone", sa.Boolean(), nullable=False, server_default=sa.true()),
    )


def downgrade() -> None:
    op.drop_column("theme_configs", "show_phone")
