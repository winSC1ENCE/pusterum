# ruff: noqa: E501  (frozen default-text snapshots)
"""Shorten the hero text to a concise PUSTERUM claim.

Data-only migration (see TDR-0003). Replaces ``hero.text`` when it still contains the
former «Hā Ola» wording (even if manually extended) or exactly matches the long default
introduced by revision 0001. Any other manually edited text stays untouched. The change is
written as a new immutable version, so the previous text remains restorable.

Revision ID: 0002_hero_text_short
Revises: 0001_pusterum_rebranding
Create Date: 2026-10-04 00:01:00 UTC

"""

from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import uuid4

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002_hero_text_short"
down_revision: str | None = "0001_pusterum_rebranding"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

KEY = "hero.text"
LEGACY_MARKER = "Hā"
PREVIOUS_DEFAULT = "Der Atem begleitet uns durch unser ganzes Leben. Er ist die Verbindung zwischen Körper und Psyche: Er reagiert auf das, was uns beschäftigt, auf unsere Gefühle, auf Anspannung, Bewegung und Körperhaltung. Als einzige autonome Körperfunktion lässt sich der Atem jedoch willentlich aktiv beeinflussen. In der Praxis PUSTERUM nutzen wir diese Verbindung als direkten Zugang, um Anspannung loszulassen, zur Ruhe zu kommen und neue Kraft zu schöpfen."
NEW_CONTENT = "Ein Raum zum Durchatmen – für mehr Ruhe, Körpergefühl und innere Balance."


def upgrade() -> None:
    bind = op.get_bind()
    if not {"content_blocks", "content_block_versions"} <= set(sa.inspect(bind).get_table_names()):
        return

    blocks = sa.table(
        "content_blocks",
        sa.column("key", sa.String),
        sa.column("current_version_number", sa.Integer),
        sa.column("current_content", sa.Text),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    versions = sa.table(
        "content_block_versions",
        sa.column("id", sa.Uuid),
        sa.column("block_key", sa.String),
        sa.column("version_number", sa.Integer),
        sa.column("content", sa.Text),
        sa.column("author_name", sa.String),
        sa.column("change_summary", sa.String),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )
    row = bind.execute(
        sa.select(blocks.c.current_version_number, blocks.c.current_content).where(
            blocks.c.key == KEY
        )
    ).first()
    if row is None:
        return
    version_number, current = row
    if LEGACY_MARKER not in current and current != PREVIOUS_DEFAULT:
        return

    now = datetime.now(UTC)
    next_version = version_number + 1
    bind.execute(
        sa.insert(versions).values(
            id=uuid4(),
            block_key=KEY,
            version_number=next_version,
            content=NEW_CONTENT,
            author_name="System Migration",
            change_summary="Hero-Text gekürzt",
            created_at=now,
        )
    )
    bind.execute(
        sa.update(blocks)
        .where(blocks.c.key == KEY)
        .values(current_version_number=next_version, current_content=NEW_CONTENT, updated_at=now)
    )


def downgrade() -> None:
    # Intentionally a no-op: previous texts remain restorable via the version history.
    pass
