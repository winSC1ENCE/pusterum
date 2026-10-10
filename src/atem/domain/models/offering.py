"""Service offering (treatment + price) shown in the «Angebote & Tarife» section."""

from dataclasses import dataclass

from atem.domain.models.base import BaseEntity


@dataclass(kw_only=True)
class ServiceOffering(BaseEntity):
    """A bookable offer with duration and price."""

    title: str
    slug: str
    subtitle: str
    description: str
    duration_minutes: int = 60
    price_chf: float = 0.0
    is_health_insurance_recognized: bool = False
    sort_order: int = 0
    is_active: bool = True
