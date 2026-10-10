"""Theme setting: opacity of the «Atmende Blume» background photos (Design Studio slider).

Revision ID: 0012_kids_photo_opacity
Revises: 0011_practice_location
Create Date: 2026-10-05 00:01:00 UTC

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0012_kids_photo_opacity"
down_revision: str | None = "0011_practice_location"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Existing theme rows get the default (30 %) so the NOT NULL column can be added.
    op.add_column(
        "theme_configs",
        sa.Column("kids_photo_opacity", sa.Integer(), nullable=False, server_default="30"),
    )


def downgrade() -> None:
    op.drop_column("theme_configs", "kids_photo_opacity")
