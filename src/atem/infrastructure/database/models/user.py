"""SQLAlchemy ORM Models for Users and Authentication."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from atem.domain.models.user import UserRole
from atem.infrastructure.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class UserModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Database table for system users."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(150), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, native_enum=False, length=20),
        default=UserRole.ADMIN,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    totp_secret_encrypted: Mapped[str | None] = mapped_column(String(255), nullable=True)
    totp_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    totp_last_used_step: Mapped[int | None] = mapped_column(Integer, nullable=True)
    session_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    failed_login_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    password_changed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RecoveryCodeModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """One-time recovery codes for the second factor (stored as Argon2 hashes)."""

    __tablename__ = "recovery_codes"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    code_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class LoginAttemptModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Login attempts per client IP – shared rate limiting across all web workers."""

    __tablename__ = "login_attempts"

    ip_address: Mapped[str] = mapped_column(String(45), index=True, nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    # Trusted-device id (device cookie) – per-device failure limit instead of account lockout
    device_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
