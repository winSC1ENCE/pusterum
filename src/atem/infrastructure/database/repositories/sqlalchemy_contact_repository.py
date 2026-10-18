"""SQLAlchemy implementation of IContactRepository."""

from collections.abc import Sequence
from datetime import datetime
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import ColumnElement, and_, case, delete, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from atem.domain.interfaces.contact_repository import IContactRepository
from atem.domain.interfaces.secret_cipher import ISecretCipher
from atem.domain.models.contact import (
    OPEN_STATUSES,
    ContactMessage,
    ContactMessageEvent,
    DeletionRecord,
    EventAction,
    MessageQuery,
    MessageSort,
    MessageStatus,
    RetentionPolicy,
)
from atem.infrastructure.database.models.contact import (
    ContactMessageEventModel,
    ContactMessageModel,
    DeletionLogModel,
    UsedCaptchaChallengeModel,
)
from atem.infrastructure.database.models.user import UserModel
from atem.infrastructure.database.repositories.base import SqlAlchemyRepository

logger = structlog.get_logger()

# Free text may contain health data (ADR-0006, TDR-0012): stored encrypted, decrypted on read.
ENCRYPTED_FIELDS = frozenset({"message", "sender_phone", "notes"})
# Shown instead of a value that no longer decrypts (SECRET_KEY changed); never written back.
UNREADABLE = "[nicht lesbar: Schlüssel geändert]"

_M = ContactMessageModel
_OPEN_FIRST = case((_M.status.in_(OPEN_STATUSES), 0), else_=1)
# Workflow order for sorting by status (alphabetical codes would mix open and closed ones).
_STATUS_ORDER = case({status: rank for rank, status in enumerate(MessageStatus)}, value=_M.status)
_ORDER_BY: dict[MessageSort, tuple[Any, ...]] = {
    MessageSort.OPEN_FIRST: (_OPEN_FIRST, _M.created_at.desc()),
    MessageSort.NEWEST: (_M.created_at.desc(),),
    MessageSort.OLDEST: (_M.created_at,),
    MessageSort.NAME: (func.lower(_M.sender_name), _M.created_at.desc()),
    MessageSort.STATUS: (_STATUS_ORDER, _M.created_at.desc()),
}


def _filters(query: MessageQuery) -> list[ColumnElement[bool]]:
    conditions: list[ColumnElement[bool]] = []
    if query.statuses:
        conditions.append(_M.status.in_(query.statuses))
    if text := query.text.strip():
        conditions.append(
            or_(
                _M.sender_name.icontains(text, autoescape=True),
                _M.sender_email.icontains(text, autoescape=True),
                _M.subject.icontains(text, autoescape=True),
            )
        )
    if query.received_from is not None:
        conditions.append(_M.created_at >= query.received_from)
    if query.received_before is not None:
        conditions.append(_M.created_at < query.received_before)
    return conditions


