"""Admin security: 2FA (TOTP), recovery codes, lockout, session revocation, login attempts.

Revision ID: 0005_admin_security
Revises: 0004_domain_pusterum_be
Create Date: 2026-10-04 00:04:00 UTC

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0005_admin_security"
down_revision: str | None = "0004_domain_pusterum_be"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "login_attempts",
        sa.Column("ip_address", sa.String(length=45), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_login_attempts_ip_address"), "login_attempts", ["ip_address"], unique=False
    )
    op.create_table(
        "recovery_codes",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("code_hash", sa.String(length=255), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_recovery_codes_user_id"), "recovery_codes", ["user_id"], unique=False)

    # Existing rows get server defaults so the NOT NULL columns can be added.
    op.add_column("users", sa.Column("totp_secret_encrypted", sa.String(255), nullable=True))
    op.add_column(
        "users", sa.Column("totp_enabled", sa.Boolean(), nullable=False, server_default=sa.false())
    )
    op.add_column("users", sa.Column("totp_last_used_step", sa.Integer(), nullable=True))
    op.add_column(
        "users", sa.Column("session_version", sa.Integer(), nullable=False, server_default="1")
    )
    op.add_column(
        "users", sa.Column("failed_login_count", sa.Integer(), nullable=False, server_default="0")
    )
    op.add_column("users", sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "users",
        sa.Column("must_change_password", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "users", sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column("users", sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    for column in (
        "last_login_at",
        "password_changed_at",
        "must_change_password",
        "locked_until",
        "failed_login_count",
        "session_version",
        "totp_last_used_step",
        "totp_enabled",
        "totp_secret_encrypted",
    ):
        op.drop_column("users", column)
    op.drop_index(op.f("ix_recovery_codes_user_id"), table_name="recovery_codes")
    op.drop_table("recovery_codes")
    op.drop_index(op.f("ix_login_attempts_ip_address"), table_name="login_attempts")
    op.drop_table("login_attempts")
