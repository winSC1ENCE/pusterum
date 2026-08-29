"""Profile Application Service."""

from uuid import UUID

from atem.application.dto.profile import (
    CompetencyDTO,
    PracticeInfoDTO,
    ServiceOfferingDTO,
    TherapistProfileDTO,
)
from atem.domain.exceptions import EntityNotFoundException
from atem.domain.interfaces.profile_repository import IProfileRepository
from atem.domain.models.profile import PracticeInfo, ServiceOffering, TherapistProfile


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

    async def create_service(self, dto: ServiceOfferingDTO) -> ServiceOfferingDTO:
        """Create new service offering."""
        service = ServiceOffering(
            title=dto.title,
            slug=dto.slug,
            subtitle=dto.subtitle,
            description=dto.description,
            duration_minutes=dto.duration_minutes,
            price_chf=dto.price_chf,
            is_health_insurance_recognized=dto.is_health_insurance_recognized,
            sort_order=dto.sort_order,
            is_active=dto.is_active,
        )
        saved = await self._repository.save_service(service)
        dto.id = saved.id
        return dto

    async def update_service(self, service_id: UUID, dto: ServiceOfferingDTO) -> ServiceOfferingDTO:
        """Update existing service offering."""
        existing = await self._repository.get_service_by_id(service_id)
        if not existing:
            raise EntityNotFoundException("ServiceOffering", str(service_id))

        existing.title = dto.title
        existing.slug = dto.slug
        existing.subtitle = dto.subtitle
        existing.description = dto.description
        existing.duration_minutes = dto.duration_minutes
        existing.price_chf = dto.price_chf
        existing.is_health_insurance_recognized = dto.is_health_insurance_recognized
        existing.sort_order = dto.sort_order
        existing.is_active = dto.is_active

        saved = await self._repository.save_service(existing)
        dto.id = saved.id
        return dto

    async def delete_service(self, service_id: UUID) -> bool:
        """Delete service offering."""
        deleted = await self._repository.delete_service(service_id)
        if not deleted:
            raise EntityNotFoundException("ServiceOffering", str(service_id))
        return True

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
