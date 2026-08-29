"""Profile and Content Domain Models."""

from dataclasses import dataclass, field

from atem.domain.models.base import BaseEntity


@dataclass(kw_only=True)
class Competency(BaseEntity):
    """Competency or qualification of the therapist."""

    title: str
    description: str
    icon_name: str = "sparkles"
    sort_order: int = 0
    is_active: bool = True


@dataclass(kw_only=True)
class ServiceOffering(BaseEntity):
    """Service offering / treatment modality."""

    title: str
    slug: str
    subtitle: str
    description: str
    duration_minutes: int = 60
    price_chf: float = 140.0
    is_health_insurance_recognized: bool = True
    sort_order: int = 0
    is_active: bool = True


@dataclass(kw_only=True)
class PracticeInfo(BaseEntity):
    """Information about the physical practice location."""

    name: str
    street: str
    zip_code: str
    city: str
    canton: str = "ZH"
    country: str = "Schweiz"
    phone: str
    email: str
    directions_info: str = ""
    accessibility_info: str = "Rollstuhlgängig"
    latitude: float | None = None
    longitude: float | None = None


@dataclass(kw_only=True)
class TherapistProfile(BaseEntity):
    """Main profile of the breath therapist."""

    full_name: str
    title: str
    diploma: str
    tagline: str
    bio: str
    quote: str
    profile_image_url: str = "/static/images/profile.jpg"
    booking_external_url: str | None = None
    competencies: list[Competency] = field(default_factory=list)
    services: list[ServiceOffering] = field(default_factory=list)
    practice: PracticeInfo | None = None
