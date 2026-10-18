"""Deletion log: IDs of deleted messages, re-applied after a restore (ADR-0006, TDR-0013).

Revision ID: 0021_deletion_log
Revises: 0020_privacy_statement
Create Date: 2026-10-18 00:04:00 UTC

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0021_deletion_log"
down_revision: str | None = "0020_privacy_statement"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "deletion_log",
        sa.Column("message_id", sa.UUID(), nullable=False),
        sa.Column(
            "reason",
            sa.Enum("MESSAGE", "PERSON", name="deletionreason", native_enum=False, length=20),
            nullable=False,
        ),
        sa.Column("email_hash", sa.String(length=64), nullable=True),
        sa.Column("actor_id", sa.UUID(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_deletion_log_message_id"), "deletion_log", ["message_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_deletion_log_message_id"), table_name="deletion_log")
    op.drop_table("deletion_log")
