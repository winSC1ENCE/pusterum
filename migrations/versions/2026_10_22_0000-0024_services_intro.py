"""Offerings section: ``services.empty_text`` becomes the permanent intro ``services.intro``.

Data-only migration (see TDR-0003). The placeholder shown while no offerings exist was used
for the practice's description of the method («Arbeitsweise»). It is renamed to
``services.intro`` (always shown above the offering cards) with its full version history;
the empty-offerings placeholder is now a fixed admin hint instead of an editable block.

Revision ID: 0024_services_intro
Revises: 0023_section_order
Create Date: 2026-10-22 00:00:00 UTC

"""

from collections.abc import Sequence

import sqlalchemy as sa
from _helpers import has_content_tables
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0024_services_intro"
down_revision: str | None = "0023_section_order"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OLD_KEY = "services.empty_text"
NEW_KEY = "services.intro"

_BLOCKS = sa.table(
    "content_blocks",
    sa.column("key", sa.String),
    sa.column("section", sa.String),
    sa.column("block_type", sa.String),
    sa.column("current_version_number", sa.Integer),
    sa.column("current_content", sa.Text),
    sa.column("updated_at", sa.DateTime(timezone=True)),
)
_VERSIONS = sa.table("content_block_versions", sa.column("block_key", sa.String))


def _rename(old: str, new: str) -> None:
    """Move a block and its versions to a new key (the versions reference the key)."""
    bind = op.get_bind()
    if not has_content_tables(bind):
        return
    source = bind.execute(sa.select(_BLOCKS).where(_BLOCKS.c.key == old)).mappings().first()
    if source is None:
        return
    # A row under the new key can only be an untouched seed from an app start before this
    # migration (e.g. local development); the renamed block replaces it.
    bind.execute(sa.delete(_VERSIONS).where(_VERSIONS.c.block_key == new))
    bind.execute(sa.delete(_BLOCKS).where(_BLOCKS.c.key == new))
    bind.execute(sa.insert(_BLOCKS).values({**source, "key": new}))
    bind.execute(sa.update(_VERSIONS).where(_VERSIONS.c.block_key == old).values(block_key=new))
    bind.execute(sa.delete(_BLOCKS).where(_BLOCKS.c.key == old))


def upgrade() -> None:
    _rename(OLD_KEY, NEW_KEY)


def downgrade() -> None:
    _rename(NEW_KEY, OLD_KEY)
