"""Authentication Application Service."""

import structlog

from atem.application.dto.auth import LoginRequestDTO, UserResponseDTO
from atem.domain.exceptions import AuthenticationException, ValidationException
from atem.domain.interfaces.password_hasher import IPasswordHasher
from atem.domain.interfaces.user_repository import IUserRepository
from atem.domain.models.user import User, UserRole

logger = structlog.get_logger(__name__)

MIN_ADMIN_PASSWORD_LENGTH = 12


class AuthService:
    """Application service for administrator authentication."""

    def __init__(
        self,
        user_repository: IUserRepository,
        password_hasher: IPasswordHasher,
    ) -> None:
        self._user_repository = user_repository
        self._password_hasher = password_hasher

    async def authenticate(self, dto: LoginRequestDTO) -> UserResponseDTO:
        """Authenticate user credentials."""
        user = await self._user_repository.get_by_username(dto.username)
        if not user or not user.is_active:
            logger.warning(
                "Authentication failed: user not found or inactive",
                username=dto.username,
            )
            raise AuthenticationException("Ungültige Anmeldedaten.")

        if not self._password_hasher.verify_password(dto.password, user.password_hash):
            logger.warning("Authentication failed: password mismatch", username=dto.username)
            raise AuthenticationException("Ungültige Anmeldedaten.")

        logger.info("User authenticated successfully", username=user.username, user_id=str(user.id))
        return UserResponseDTO(
            id=user.id,
            username=user.username,
            email=user.email,
            role=user.role,
            is_active=user.is_active,
        )

    async def ensure_initial_admin(
        self,
        username: str,
        email: str,
        initial_password: str,
    ) -> None:
        """Ensure default admin account exists upon initialization."""
        existing = await self._user_repository.get_by_username(username)
        if not existing:
            hashed = self._password_hasher.hash_password(initial_password)
            admin_user = User(
                username=username,
                email=email,
                password_hash=hashed,
                role=UserRole.ADMIN,
                is_active=True,
            )
            await self._user_repository.create_user(admin_user)
            logger.info("Created initial admin user", username=username)

    async def create_admin(self, username: str, email: str, password: str) -> UserResponseDTO:
        """Create a new administrator account (used by the CLI in production)."""
        if len(password) < MIN_ADMIN_PASSWORD_LENGTH:
            raise ValidationException(
                f"Das Passwort muss mindestens {MIN_ADMIN_PASSWORD_LENGTH} Zeichen lang sein."
            )
        if await self._user_repository.get_by_username(username):
            raise ValidationException(f"Benutzer «{username}» existiert bereits.")
        user = await self._user_repository.create_user(
            User(
                username=username,
                email=email,
                password_hash=self._password_hasher.hash_password(password),
                role=UserRole.ADMIN,
                is_active=True,
            )
        )
        logger.info("admin_created", user_id=str(user.id))
        return UserResponseDTO(
            id=user.id,
            username=user.username,
            email=user.email,
            role=user.role,
            is_active=user.is_active,
        )
