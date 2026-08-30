"""Profile Repository Interface (ABC)."""

from abc import ABC, abstractmethod
from uuid import UUID

from atem.domain.models.profile import Competency, PracticeInfo, ServiceOffering, TherapistProfile


class IProfileRepository(ABC):
    """Abstract interface defining operations for profile and practice content."""

    @abstractmethod
    async def get_profile(self) -> TherapistProfile:
        """Fetch the active therapist profile."""

    @abstractmethod
    async def save_profile(self, profile: TherapistProfile) -> TherapistProfile:
        """Save or update therapist profile."""

    @abstractmethod
    async def get_competencies(self, *, active_only: bool = True) -> list[Competency]:
        """Fetch list of therapist competencies."""

    @abstractmethod
    async def get_services(self, *, active_only: bool = True) -> list[ServiceOffering]:
        """Fetch list of active service offerings."""

    @abstractmethod
    async def get_service_by_id(self, service_id: UUID) -> ServiceOffering | None:
        """Fetch single service offering by ID."""

    @abstractmethod
    async def save_service(self, service: ServiceOffering) -> ServiceOffering:
        """Create or update a service offering."""

    @abstractmethod
    async def delete_service(self, service_id: UUID) -> bool:
        """Delete a service offering by ID."""

    @abstractmethod
    async def get_practice_info(self) -> PracticeInfo | None:
        """Fetch practice location and contact information."""

    @abstractmethod
    async def save_practice_info(self, practice: PracticeInfo) -> PracticeInfo:
        """Save or update practice location information."""
