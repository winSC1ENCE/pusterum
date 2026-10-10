"""Global exception handlers: meaningful status codes instead of HTTP 500.

Browsers get friendly HTML pages (404/500), HTMX/API callers a short JSON/text body.
"""

from typing import Any

import structlog
from litestar import MediaType, Request
from litestar.exceptions import HTTPException, NotFoundException
from litestar.response import Response, Template
from litestar.status_codes import (
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_429_TOO_MANY_REQUESTS,
    HTTP_500_INTERNAL_SERVER_ERROR,
)
from pydantic import ValidationError as PydanticValidationError

from atem.domain.exceptions import (
    EntityNotFoundException,
    RateLimitedException,
    ValidationException,
)

logger = structlog.get_logger(__name__)


def _wants_html(request: Request[Any, Any, Any]) -> bool:
    return (
        request.method == "GET"
        and request.headers.get("hx-request") != "true"
        and "text/html" in request.headers.get("accept", "")
    )


def _error_response(
    request: Request[Any, Any, Any], status_code: int, message: str
) -> Response[Any]:
    if _wants_html(request):
        return Template(
            template_name="pages/error.html",
            context={"status_code": status_code, "message": message},
            status_code=status_code,
        )
    return Response(content={"detail": message}, status_code=status_code)


def validation_error_handler(_request: Request[Any, Any, Any], exc: Exception) -> Response[Any]:
    """Invalid input (pydantic or domain rules) → 400 with a human readable message."""
    if isinstance(exc, ValidationException):
        message = exc.message
    elif isinstance(exc, PydanticValidationError):
        message = "Ungültige Eingabe: " + "; ".join(
            f"{'.'.join(str(p) for p in err['loc'])}: {err['msg']}" for err in exc.errors()
        )
    else:
        message = "Ungültige Eingabe."
    return Response(content={"detail": message}, status_code=HTTP_400_BAD_REQUEST)


def not_found_handler(request: Request[Any, Any, Any], _exc: Exception) -> Response[Any]:
    """Unknown pages or entities → 404."""
    return _error_response(request, HTTP_404_NOT_FOUND, "Die Seite wurde nicht gefunden.")


def rate_limited_handler(request: Request[Any, Any, Any], exc: Exception) -> Response[Any]:
    """Abuse protection triggered → 429."""
    message = exc.message if isinstance(exc, RateLimitedException) else "Zu viele Anfragen."
    return _error_response(request, HTTP_429_TOO_MANY_REQUESTS, message)


def internal_error_handler(request: Request[Any, Any, Any], exc: Exception) -> Response[Any]:
    """Unexpected errors → generic 500 page; details only in the log."""
    if isinstance(exc, HTTPException):
        return Response(
            content={"detail": exc.detail},
            status_code=exc.status_code,
            headers=exc.headers,
            media_type=MediaType.JSON,
        )
    logger.exception("unhandled_exception", path=request.url.path)
    return _error_response(
        request,
        HTTP_500_INTERNAL_SERVER_ERROR,
        "Es ist ein unerwarteter Fehler aufgetreten. Bitte versuchen Sie es später erneut.",
    )


EXCEPTION_HANDLERS: dict[type[Exception] | int, Any] = {
    ValidationException: validation_error_handler,
    PydanticValidationError: validation_error_handler,
    EntityNotFoundException: not_found_handler,
    NotFoundException: not_found_handler,
    RateLimitedException: rate_limited_handler,
    HTTP_500_INTERNAL_SERVER_ERROR: internal_error_handler,
}
