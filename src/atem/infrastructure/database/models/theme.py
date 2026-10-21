"""SQLAlchemy ORM Model for Theme and Corporate Design Configuration."""

from sqlalchemy import Boolean, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from atem.domain.models.theme import ColorPresetKey, PageSection, ShapeType
from atem.infrastructure.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ThemeConfigModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Database table for corporate design and theme configuration."""

    __tablename__ = "theme_configs"

    preset_key: Mapped[ColorPresetKey] = mapped_column(
        SAEnum(ColorPresetKey, native_enum=False, length=30),
        default=ColorPresetKey.SALBEI_SAND,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(100), default="Salbei & Sand", nullable=False)
    primary_color: Mapped[str] = mapped_column(String(20), default="#4A6C50", nullable=False)
    primary_hover: Mapped[str] = mapped_column(String(20), default="#3C5641", nullable=False)
    secondary_color: Mapped[str] = mapped_column(String(20), default="#CEDECF", nullable=False)
    accent_color: Mapped[str] = mapped_column(String(20), default="#7FA485", nullable=False)
    background_color: Mapped[str] = mapped_column(String(20), default="#FAF8F5", nullable=False)
    surface_color: Mapped[str] = mapped_column(String(20), default="#FFFFFF", nullable=False)
    surface_muted: Mapped[str] = mapped_column(String(20), default="#F3EFE8", nullable=False)
    text_main_color: Mapped[str] = mapped_column(String(20), default="#1E293B", nullable=False)
    text_muted_color: Mapped[str] = mapped_column(String(20), default="#64748B", nullable=False)
    border_color: Mapped[str] = mapped_column(String(20), default="#E6DED1", nullable=False)

    heading_font: Mapped[str] = mapped_column(String(50), default="Lora", nullable=False)
    body_font: Mapped[str] = mapped_column(String(50), default="Plus Jakarta Sans", nullable=False)

    active_shape: Mapped[ShapeType] = mapped_column(
        SAEnum(ShapeType, native_enum=False, length=30),
        default=ShapeType.DANDELION_SEED,
        nullable=False,
    )
    dandelion_mode: Mapped[str] = mapped_column(String(255), default="disabled", nullable=False)
    dandelion_seed_size: Mapped[int] = mapped_column(default=48, nullable=False)
    dandelion_seed_opacity: Mapped[int] = mapped_column(default=80, nullable=False)
    kids_photo_opacity: Mapped[int] = mapped_column(default=30, nullable=False)
    header_opacity: Mapped[int] = mapped_column(default=60, nullable=False)
    show_phone: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Comma separated PageSection values (see SqlAlchemyThemeRepository)
    section_order: Mapped[str] = mapped_column(
        String(255), default=",".join(PageSection), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
