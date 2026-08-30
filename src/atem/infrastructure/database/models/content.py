"""SQLAlchemy ORM Models for Site Content and Version Audit Logs."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from atem.infrastructure.database.base import Base


class ContentBlockModel(Base):
    """Database table for editable website content elements."""

    __tablename__ = "content_blocks"

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    section: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    block_type: Mapped[str] = mapped_column(String(32), nullable=False)
    current_version_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    current_content: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


class ContentBlockVersionModel(Base):
    """Database table for immutable content version snapshots (Audit Trail)."""

    __tablename__ = "content_block_versions"
    __table_args__ = (
        UniqueConstraint("block_key", "version_number", name="uq_block_key_version_number"),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        nullable=False,
    )
    block_key: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("content_blocks.key", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    author_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    author_name: Mapped[str] = mapped_column(String(150), default="Admin", nullable=False)
    change_summary: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
