"""Contact Data Transfer Objects (DTOs)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from atem.domain.models.contact import MessageStatus

# Single-line fields must not contain control characters (header injection, log forging).
SINGLE_LINE = r"^[^\r\n\t\x00-\x1f\x7f]*$"

# Subjects offered in the contact form besides one «Terminanfrage: <Angebot>» per active offering.
GENERAL_CONTACT_SUBJECTS = (
    "Terminanfrage Erstgespräch",
    "Frage zu Ablauf & Kosten",
    "Allgemeine Frage zur Atem- und Körpertherapie",
    "Sonstiges",
)
FALLBACK_CONTACT_SUBJECT = "Sonstiges"


class CreateContactMessageDTO(BaseModel):
    """Incoming contact message submission payload."""

    sender_name: str = Field(..., min_length=2, max_length=120, pattern=SINGLE_LINE)
    sender_email: EmailStr = Field(..., max_length=150)
    sender_phone: str | None = Field(default=None, max_length=50, pattern=r"^[0-9+()/.\- ]*$")
    subject: str = Field(default="Kontaktanfrage via Website", max_length=200, pattern=SINGLE_LINE)
    message: str = Field(..., min_length=10, max_length=5000)
    honeypot: str | None = Field(default=None, max_length=200)


class ContactMessageResponseDTO(BaseModel):
    """Outgoing contact message response DTO."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    sender_name: str
    sender_email: str
    sender_phone: str | None
    subject: str
    message: str
    status: MessageStatus
    notes: str | None
    created_at: datetime
    confirmation_sent: bool = False
