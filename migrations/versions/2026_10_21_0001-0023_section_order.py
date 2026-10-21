"""Reorderable start-page sections: ``theme_configs.section_order``.

Comma separated ``PageSection`` values; the default is the order requested by the practice
(competencies, services, kids, about, quotes, practice). Hero and contact stay fixed.

Revision ID: 0023_section_order
Revises: 0022_services_rich_text
Create Date: 2026-10-21 00:01:00 UTC

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0023_section_order"
down_revision: str | None = "0022_services_rich_text"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Frozen snapshot of the default (do not import from the application)
DEFAULT_ORDER = "competencies,services,kids,about,quotes,practice"


def upgrade() -> None:
    # Existing theme rows get the default order so the NOT NULL column can be added.
    op.add_column(
        "theme_configs",
        sa.Column(
            "section_order", sa.String(length=255), nullable=False, server_default=DEFAULT_ORDER
        ),
    )


def downgrade() -> None:
    op.drop_column("theme_configs", "section_order")
