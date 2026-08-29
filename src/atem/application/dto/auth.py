"""Authentication DTOs."""

from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from atem.domain.models.user import UserRole


class LoginRequestDTO(BaseModel):
    """Admin login request credentials."""

    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=6)


class UserResponseDTO(BaseModel):
    """Safe user profile response DTO."""

    id: UUID
    username: str
    email: EmailStr
    role: UserRole
    is_active: bool
