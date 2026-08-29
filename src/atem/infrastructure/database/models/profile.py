"""SQLAlchemy ORM Models for Profile, Competencies, Offerings, and Practice."""

from sqlalchemy import Boolean, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from atem.infrastructure.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class TherapistProfileModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Database table for therapist profile."""

    __tablename__ = "therapist_profiles"

    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    diploma: Mapped[str] = mapped_column(String(250), nullable=False)
    tagline: Mapped[str] = mapped_column(String(300), nullable=False)
    bio: Mapped[str] = mapped_column(Text, nullable=False)
    quote: Mapped[str] = mapped_column(String(500), nullable=False)
    profile_image_url: Mapped[str] = mapped_column(
        String(500),
        default="/static/images/profile.jpg",
    )
    booking_external_url: Mapped[str | None] = mapped_column(String(500), nullable=True)


class CompetencyModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Database table for therapist competencies."""

    __tablename__ = "competencies"

    title: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    icon_name: Mapped[str] = mapped_column(String(50), default="sparkles", nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class ServiceOfferingModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Database table for treatments and service offerings."""

    __tablename__ = "service_offerings"

    title: Mapped[str] = mapped_column(String(150), nullable=False)
    slug: Mapped[str] = mapped_column(String(150), unique=True, index=True, nullable=False)
    subtitle: Mapped[str] = mapped_column(String(250), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    price_chf: Mapped[float] = mapped_column(Float, default=140.0, nullable=False)
    is_health_insurance_recognized: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class PracticeInfoModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Database table for practice location and details."""

    __tablename__ = "practice_info"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    street: Mapped[str] = mapped_column(String(200), nullable=False)
    zip_code: Mapped[str] = mapped_column(String(10), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    canton: Mapped[str] = mapped_column(String(10), default="ZH", nullable=False)
    country: Mapped[str] = mapped_column(String(50), default="Schweiz", nullable=False)
    phone: Mapped[str] = mapped_column(String(50), nullable=False)
    email: Mapped[str] = mapped_column(String(150), nullable=False)
    directions_info: Mapped[str] = mapped_column(Text, default="", nullable=False)
    accessibility_info: Mapped[str] = mapped_column(
        String(200),
        default="Rollstuhlgängig",
        nullable=False,
    )
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
