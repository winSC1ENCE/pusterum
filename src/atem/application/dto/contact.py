"""Contact Data Transfer Objects (DTOs)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from atem.domain.models.contact import MessageStatus


class CreateContactMessageDTO(BaseModel):
    """Incoming contact message submission payload."""

    sender_name: str = Field(..., min_length=2, max_length=120, description="Name des Absenders")
    sender_email: EmailStr = Field(..., description="E-Mail-Adresse für Rückantwort")
    sender_phone: str | None = Field(
        default=None,
        max_length=50,
        description="Telefonnummer optional",
    )
    subject: str = Field(default="Kontaktanfrage via Website", max_length=200)
    message: str = Field(..., min_length=10, max_length=5000, description="Nachrichtentext")
    honeypot: str | None = Field(default=None, description="Anti-Spam Honeypot (must be empty)")


class ContactMessageResponseDTO(BaseModel):
    """Outgoing contact message response DTO."""

    id: UUID
    sender_name: str
    sender_email: str
    sender_phone: str | None
    subject: str
    message: str
    status: MessageStatus
    notes: str | None
    created_at: datetime


class UpdateContactMessageStatusDTO(BaseModel):
    """Update status or internal notes for a contact inquiry."""

    status: MessageStatus
    notes: str | None = None
