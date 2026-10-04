"""Profile and Content Data Transfer Objects (DTOs)."""

from uuid import UUID

from pydantic import BaseModel, Field


class CompetencyDTO(BaseModel):
    """DTO for therapist competency."""

    id: UUID | None = None
    title: str = Field(..., min_length=2, max_length=150)
    description: str = Field(..., min_length=5, max_length=1000)
    icon_name: str = Field(default="sparkles", max_length=50)
    sort_order: int = Field(default=0, ge=0)
    is_active: bool = True


class ServiceOfferingDTO(BaseModel):
    """DTO for service offering."""

    id: UUID | None = None
    title: str = Field(..., min_length=2, max_length=150)
    slug: str = Field(..., min_length=2, max_length=150)
    subtitle: str = Field(..., max_length=250)
    description: str = Field(..., min_length=10)
    duration_minutes: int = Field(default=60, ge=15, le=300)
    price_chf: float = Field(default=140.0, ge=0.0)
    is_health_insurance_recognized: bool = False
    sort_order: int = Field(default=0, ge=0)
    is_active: bool = True


class PracticeInfoDTO(BaseModel):
    """DTO for practice location and contact information."""

    id: UUID | None = None
    name: str = Field(..., min_length=2, max_length=200)
    street: str = Field(..., min_length=2, max_length=200)
    zip_code: str = Field(..., min_length=4, max_length=10)
    city: str = Field(..., min_length=2, max_length=100)
    canton: str = Field(default="ZH", max_length=10)
    country: str = Field(default="Schweiz", max_length=50)
    phone: str = Field(..., min_length=5, max_length=50)
    email: str = Field(..., min_length=5, max_length=150)
    directions_info: str = Field(default="", max_length=1000)
    accessibility_info: str = Field(default="Rollstuhlgängig", max_length=200)
    latitude: float | None = None
    longitude: float | None = None


class TherapistProfileDTO(BaseModel):
    """DTO for main therapist profile."""

    id: UUID | None = None
    full_name: str = Field(..., min_length=2, max_length=150)
    title: str = Field(..., min_length=2, max_length=150)
    diploma: str = Field(..., min_length=2, max_length=250)
    tagline: str = Field(..., min_length=5, max_length=300)
    bio: str = Field(..., min_length=20)
    quote: str = Field(..., min_length=5, max_length=500)
    profile_image_url: str = Field(default="/static/images/profile.jpg")
    booking_external_url: str | None = None
    competencies: list[CompetencyDTO] = Field(default_factory=list)
    services: list[ServiceOfferingDTO] = Field(default_factory=list)
    practice: PracticeInfoDTO | None = None


class ServiceFormDTO(BaseModel):
    """Admin form for creating/updating an offering (slug is derived from the title)."""

    title: str = Field(..., min_length=2, max_length=150)
    subtitle: str = Field(default="", max_length=250)
    description: str = Field(..., min_length=10, max_length=2000)
    duration_minutes: int = Field(default=60, ge=15, le=300)
    price_chf: float = Field(default=0.0, ge=0.0, le=10_000.0)
    sort_order: int = Field(default=0, ge=0, le=999)
    is_active: bool = True
