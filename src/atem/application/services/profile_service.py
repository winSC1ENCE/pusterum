"""Profile Application Service."""

import re
import unicodedata
from uuid import UUID

import structlog

from atem.application.dto.profile import (
    CompetencyDTO,
    PracticeInfoDTO,
    ServiceFormDTO,
    ServiceOfferingDTO,
    TherapistProfileDTO,
)
from atem.domain.exceptions import EntityNotFoundException
from atem.domain.interfaces.profile_repository import IProfileRepository
from atem.domain.models.profile import PracticeInfo, ServiceOffering, TherapistProfile

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


class ProfileService:
    """Application service for managing therapist profile and practice content."""

    def __init__(self, profile_repository: IProfileRepository) -> None:
        self._repository = profile_repository

    async def get_public_profile(self) -> TherapistProfileDTO:
        """Fetch consolidated public profile for landing page."""
        profile = await self._repository.get_profile()
        competencies = await self._repository.get_competencies(active_only=True)
        services = await self._repository.get_services(active_only=True)
        practice = await self._repository.get_practice_info()

        return TherapistProfileDTO(
            id=profile.id,
            full_name=profile.full_name,
            title=profile.title,
            diploma=profile.diploma,
            tagline=profile.tagline,
            bio=profile.bio,
            quote=profile.quote,
            profile_image_url=profile.profile_image_url,
            booking_external_url=profile.booking_external_url,
            competencies=[
                CompetencyDTO(
                    id=c.id,
                    title=c.title,
                    description=c.description,
                    icon_name=c.icon_name,
                    sort_order=c.sort_order,
                    is_active=c.is_active,
                )
                for c in competencies
            ],
            services=[
                ServiceOfferingDTO(
                    id=s.id,
                    title=s.title,
                    slug=s.slug,
                    subtitle=s.subtitle,
                    description=s.description,
                    duration_minutes=s.duration_minutes,
                    price_chf=s.price_chf,
                    is_health_insurance_recognized=s.is_health_insurance_recognized,
                    sort_order=s.sort_order,
                    is_active=s.is_active,
                )
                for s in services
            ],
            practice=PracticeInfoDTO(
                id=practice.id,
                name=practice.name,
                street=practice.street,
                zip_code=practice.zip_code,
                city=practice.city,
                canton=practice.canton,
                country=practice.country,
                phone=practice.phone,
                email=practice.email,
                directions_info=practice.directions_info,
                accessibility_info=practice.accessibility_info,
                latitude=practice.latitude,
                longitude=practice.longitude,
            )
            if practice
            else None,
        )

    async def update_profile(self, dto: TherapistProfileDTO) -> TherapistProfileDTO:
        """Update profile information."""
        profile = TherapistProfile(
            full_name=dto.full_name,
            title=dto.title,
            diploma=dto.diploma,
            tagline=dto.tagline,
            bio=dto.bio,
            quote=dto.quote,
            profile_image_url=dto.profile_image_url,
            booking_external_url=dto.booking_external_url,
        )
        if dto.id:
            profile.id = dto.id
        saved = await self._repository.save_profile(profile)
        dto.id = saved.id
        return dto

    async def list_services(self, *, include_inactive: bool = False) -> list[ServiceOfferingDTO]:
        """Offerings ordered by sort order (admin view includes inactive ones)."""
        services = await self._repository.get_services(active_only=not include_inactive)
        return [ServiceOfferingDTO.model_validate(s, from_attributes=True) for s in services]

    async def create_service(self, form: ServiceFormDTO) -> ServiceOfferingDTO:
        """Create a new service offering."""
        service = ServiceOffering(
            **form.model_dump(),
            slug=await self._unique_slug(form.title),
            is_health_insurance_recognized=False,
        )
        saved = await self._repository.save_service(service)
        logger.info("admin_action", action="service_created", service_id=str(saved.id))
        return ServiceOfferingDTO.model_validate(saved, from_attributes=True)

    async def update_service(self, service_id: UUID, form: ServiceFormDTO) -> ServiceOfferingDTO:
        """Update an existing service offering."""
        existing = await self._repository.get_service_by_id(service_id)
        if not existing:
            raise EntityNotFoundException("ServiceOffering", str(service_id))
        for name, value in form.model_dump().items():
            setattr(existing, name, value)
        existing.slug = await self._unique_slug(form.title, exclude_id=service_id)
        saved = await self._repository.save_service(existing)
        logger.info("admin_action", action="service_updated", service_id=str(service_id))
        return ServiceOfferingDTO.model_validate(saved, from_attributes=True)

    async def delete_service(self, service_id: UUID) -> bool:
        """Delete service offering."""
        deleted = await self._repository.delete_service(service_id)
        if not deleted:
            raise EntityNotFoundException("ServiceOffering", str(service_id))
        logger.info("admin_action", action="service_deleted", service_id=str(service_id))
        return True

    async def _unique_slug(self, title: str, exclude_id: UUID | None = None) -> str:
        """URL-friendly, unique slug derived from the title (umlauts transliterated)."""
        base = slugify(title) or "angebot"
        taken = {
            s.slug
            for s in await self._repository.get_services(active_only=False)
            if s.id != exclude_id
        }
        slug, counter = base, 2
        while slug in taken:
            slug, counter = f"{base}-{counter}", counter + 1
        return slug

    async def update_practice_info(self, dto: PracticeInfoDTO) -> PracticeInfoDTO:
        """Update practice location info."""
        practice = PracticeInfo(
            name=dto.name,
            street=dto.street,
            zip_code=dto.zip_code,
            city=dto.city,
            canton=dto.canton,
            country=dto.country,
            phone=dto.phone,
            email=dto.email,
            directions_info=dto.directions_info,
            accessibility_info=dto.accessibility_info,
            latitude=dto.latitude,
            longitude=dto.longitude,
        )
        if dto.id:
            practice.id = dto.id
        saved = await self._repository.save_practice_info(practice)
        dto.id = saved.id
        return dto
