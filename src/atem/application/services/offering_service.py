"""Offering Application Service – «Angebote & Tarife»."""

import re
import unicodedata
from uuid import UUID

import structlog

from atem.application.dto.offering import ServiceFormDTO, ServiceOfferingDTO
from atem.domain.exceptions import EntityNotFoundException
from atem.domain.interfaces.offering_repository import IOfferingRepository
from atem.domain.models.offering import ServiceOffering

logger = structlog.get_logger(__name__)

_UMLAUTS = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"})


def slugify(text: str) -> str:
    """Lower-case ASCII slug: 'Einzelsitzung Atem & Körper' -> 'einzelsitzung-atem-koerper'."""
    ascii_text = (
        unicodedata.normalize("NFKD", text.lower().translate(_UMLAUTS))
        .encode("ascii", "ignore")
        .decode()
    )
    return re.sub(r"[^a-z0-9]+", "-", ascii_text).strip("-")[:150]


class OfferingService:
    """Create, update, list and delete service offerings."""

    def __init__(self, repository: IOfferingRepository) -> None:
        self._repository = repository

    async def list_services(self, *, include_inactive: bool = False) -> list[ServiceOfferingDTO]:
        """Offerings ordered by sort order (admin view includes hidden ones)."""
        offerings = await self._repository.list_offerings(active_only=not include_inactive)
        return [ServiceOfferingDTO.model_validate(o) for o in offerings]

    async def booking_subjects(self) -> list[str]:
        """One contact form subject per offering shown on the website."""
        return [service.booking_subject for service in await self.list_services()]

    async def create_service(self, form: ServiceFormDTO) -> ServiceOfferingDTO:
        """Create a new offering (never claims insurance recognition)."""
        offering = ServiceOffering(**form.model_dump(), slug=await self._unique_slug(form.title))
        saved = await self._repository.save_offering(offering)
        logger.info("admin_action", action="service_created", service_id=str(saved.id))
        return ServiceOfferingDTO.model_validate(saved)

    async def update_service(self, service_id: UUID, form: ServiceFormDTO) -> ServiceOfferingDTO:
        """Update an existing offering."""
        existing = await self._repository.get_offering(service_id)
        if existing is None:
            raise EntityNotFoundException("ServiceOffering", str(service_id))
        for name, value in form.model_dump().items():
            setattr(existing, name, value)
        existing.slug = await self._unique_slug(form.title, exclude_id=service_id)
        saved = await self._repository.save_offering(existing)
        logger.info("admin_action", action="service_updated", service_id=str(service_id))
        return ServiceOfferingDTO.model_validate(saved)

    async def delete_service(self, service_id: UUID) -> bool:
        """Delete an offering."""
        if not await self._repository.delete_offering(service_id):
            raise EntityNotFoundException("ServiceOffering", str(service_id))
        logger.info("admin_action", action="service_deleted", service_id=str(service_id))
        return True

    async def _unique_slug(self, title: str, exclude_id: UUID | None = None) -> str:
        base = slugify(title) or "angebot"
        offerings = await self._repository.list_offerings(active_only=False)
        taken = {o.slug for o in offerings if o.id != exclude_id}
        slug, counter = base, 2
        while slug in taken:
            slug, counter = f"{base}-{counter}", counter + 1
        return slug
