"""Theme setting: background opacity of the sticky header (Design Studio slider, glass effect).

Revision ID: 0016_header_opacity
Revises: 0015_privacy_font_size
Create Date: 2026-10-15 00:00:00 UTC

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0016_header_opacity"
down_revision: str | None = "0015_privacy_font_size"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Existing theme rows get the default (60 %) so the NOT NULL column can be added.
    op.add_column(
        "theme_configs",
        sa.Column("header_opacity", sa.Integer(), nullable=False, server_default="60"),
    )


def downgrade() -> None:
    op.drop_column("theme_configs", "header_opacity")
