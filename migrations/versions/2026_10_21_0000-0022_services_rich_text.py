"""Services boxes become formatted rich-text blocks.

Data-only migration (see TDR-0003). ``services.empty_text`` and ``services.insurance_text``
switch to the block type ``rich_text`` (bold, italic, underline, bullet lists). Existing texts
stay untouched; lines starting with ``- `` are now rendered as bullet lists.

Revision ID: 0022_services_rich_text
Revises: 0021_deletion_log
Create Date: 2026-10-21 00:00:00 UTC

"""

from collections.abc import Sequence

import sqlalchemy as sa
from _helpers import has_content_tables
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0022_services_rich_text"
down_revision: str | None = "0021_deletion_log"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

KEYS = ("services.empty_text", "services.insurance_text")

_BLOCKS = sa.table(
    "content_blocks", sa.column("key", sa.String), sa.column("block_type", sa.String)
)


def _set_type(block_type: str) -> None:
    bind = op.get_bind()
    if has_content_tables(bind):
        bind.execute(
            sa.update(_BLOCKS).where(_BLOCKS.c.key.in_(KEYS)).values(block_type=block_type)
        )


def upgrade() -> None:
    _set_type("rich_text")


def downgrade() -> None:
    _set_type("textarea")
