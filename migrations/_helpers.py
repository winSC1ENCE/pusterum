"""Shared helpers for data migrations of content blocks (ADR-0002 versioning).

Data migrations only replace blocks that still hold the *previous default* – texts edited
by the practice owner are never overwritten. Every replacement becomes a new version, so
the previous text stays restorable from the admin version history.
"""

from collections.abc import Mapping, Sequence
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


def _write_version(
    bind: Connection, key: str, version: int, content: str, *, summary: str, now: datetime
) -> None:
    """Store ``content`` as version ``version`` of ``key`` and make it the current text."""
    bind.execute(
        sa.insert(_VERSIONS).values(
            id=uuid4(),
            block_key=key,
            version_number=version,
            content=content,
            author_name="System Migration",
            change_summary=summary,
            created_at=now,
        )
    )
    bind.execute(
        sa.update(_BLOCKS)
        .where(_BLOCKS.c.key == key)
        .values(current_version_number=version, current_content=content, updated_at=now)
    )


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
        _write_version(bind, key, version + 1, new, summary=summary, now=now)
        replaced += 1
    return replaced


def add_links(text: str, links: Sequence[tuple[Sequence[str], str]]) -> str:
    """Turn the first found phrase of each ``(phrases, url)`` into ``[phrase](url)``.

    Phrases are tried in order (first hit wins). A link whose URL already appears in the text
    is skipped, so running the migration twice or on hand-made links changes nothing.
    """
    for phrases, url in links:
        if url in text:
            continue
        for phrase in phrases:
            if phrase in text:
                text = text.replace(phrase, f"[{phrase}]({url})", 1)
                break
    return text


def link_phrases(
    bind: Connection, changes: Mapping[str, Sequence[tuple[Sequence[str], str]]], summary: str
) -> int:
    """Apply :func:`add_links` to the *current* text of each key (also edited texts).

    Only phrases are wrapped, the wording stays untouched. Every change becomes a new version,
    so the practice owner can restore the previous text. Returns the number of changed blocks.
    """
    if not has_content_tables(bind):
        return 0
    now = datetime.now(UTC)
    changed = 0
    rows = bind.execute(
        sa.select(_BLOCKS.c.key, _BLOCKS.c.current_version_number, _BLOCKS.c.current_content).where(
            _BLOCKS.c.key.in_(list(changes))
        )
    ).all()
    for key, version, current in rows:
        new = add_links(current or "", changes[key])
        if new == (current or ""):
            continue
        _write_version(bind, key, version + 1, new, summary=summary, now=now)
        changed += 1
    return changed
