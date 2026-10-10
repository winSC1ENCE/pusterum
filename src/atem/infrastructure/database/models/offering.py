"""SQLAlchemy ORM model for service offerings."""

from sqlalchemy import Boolean, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from atem.infrastructure.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ServiceOfferingModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Database table for treatments and service offerings."""

    __tablename__ = "service_offerings"

    title: Mapped[str] = mapped_column(String(150), nullable=False)
    slug: Mapped[str] = mapped_column(String(150), unique=True, index=True, nullable=False)
    subtitle: Mapped[str] = mapped_column(String(250), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    price_chf: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    is_health_insurance_recognized: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
