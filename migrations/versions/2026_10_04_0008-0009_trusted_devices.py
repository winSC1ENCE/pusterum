"""Trusted devices: per-device login failure counting (lockout denial-of-service protection).

Revision ID: 0009_trusted_devices
Revises: 0008_cleanup_profile_tables
Create Date: 2026-10-04 00:08:00 UTC

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0009_trusted_devices"
down_revision: str | None = "0008_cleanup_profile_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add the device id to login attempts."""
    op.add_column("login_attempts", sa.Column("device_id", sa.String(length=64), nullable=True))
    op.create_index(
        op.f("ix_login_attempts_device_id"), "login_attempts", ["device_id"], unique=False
    )


def downgrade() -> None:
    """Remove the device id from login attempts."""
    op.drop_index(op.f("ix_login_attempts_device_id"), table_name="login_attempts")
    op.drop_column("login_attempts", "device_id")
