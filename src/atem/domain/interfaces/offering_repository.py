"""Offering Repository Interface (ABC)."""

from abc import ABC, abstractmethod
from uuid import UUID

from atem.domain.models.offering import ServiceOffering


class IOfferingRepository(ABC):
    """Storage of service offerings."""

    @abstractmethod
    async def list_offerings(self, *, active_only: bool = True) -> list[ServiceOffering]:
        """Offerings ordered by sort order."""

    @abstractmethod
    async def get_offering(self, offering_id: UUID) -> ServiceOffering | None:
        """Fetch one offering."""

    @abstractmethod
    async def save_offering(self, offering: ServiceOffering) -> ServiceOffering:
        """Insert or update an offering."""

    @abstractmethod
    async def delete_offering(self, offering_id: UUID) -> bool:
        """Delete an offering; False if it did not exist."""
