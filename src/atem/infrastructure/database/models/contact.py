"""SQLAlchemy ORM Models for Contact Messages."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from atem.domain.models.contact import MessageStatus
from atem.infrastructure.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ContactMessageModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Database table for contact messages."""

    __tablename__ = "contact_messages"
    __table_args__ = (Index("ix_contact_messages_ip_created", "ip_address", "created_at"),)

    sender_name: Mapped[str] = mapped_column(String(120), nullable=False)
    sender_email: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    # message, sender_phone and notes hold Fernet ciphertext (TDR-0012), hence Text.
    sender_phone: Mapped[str | None] = mapped_column(Text, nullable=True)
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
    email_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    confirmation_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class UsedCaptchaChallengeModel(Base):
    """Solved captcha challenges – every challenge is accepted only once (replay guard)."""

    __tablename__ = "used_captcha_challenges"

    challenge_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
