"""Remove unused profile tables and theme columns (dead code cleanup).

Therapist profile, competencies and practice info are fully replaced by editable content
blocks; the «motif» theme settings were never rendered. Service offerings stay.

Revision ID: 0008_cleanup_profile_tables
Revises: 0007_privacy_policy
Create Date: 2026-10-04 00:07:00 UTC

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0008_cleanup_profile_tables"
down_revision: str | None = "0007_privacy_policy"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> list[sa.Column[object]]:
    return [
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def upgrade() -> None:
    op.drop_table("therapist_profiles")
    op.drop_table("competencies")
    op.drop_table("practice_info")
    op.drop_column("theme_configs", "motif_enabled")
    op.drop_column("theme_configs", "motif_animation_speed")


def downgrade() -> None:
    """Recreate the (empty) tables and columns as they were in the baseline schema."""
    op.add_column(
        "theme_configs",
        sa.Column("motif_animation_speed", sa.String(20), nullable=False, server_default="normal"),
    )
    op.add_column(
        "theme_configs",
        sa.Column("motif_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_table(
        "practice_info",
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("street", sa.String(200), nullable=False),
        sa.Column("zip_code", sa.String(10), nullable=False),
        sa.Column("city", sa.String(100), nullable=False),
        sa.Column("canton", sa.String(10), nullable=False),
        sa.Column("country", sa.String(50), nullable=False),
        sa.Column("phone", sa.String(50), nullable=False),
        sa.Column("email", sa.String(150), nullable=False),
        sa.Column("directions_info", sa.Text(), nullable=False),
        sa.Column("accessibility_info", sa.String(200), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        *_timestamps(),
    )
    op.create_table(
        "competencies",
        sa.Column("title", sa.String(150), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("icon_name", sa.String(50), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        *_timestamps(),
    )
    op.create_table(
        "therapist_profiles",
        sa.Column("full_name", sa.String(150), nullable=False),
        sa.Column("title", sa.String(150), nullable=False),
        sa.Column("diploma", sa.String(250), nullable=False),
        sa.Column("tagline", sa.String(300), nullable=False),
        sa.Column("bio", sa.Text(), nullable=False),
        sa.Column("quote", sa.String(500), nullable=False),
        sa.Column("profile_image_url", sa.String(500), nullable=False),
        sa.Column("booking_external_url", sa.String(500), nullable=True),
        *_timestamps(),
    )
