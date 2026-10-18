"""Generic SQLAlchemy repository base – maps dataclass entities to ORM models by field name.

Concrete repositories declare ``model`` and ``entity``; the shared helpers replace the
hand-written field-by-field copying. Repositories only ``flush()`` – the request (or the
CLI/bootstrap caller) owns the transaction and commits.
"""

from dataclasses import fields
from typing import Any, ClassVar
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from atem.infrastructure.database.base import Base

IMMUTABLE_FIELDS = frozenset({"id", "created_at", "updated_at"})


class SqlAlchemyRepository[ModelT: Base, EntityT]:
    """Shared CRUD plumbing for dataclass entities with a UUID primary key."""

    model: ClassVar[type[Any]]
    entity: ClassVar[type[Any]]

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @classmethod
    def _field_names(cls) -> tuple[str, ...]:
        return tuple(f.name for f in fields(cls.entity))

    def _encode(self, name: str, value: Any) -> Any:  # noqa: ARG002 - hook for subclasses
        """Convert an entity value to its stored form (identity; override e.g. to encrypt)."""
        return value

    def _decode(self, name: str, value: Any) -> Any:  # noqa: ARG002 - hook for subclasses
        """Convert a stored value back to the entity value (identity; override to decrypt)."""
        return value

    def _to_entity(self, model: ModelT) -> EntityT:
        entity: EntityT = self.entity(
            **{n: self._decode(n, getattr(model, n)) for n in self._field_names()}
        )
        return entity

    def _apply(self, model: ModelT, entity: EntityT) -> None:
        for name in self._field_names():
            if name not in IMMUTABLE_FIELDS:
                setattr(model, name, self._encode(name, getattr(entity, name)))

    async def _get(self, entity_id: UUID) -> EntityT | None:
        model = await self._session.get(self.model, entity_id)
        return self._to_entity(model) if model else None

    async def _add(self, entity: EntityT) -> EntityT:
        model = self.model(**{n: self._encode(n, getattr(entity, n)) for n in self._field_names()})
        self._session.add(model)
        await self._session.flush()
        return self._to_entity(model)

    async def _save(self, entity: EntityT) -> EntityT:
        """Insert or update by primary key."""
        model = await self._session.get(self.model, getattr(entity, "id"))  # noqa: B009
        if model is None:
            return await self._add(entity)
        self._apply(model, entity)
        await self._session.flush()
        return self._to_entity(model)

    async def _delete(self, entity_id: UUID) -> bool:
        result = await self._session.execute(delete(self.model).where(self.model.id == entity_id))
        return bool(getattr(result, "rowcount", 0))

    async def _list(self, *where: Any, order_by: Any = None) -> list[EntityT]:
        stmt = select(self.model).where(*where)
        if order_by is not None:
            stmt = stmt.order_by(order_by)
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]
