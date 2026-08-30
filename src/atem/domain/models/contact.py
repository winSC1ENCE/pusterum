"""Contact Domain Models."""

from dataclasses import dataclass
from enum import StrEnum

from atem.domain.models.base import BaseEntity


class MessageStatus(StrEnum):
    """Status of an incoming contact message."""

    NEW = "NEW"
    READ = "READ"
    REPLIED = "REPLIED"
    ARCHIVED = "ARCHIVED"


@dataclass(kw_only=True)
class ContactMessage(BaseEntity):
    """Contact inquiry from the website."""

    sender_name: str
    sender_email: str
    sender_phone: str | None = None
    subject: str = "Kontaktanfrage via Website"
    message: str
    status: MessageStatus = MessageStatus.NEW
    notes: str | None = None
    ip_address: str | None = None
