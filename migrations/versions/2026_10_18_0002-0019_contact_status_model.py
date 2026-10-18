"""Contact status model with history (TDR-0010).

* Status codes: ``READ`` becomes ``IN_PROGRESS``, ``ARCHIVED`` becomes ``DONE``; new ``SPAM``.
* ``closed_at``: when a message was closed (done or spam), basis of the retention periods.
* ``contact_message_events``: who changed the status or the notes and when (no content).
* Index (``status``, ``created_at``) for the filtered list replaces the index on ``status``.

Revision ID: 0019_contact_status_model
Revises: 0018_encrypt_contact_text
Create Date: 2026-10-18 00:02:00 UTC

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0019_contact_status_model"
down_revision: str | None = "0018_encrypt_contact_text"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_MESSAGES = sa.table(
    "contact_messages",
    sa.column("status", sa.String),
    sa.column("closed_at", sa.DateTime(timezone=True)),
    sa.column("updated_at", sa.DateTime(timezone=True)),
)


def _rename_status(old: str, new: str, **values: object) -> None:
    op.execute(sa.update(_MESSAGES).where(_MESSAGES.c.status == old).values(status=new, **values))


def upgrade() -> None:
    op.add_column(
        "contact_messages", sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True)
    )
    _rename_status("READ", "IN_PROGRESS")
    _rename_status("ARCHIVED", "DONE", closed_at=_MESSAGES.c.updated_at)

    op.drop_index("ix_contact_messages_status", table_name="contact_messages")
    op.create_index(
        "ix_contact_messages_status_created", "contact_messages", ["status", "created_at"]
    )

    op.create_table(
        "contact_message_events",
        sa.Column("message_id", sa.UUID(), nullable=False),
        sa.Column(
            "action",
            sa.Enum("STATUS", "NOTES", name="eventaction", native_enum=False, length=20),
            nullable=False,
        ),
        sa.Column("old_value", sa.String(length=20), nullable=True),
        sa.Column("new_value", sa.String(length=20), nullable=True),
        sa.Column("actor_id", sa.UUID(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["message_id"], ["contact_messages.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_contact_message_events_message_id"), "contact_message_events", ["message_id"]
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_contact_message_events_message_id"), table_name="contact_message_events")
    op.drop_table("contact_message_events")

    op.drop_index("ix_contact_messages_status_created", table_name="contact_messages")
    op.create_index("ix_contact_messages_status", "contact_messages", ["status"])

    _rename_status("IN_PROGRESS", "READ")
    _rename_status("DONE", "ARCHIVED")
    _rename_status("SPAM", "ARCHIVED")
    op.drop_column("contact_messages", "closed_at")
