"""Contact form protection: captcha replay guard, confirmation throttling, rate-limit index.

Revision ID: 0006_contact_protection
Revises: 0005_admin_security
Create Date: 2026-10-04 00:05:00 UTC

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0006_contact_protection"
down_revision: str | None = "0005_admin_security"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "used_captcha_challenges",
        sa.Column("challenge_id", sa.String(length=128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("challenge_id"),
    )
    op.add_column("contact_messages", sa.Column("email_hash", sa.String(64), nullable=True))
    op.add_column(
        "contact_messages",
        sa.Column("confirmation_sent", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index(
        op.f("ix_contact_messages_email_hash"), "contact_messages", ["email_hash"], unique=False
    )
    op.create_index(
        "ix_contact_messages_ip_created",
        "contact_messages",
        ["ip_address", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_contact_messages_ip_created", table_name="contact_messages")
    op.drop_index(op.f("ix_contact_messages_email_hash"), table_name="contact_messages")
    op.drop_column("contact_messages", "confirmation_sent")
    op.drop_column("contact_messages", "email_hash")
    op.drop_table("used_captcha_challenges")
