"""Shared helpers for data migrations of content blocks (ADR-0002 versioning).

Data migrations only replace blocks that still hold the *previous default* – texts edited
by the practice owner are never overwritten. Every replacement becomes a new version, so
the previous text stays restorable from the admin version history.
"""

from collections.abc import Mapping
from datetime import UTC, datetime
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy.engine import Connection

_BLOCKS = sa.table(
    "content_blocks",
    sa.column("key", sa.String),
    sa.column("current_version_number", sa.Integer),
    sa.column("current_content", sa.Text),
    sa.column("updated_at", sa.DateTime(timezone=True)),
)
_VERSIONS = sa.table(
    "content_block_versions",
    sa.column("id", sa.Uuid),
    sa.column("block_key", sa.String),
    sa.column("version_number", sa.Integer),
    sa.column("content", sa.Text),
    sa.column("author_name", sa.String),
    sa.column("change_summary", sa.String),
    sa.column("created_at", sa.DateTime(timezone=True)),
)


def has_content_tables(bind: Connection) -> bool:
    """True once the content tables exist (fresh databases are seeded at startup instead)."""
    return {"content_blocks", "content_block_versions"} <= set(sa.inspect(bind).get_table_names())


def replace_default_texts(
    bind: Connection, changes: Mapping[str, tuple[str, str]], summary: str
) -> int:
    """Apply ``{key: (old_default, new_default)}`` to untouched blocks; return the count."""
    if not has_content_tables(bind):
        return 0
    now = datetime.now(UTC)
    replaced = 0
    rows = bind.execute(
        sa.select(_BLOCKS.c.key, _BLOCKS.c.current_version_number, _BLOCKS.c.current_content).where(
            _BLOCKS.c.key.in_(list(changes))
        )
    ).all()
    for key, version, current in rows:
        old, new = changes[key]
        if current != old:
            continue
        bind.execute(
            sa.insert(_VERSIONS).values(
                id=uuid4(),
                block_key=key,
                version_number=version + 1,
                content=new,
                author_name="System Migration",
                change_summary=summary,
                created_at=now,
            )
        )
        bind.execute(
            sa.update(_BLOCKS)
            .where(_BLOCKS.c.key == key)
            .values(current_version_number=version + 1, current_content=new, updated_at=now)
        )
        replaced += 1
    return replaced
