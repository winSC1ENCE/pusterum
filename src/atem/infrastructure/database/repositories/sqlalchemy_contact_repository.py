"""SQLAlchemy implementation of IContactRepository."""

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from atem.domain.interfaces.contact_repository import IContactRepository
from atem.domain.models.contact import ContactMessage, MessageStatus
from atem.infrastructure.database.models.contact import ContactMessageModel


class SqlAlchemyContactRepository(IContactRepository):
    """SQLAlchemy 2.0 Async repository for Contact Messages."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_message(self, message: ContactMessage) -> ContactMessage:
        """Store incoming contact message."""
        model = ContactMessageModel(
            id=message.id,
            sender_name=message.sender_name,
            sender_email=message.sender_email,
            sender_phone=message.sender_phone,
            subject=message.subject,
            message=message.message,
            status=message.status,
            notes=message.notes,
            ip_address=message.ip_address,
        )
        self._session.add(model)
        await self._session.flush()
        message.id = model.id
        message.created_at = model.created_at
        message.updated_at = model.updated_at
        return message

    async def get_messages(
        self,
        *,
        status: MessageStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ContactMessage]:
        """Fetch messages with status filter."""
        stmt = (
            select(ContactMessageModel)
            .order_by(ContactMessageModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if status:
            stmt = stmt.where(ContactMessageModel.status == status)

        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [
            ContactMessage(
                id=m.id,
                created_at=m.created_at,
                updated_at=m.updated_at,
                sender_name=m.sender_name,
                sender_email=m.sender_email,
                sender_phone=m.sender_phone,
                subject=m.subject,
                message=m.message,
                status=m.status,
                notes=m.notes,
                ip_address=m.ip_address,
            )
            for m in models
        ]

    async def get_message_by_id(self, message_id: UUID) -> ContactMessage | None:
        """Fetch single message by ID."""
        stmt = select(ContactMessageModel).where(ContactMessageModel.id == message_id)
        result = await self._session.execute(stmt)
        m = result.scalar_one_or_none()
        if not m:
            return None
        return ContactMessage(
            id=m.id,
            created_at=m.created_at,
            updated_at=m.updated_at,
            sender_name=m.sender_name,
            sender_email=m.sender_email,
            sender_phone=m.sender_phone,
            subject=m.subject,
            message=m.message,
            status=m.status,
            notes=m.notes,
            ip_address=m.ip_address,
        )

    async def update_message(self, message: ContactMessage) -> ContactMessage:
        """Update message attributes."""
        stmt = select(ContactMessageModel).where(ContactMessageModel.id == message.id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if model:
            model.status = message.status
            model.notes = message.notes
            await self._session.flush()
            message.updated_at = model.updated_at

        return message

    async def delete_message(self, message_id: UUID) -> bool:
        """Delete message by ID."""
        stmt = delete(ContactMessageModel).where(ContactMessageModel.id == message_id)
        result = await self._session.execute(stmt)
        return bool(getattr(result, "rowcount", 0) > 0)
