"""Contact Domain Models."""

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from uuid import UUID

from atem.domain.models.base import BaseEntity


class MessageStatus(StrEnum):
    """Processing status of an incoming contact message (TDR-0010).

    The codes are stored in the database and must stay stable; the German labels are for display.
    """

    NEW = "NEW"
    IN_PROGRESS = "IN_PROGRESS"
    REPLIED = "REPLIED"
    DONE = "DONE"
    SPAM = "SPAM"

    @property
    def label(self) -> str:
        """German display name."""
        return STATUS_LABELS[self]

    @property
    def is_open(self) -> bool:
        """True while the message still needs attention (not done, not spam)."""
        return self not in CLOSED_STATUSES


STATUS_LABELS: dict[MessageStatus, str] = {
    MessageStatus.NEW: "Neu",
    MessageStatus.IN_PROGRESS: "In Bearbeitung",
    MessageStatus.REPLIED: "Beantwortet",
    MessageStatus.DONE: "Erledigt",
    MessageStatus.SPAM: "Spam",
}
CLOSED_STATUSES = frozenset({MessageStatus.DONE, MessageStatus.SPAM})
OPEN_STATUSES = tuple(s for s in MessageStatus if s not in CLOSED_STATUSES)


class EventAction(StrEnum):
    """What an entry in the history of a message records."""

    STATUS = "STATUS"
    NOTES = "NOTES"


class MessageSort(StrEnum):
    """Sort orders of the admin list; the value is the URL parameter."""

    OPEN_FIRST = "offen"  # open messages first, then newest (default)
    NEWEST = "neu"
    OLDEST = "alt"
    NAME = "name"
    STATUS = "status"


@dataclass(frozen=True)
class MessageQuery:
    """Filter, sort and page of the admin list. Empty ``statuses`` means all statuses."""

    statuses: tuple[MessageStatus, ...] = ()
    text: str = ""  # searched in name, e-mail and subject (the free text is encrypted)
    received_from: datetime | None = None
    received_before: datetime | None = None
    sort: MessageSort = MessageSort.OPEN_FIRST
    limit: int = 25
    offset: int = 0


@dataclass(frozen=True)
class RetentionPolicy:
    """How long contact messages are kept (ADR-0006, TDR-0010).

    Closed messages are deleted a fixed time after closing, all others at the latest after
    ``max_age`` from receipt.
    """

    done: timedelta = timedelta(days=183)
    spam: timedelta = timedelta(days=7)
    max_age: timedelta = timedelta(days=365)

    def delete_after(self, message: "ContactMessage") -> datetime:
        """Point in time from which the retention job deletes the message."""
        latest = message.created_at + self.max_age
        if message.closed_at is None:
            return latest
        if message.status == MessageStatus.DONE:
            return min(latest, message.closed_at + self.done)
        if message.status == MessageStatus.SPAM:
            return min(latest, message.closed_at + self.spam)
        return latest


@dataclass(kw_only=True)
class ContactMessage(BaseEntity):
    """Contact inquiry from the website."""

    sender_name: str
    sender_email: str
    sender_phone: str | None = None
    subject: str = "Kontaktanfrage via Website"
    message: str
    status: MessageStatus = MessageStatus.NEW
    # Set when the message is closed (done or spam), cleared when it is reopened.
    closed_at: datetime | None = None
    notes: str | None = None
    ip_address: str | None = None
    # Peppered SHA-256 of the lower-cased sender e-mail: limits confirmation mails per
    # address without needing to query the plain address.
    email_hash: str | None = None
    confirmation_sent: bool = False

    @property
    def first_name(self) -> str:
        """First word of the sender name (notification mail without personal details)."""
        return self.sender_name.split()[0] if self.sender_name.split() else ""

    def change_status(self, status: MessageStatus, now: datetime | None = None) -> None:
        """Set the status and keep ``closed_at`` in line with it."""
        if status == self.status:
            return
        self.status = status
        if status in CLOSED_STATUSES:
            self.closed_at = now or datetime.now(UTC)
        else:
            self.closed_at = None


@dataclass(kw_only=True)
class ContactMessageEvent(BaseEntity):
    """One entry in the history of a message: who changed what and when (no message content).

    ``actor_email`` is filled when reading (from the admin account) and never stored.
    """

    message_id: UUID
    action: EventAction
    old_value: str | None = None
    new_value: str | None = None
    actor_id: UUID | None = None
    actor_email: str | None = field(default=None, compare=False)
