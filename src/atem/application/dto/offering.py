"""Service offering DTOs."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ServiceOfferingDTO(BaseModel):
    """Offering as shown on the website and in the admin."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    slug: str
    subtitle: str
    description: str
    duration_minutes: int
    price_chf: float
    is_health_insurance_recognized: bool = False
    sort_order: int = 0
    is_active: bool = True


class ServiceFormDTO(BaseModel):
    """Admin form for creating/updating an offering (slug is derived from the title)."""

    title: str = Field(..., min_length=2, max_length=150)
    subtitle: str = Field(default="", max_length=250)
    description: str = Field(..., min_length=10, max_length=2000)
    duration_minutes: int = Field(default=60, ge=15, le=300)
    price_chf: float = Field(default=0.0, ge=0.0, le=10_000.0)
    sort_order: int = Field(default=0, ge=0, le=999)
    is_active: bool = True