class SqlAlchemyContactRepository(
    SqlAlchemyRepository[ContactMessageModel, ContactMessage], IContactRepository
):
    """SQLAlchemy 2.0 Async repository for contact messages and captcha replay records."""

    model = ContactMessageModel
    entity = ContactMessage

    def __init__(self, session: AsyncSession, cipher: ISecretCipher) -> None:
        super().__init__(session)
        self._cipher = cipher

    def _encode(self, name: str, value: Any) -> Any:
        if name in ENCRYPTED_FIELDS and value is not None:
            return self._cipher.encrypt(value)
        return value

    def _decode(self, name: str, value: Any) -> Any:
        if name in ENCRYPTED_FIELDS and value is not None:
            try:
                return self._cipher.decrypt(value)
            except ValueError:
                logger.warning("contact_field_unreadable", field=name)
                return UNREADABLE
        return value

    def _apply(self, model: ContactMessageModel, entity: ContactMessage) -> None:
        stored = {name: getattr(model, name) for name in ENCRYPTED_FIELDS}
        super()._apply(model, entity)
        for name, ciphertext in stored.items():
            if getattr(entity, name) == UNREADABLE:  # keep the original ciphertext
                setattr(model, name, ciphertext)

    async def create_message(self, message: ContactMessage) -> ContactMessage:
        """Store incoming contact message."""
        return await self._add(message)

    async def search_messages(self, query: MessageQuery) -> tuple[list[ContactMessage], int]:
        """One page of matching messages (filtered and sorted in the database) and the total."""
        conditions = _filters(query)
        total = await self._session.scalar(select(func.count()).select_from(_M).where(*conditions))
        result = await self._session.execute(
            select(_M)
            .where(*conditions)
            .order_by(*_ORDER_BY[query.sort], _M.id)
            .limit(query.limit)
            .offset(query.offset)
        )
        return [self._to_entity(m) for m in result.scalars().all()], int(total or 0)

    async def get_message_by_id(self, message_id: UUID) -> ContactMessage | None:
        """Fetch single message by ID."""
        return await self._get(message_id)

    async def update_message(self, message: ContactMessage) -> ContactMessage:
        """Persist status, notes and confirmation flag."""
        return await self._save(message)

    async def add_event(self, event: ContactMessageEvent) -> None:
        """Append a history entry."""
        self._session.add(
            ContactMessageEventModel(
                id=event.id,
                created_at=event.created_at,
                message_id=event.message_id,
                action=event.action,
                old_value=event.old_value,
                new_value=event.new_value,
                actor_id=event.actor_id,
            )
        )
        await self._session.flush()

    async def list_events(self, message_id: UUID) -> list[ContactMessageEvent]:
        """History of a message, oldest first; ``actor_email`` from the admin account."""
        event = ContactMessageEventModel
        rows = await self._session.execute(
            select(event, UserModel.email)
            .outerjoin(UserModel, UserModel.id == event.actor_id)
            .where(event.message_id == message_id)
            .order_by(event.created_at, event.id)
        )
        return [
            ContactMessageEvent(
                id=e.id,
                created_at=e.created_at,
                updated_at=e.updated_at,
                message_id=e.message_id,
                action=EventAction(e.action),
                old_value=e.old_value,
                new_value=e.new_value,
                actor_id=e.actor_id,
                actor_email=email,
            )
            for e, email in rows.all()
        ]

    async def delete_message(self, message_id: UUID) -> bool:
        """Delete message by ID, with its history."""
        await self._delete_events(_M.id == message_id)
        return await self._delete(message_id)

    async def delete_messages(self, message_ids: Sequence[UUID]) -> int:
        """Delete these messages with their history."""
        if not message_ids:
            return 0
        await self._delete_events(_M.id.in_(message_ids))
        result = await self._session.execute(delete(_M).where(_M.id.in_(message_ids)))
        return int(getattr(result, "rowcount", 0) or 0)

    async def record_deletions(self, records: Sequence[DeletionRecord]) -> None:
        """Add entries to the deletion log."""
        self._session.add_all(
            DeletionLogModel(
                id=r.id,
                created_at=r.created_at,
                message_id=r.message_id,
                reason=r.reason,
                email_hash=r.email_hash,
                actor_id=r.actor_id,
            )
            for r in records
        )
        await self._session.flush()

    async def reapply_deletions(self) -> int:
        """Delete messages listed in the deletion log (usually none; after a restore some)."""
        listed = _M.id.in_(select(DeletionLogModel.message_id))
        await self._delete_events(listed)
        result = await self._session.execute(delete(_M).where(listed))
        return int(getattr(result, "rowcount", 0) or 0)

    async def purge_deletion_log(self, cutoff: datetime) -> int:
        """Remove log entries created before ``cutoff``."""
        result = await self._session.execute(
            delete(DeletionLogModel).where(DeletionLogModel.created_at < cutoff)
        )
        return int(getattr(result, "rowcount", 0) or 0)

    async def _delete_events(self, *where: ColumnElement[bool]) -> None:
        # Explicit, because SQLite (tests) does not enforce ON DELETE CASCADE by default.
        await self._session.execute(
            delete(ContactMessageEventModel).where(
                ContactMessageEventModel.message_id.in_(select(_M.id).where(*where))
            )
        )

    async def find_by_sender_email(self, email: str) -> list[ContactMessage]:
        """All messages from an address (case and surrounding spaces ignored), oldest first."""
        return await self._list(
            func.lower(func.trim(ContactMessageModel.sender_email)) == email.strip().lower(),
            order_by=ContactMessageModel.created_at,
        )

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

    async def delete_expired(self, policy: RetentionPolicy, now: datetime) -> int:
        """Delete messages past their retention period (see ``RetentionPolicy.delete_after``)."""
        expired = or_(
            _M.created_at < now - policy.max_age,
            and_(_M.status == MessageStatus.DONE, _M.closed_at < now - policy.done),
            and_(_M.status == MessageStatus.SPAM, _M.closed_at < now - policy.spam),
        )
        await self._delete_events(expired)
        result = await self._session.execute(delete(_M).where(expired))
        return int(getattr(result, "rowcount", 0) or 0)

    async def anonymize_ips_older_than(self, cutoff: datetime) -> int:
        """Set ``ip_address`` to NULL for messages created before ``cutoff``."""
        result = await self._session.execute(
            update(ContactMessageModel)
            .where(
                ContactMessageModel.created_at < cutoff,
                ContactMessageModel.ip_address.is_not(None),
            )
            .values(ip_address=None)
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
