"""User and Authentication Domain Models."""

from dataclasses import dataclass
from enum import StrEnum

from atem.domain.models.base import BaseEntity


class UserRole(StrEnum):
    """User authorization roles."""

    ADMIN = "ADMIN"
    EDITOR = "EDITOR"


@dataclass(kw_only=True)
class User(BaseEntity):
    """System user model for administration."""

    username: str
    email: str
    password_hash: str
    role: UserRole = UserRole.ADMIN
    is_active: bool = True
