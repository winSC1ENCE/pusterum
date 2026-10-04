"""Switch the practice e-mail to the final domain pusterum.be (.be = Bern).

Data-only migration (see TDR-0003). Replaces the interim address ``kontakt@pusterum.ch``
(introduced by revision 0001) in the ``practice.email`` content block and in
``practice_info.email`` when it is still exactly that value. Manually set addresses stay
untouched. The content change is written as a new version.

Revision ID: 0004_domain_pusterum_be
Revises: 0003_hero_text_optional
Create Date: 2026-10-04 00:03:00 UTC

"""

from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import uuid4

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004_domain_pusterum_be"
down_revision: str | None = "0003_hero_text_optional"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

KEY = "practice.email"
OLD_EMAIL = "kontakt@pusterum.ch"
NEW_EMAIL = "kontakt@pusterum.be"


def upgrade() -> None:
    bind = op.get_bind()
    existing = set(sa.inspect(bind).get_table_names())

    if "practice_info" in existing:
        practice = sa.table("practice_info", sa.column("email", sa.String))
        bind.execute(
            sa.update(practice).where(practice.c.email == OLD_EMAIL).values(email=NEW_EMAIL)
        )

    if not {"content_blocks", "content_block_versions"} <= existing:
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
    if row is None or row.current_content != OLD_EMAIL:
        return

    now = datetime.now(UTC)
    next_version = row.current_version_number + 1
    bind.execute(
        sa.insert(versions).values(
            id=uuid4(),
            block_key=KEY,
            version_number=next_version,
            content=NEW_EMAIL,
            author_name="System Migration",
            change_summary="Domain pusterum.be",
            created_at=now,
        )
    )
    bind.execute(
        sa.update(blocks)
        .where(blocks.c.key == KEY)
        .values(current_version_number=next_version, current_content=NEW_EMAIL, updated_at=now)
    )


def downgrade() -> None:
    # Intentionally a no-op: the previous address remains restorable via the version history.
    pass
