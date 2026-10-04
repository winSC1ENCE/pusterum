"""E-mail address as the only admin login (no user names).

Existing addresses are normalized (trimmed, lower case) so that the login lookup is
case-insensitive; the ``username`` column is removed.

Revision ID: 0010_email_login
Revises: 0009_trusted_devices
Create Date: 2026-10-04 00:09:00 UTC

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0010_email_login"
down_revision: str | None = "0009_trusted_devices"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Normalize e-mail logins and drop the user name."""
    op.execute(sa.text("UPDATE users SET email = lower(trim(email))"))
    op.drop_index(op.f("ix_users_username"), table_name="users")
    op.drop_column("users", "username")


def downgrade() -> None:
    """Restore the user name column (filled with the e-mail address)."""
    op.add_column("users", sa.Column("username", sa.String(length=100), nullable=True))
    op.execute(sa.text("UPDATE users SET username = left(email, 100)"))
    op.alter_column("users", "username", nullable=False)
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)
