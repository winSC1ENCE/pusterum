"""SQLAlchemy ORM Models for Contact Messages."""

from sqlalchemy import Enum as SAEnum
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from atem.domain.models.contact import MessageStatus
from atem.infrastructure.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ContactMessageModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Database table for contact messages."""

    __tablename__ = "contact_messages"

    sender_name: Mapped[str] = mapped_column(String(120), nullable=False)
    sender_email: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    sender_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[MessageStatus] = mapped_column(
        SAEnum(MessageStatus, native_enum=False, length=20),
        default=MessageStatus.NEW,
        nullable=False,
        index=True,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
