"""Training entries and practice description become rich text with links.

Data-only migration (see TDR-0003). ``about.credential_*`` and ``practice.description`` switch
to the block type ``rich_text`` (links ``[Text](https://…)``, bold, italic, lists). The names of
the training institutes and of the shared practice are linked in the *current* texts, also when
the practice owner has edited them; the wording stays untouched and each change is a new
version (restorable from the admin version history).

Revision ID: 0025_links_about
Revises: 0024_services_intro
Create Date: 2026-10-30 00:00:00 UTC

"""

from collections.abc import Sequence

import sqlalchemy as sa
from _helpers import has_content_tables, link_phrases
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0025_links_about"
down_revision: str | None = "0024_services_intro"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# The order of the training entries is up to the practice owner: every entry gets every rule.
CREDENTIAL_KEYS = tuple(f"about.credential_{n}" for n in range(1, 11))
DESCRIPTION_KEY = "practice.description"

CREDENTIAL_LINKS: tuple[tuple[tuple[str, ...], str], ...] = (
    (
        (
            "Institut für Körperzentrierte Psychotherapie IKP",
            "IKP Institut für Körperzentrierte Psychotherapie",
        ),
        "https://www.ikp-therapien.com/",
    ),
    (("Atemfachverband AFS",), "https://www.atem-schweiz.ch/"),
    (("International Sivananda Yoga Vedanta Centre",), "https://sivananda.org.in/"),
    (("Klubschule Migros",), "https://www.klubschule.ch/"),
)
DESCRIPTION_LINKS: tuple[tuple[tuple[str, ...], str], ...] = (
    (("LaFontaine", "La Fontaine"), "https://physio-lafontaine.ch/"),
)

CHANGES = {
    **dict.fromkeys(CREDENTIAL_KEYS, CREDENTIAL_LINKS),
    DESCRIPTION_KEY: DESCRIPTION_LINKS,
}

_BLOCKS = sa.table(
    "content_blocks", sa.column("key", sa.String), sa.column("block_type", sa.String)
)


def _set_types(credential_type: str, description_type: str) -> None:
    bind = op.get_bind()
    if not has_content_tables(bind):
        return
    bind.execute(
        sa.update(_BLOCKS)
        .where(_BLOCKS.c.key.in_(CREDENTIAL_KEYS))
        .values(block_type=credential_type)
    )
    bind.execute(
        sa.update(_BLOCKS)
        .where(_BLOCKS.c.key == DESCRIPTION_KEY)
        .values(block_type=description_type)
    )


def upgrade() -> None:
    _set_types("rich_text", "rich_text")
    link_phrases(op.get_bind(), CHANGES, "Links zu Ausbildungsstätten und Praxis ergänzt")


def downgrade() -> None:
    # Links stay in the text (and in the version history); only the editor type is reverted.
    _set_types("text", "textarea")
