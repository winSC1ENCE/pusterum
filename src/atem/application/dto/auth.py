"""Authentication DTOs."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from atem.domain.models.user import UserRole

MAX_PASSWORD_LENGTH = 256


class LoginRequestDTO(BaseModel):
    """Admin login request credentials."""

    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1, max_length=MAX_PASSWORD_LENGTH)


class UserResponseDTO(BaseModel):
    """Safe user profile response DTO (never contains secrets or hashes)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    email: EmailStr
    role: UserRole
    is_active: bool
    totp_enabled: bool = False
    must_change_password: bool = False
    session_version: int = 1


class LoginResultDTO(BaseModel):
    """Outcome of the password step of the login."""

    user: UserResponseDTO
    requires_totp: bool


class TotpSetupDTO(BaseModel):
    """Pending TOTP enrolment (secret is shown once and confirmed with a code)."""

    secret: str
    provisioning_uri: str
