"""SQLAlchemy implementation of IContactRepository."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError

from atem.domain.interfaces.contact_repository import IContactRepository
from atem.domain.models.contact import ContactMessage, MessageStatus
from atem.infrastructure.database.models.contact import (
    ContactMessageModel,
    UsedCaptchaChallengeModel,
)
from atem.infrastructure.database.repositories.base import SqlAlchemyRepository


class SqlAlchemyContactRepository(
    SqlAlchemyRepository[ContactMessageModel, ContactMessage], IContactRepository
):
    """SQLAlchemy 2.0 Async repository for contact messages and captcha replay records."""

    model = ContactMessageModel
    entity = ContactMessage

    async def create_message(self, message: ContactMessage) -> ContactMessage:
        """Store incoming contact message."""
        return await self._add(message)

    async def get_messages(
        self,
        *,
        status: MessageStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ContactMessage]:
        """Fetch messages (newest first) with optional status filter."""
        stmt = (
            select(ContactMessageModel)
            .order_by(ContactMessageModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if status:
            stmt = stmt.where(ContactMessageModel.status == status)
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def get_message_by_id(self, message_id: UUID) -> ContactMessage | None:
        """Fetch single message by ID."""
        return await self._get(message_id)

    async def update_message(self, message: ContactMessage) -> ContactMessage:
        """Persist status, notes and confirmation flag."""
        return await self._save(message)

    async def delete_message(self, message_id: UUID) -> bool:
        """Delete message by ID."""
        return await self._delete(message_id)

    async def count_by_status(self) -> dict[MessageStatus, int]:
        """Number of messages per status, counted in the database (not from a page)."""
        rows = await self._session.execute(
            select(ContactMessageModel.status, func.count()).group_by(ContactMessageModel.status)
        )
        return {MessageStatus(status): int(count) for status, count in rows.all()}

    async def count_messages_from_ip(self, ip_address: str, since: datetime) -> int:
        """Count messages sent from an IP address since the given time."""
        count = await self._session.scalar(
            select(func.count()).where(
                ContactMessageModel.ip_address == ip_address,
                ContactMessageModel.created_at >= since,
            )
        )
        return int(count or 0)

    async def confirmation_sent_since(self, email_hash: str, since: datetime) -> bool:
        """Return True if a confirmation mail went to this address since the given time."""
        count = await self._session.scalar(
            select(func.count()).where(
                ContactMessageModel.email_hash == email_hash,
                ContactMessageModel.confirmation_sent.is_(True),
                ContactMessageModel.created_at >= since,
            )
        )
        return bool(count)

    async def delete_messages_older_than(self, cutoff: datetime) -> int:
        """Delete messages created before ``cutoff``."""
        result = await self._session.execute(
            delete(ContactMessageModel).where(ContactMessageModel.created_at < cutoff)
        )
        return int(getattr(result, "rowcount", 0) or 0)

    async def register_captcha_challenge(self, challenge_id: str, expires_at: datetime) -> bool:
        """Mark a solved challenge as used; False on replay."""
        if await self._session.get(UsedCaptchaChallengeModel, challenge_id):
            return False
        try:
            async with self._session.begin_nested():
                self._session.add(
                    UsedCaptchaChallengeModel(challenge_id=challenge_id, expires_at=expires_at)
                )
        except IntegrityError:  # concurrent replay of the same solution
            return False
        return True

    async def purge_expired_captcha_challenges(self, now: datetime) -> int:
        """Remove used-challenge records that expired."""
        result = await self._session.execute(
            delete(UsedCaptchaChallengeModel).where(UsedCaptchaChallengeModel.expires_at < now)
        )
        return int(getattr(result, "rowcount", 0) or 0)
