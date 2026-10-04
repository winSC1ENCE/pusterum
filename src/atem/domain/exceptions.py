"""Domain Exceptions."""


class DomainException(Exception):
    """Base class for all domain-level exceptions."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class EntityNotFoundException(DomainException):
    """Raised when an entity is not found."""

    def __init__(self, entity_name: str, identifier: str | int) -> None:
        super().__init__(f"{entity_name} with identifier '{identifier}' was not found.")
        self.entity_name = entity_name
        self.identifier = identifier


class ValidationException(DomainException):
    """Raised when domain validation rules are violated."""


class AuthenticationException(DomainException):
    """Raised when authentication fails."""


class AuthorizationException(DomainException):
    """Raised when user lacks permission."""


class RateLimitedException(DomainException):
    """Raised when a client exceeds an abuse-protection limit."""
