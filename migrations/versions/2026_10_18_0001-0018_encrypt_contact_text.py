"""Encrypt contact free text at rest: message, sender_phone and notes (TDR-0012).

The key is derived from SECRET_KEY with the same purpose as at runtime
(``bootstrap.build_contact_cipher``), so the migration needs the production environment.
``sender_phone`` becomes ``Text`` because the ciphertext no longer fits into 50 characters.

Revision ID: 0018_encrypt_contact_text
Revises: 0017_show_phone
Create Date: 2026-10-18 00:01:00 UTC

"""

from collections.abc import Callable, Sequence

import sqlalchemy as sa
from alembic import op

from atem.infrastructure.config.settings import get_settings
from atem.infrastructure.security.fernet_secret_cipher import FernetSecretCipher

# revision identifiers, used by Alembic.
revision: str = "0018_encrypt_contact_text"
down_revision: str | None = "0017_show_phone"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_FIELDS = ("message", "sender_phone", "notes")
_MESSAGES = sa.table(
    "contact_messages",
    sa.column("id", sa.Uuid),
    *(sa.column(name, sa.Text) for name in _FIELDS),
)


def _cipher() -> FernetSecretCipher:
    # Frozen copy of the runtime key purpose; changing it there needs a re-encryption migration.
    return FernetSecretCipher(get_settings().derive_key(b"atem-contact-cipher"))


def _convert_all(convert: Callable[[str], str]) -> None:
    connection = op.get_bind()
    rows = connection.execute(sa.select(_MESSAGES)).mappings().all()
    for row in rows:
        values = {name: convert(row[name]) for name in _FIELDS if row[name] is not None}
        if values:
            connection.execute(
                sa.update(_MESSAGES).where(_MESSAGES.c.id == row["id"]).values(**values)
            )


def upgrade() -> None:
    op.alter_column(
        "contact_messages", "sender_phone", type_=sa.Text(), existing_type=sa.String(50)
    )
    _convert_all(_cipher().encrypt)


def downgrade() -> None:
    _convert_all(_cipher().decrypt)
    op.alter_column(
        "contact_messages", "sender_phone", type_=sa.String(50), existing_type=sa.Text()
    )
