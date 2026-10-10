"""SQLAlchemy implementation of IOfferingRepository."""

from uuid import UUID

from atem.domain.interfaces.offering_repository import IOfferingRepository
from atem.domain.models.offering import ServiceOffering
from atem.infrastructure.database.models.offering import ServiceOfferingModel
from atem.infrastructure.database.repositories.base import SqlAlchemyRepository


class SqlAlchemyOfferingRepository(
    SqlAlchemyRepository[ServiceOfferingModel, ServiceOffering], IOfferingRepository
):
    """Service offerings stored in ``service_offerings``."""

    model = ServiceOfferingModel
    entity = ServiceOffering

    async def list_offerings(self, *, active_only: bool = True) -> list[ServiceOffering]:
        conditions = [ServiceOfferingModel.is_active.is_(True)] if active_only else []
        return await self._list(*conditions, order_by=ServiceOfferingModel.sort_order.asc())

    async def get_offering(self, offering_id: UUID) -> ServiceOffering | None:
        return await self._get(offering_id)

    async def save_offering(self, offering: ServiceOffering) -> ServiceOffering:
        return await self._save(offering)

    async def delete_offering(self, offering_id: UUID) -> bool:
        return await self._delete(offering_id)
