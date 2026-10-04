"""Admin session handling, route guard and unauthorized-response handling.

Session layout (encrypted cookie):

* ``user``        – fully authenticated admin: ``{"id", "email", "role", "sv"}``
* ``pending_2fa`` – password verified, waiting for the TOTP code: ``{"id", "sv", "exp"}``

``sv`` is the user's ``session_version``. Logout, password and 2FA changes increment it in
the database, which revokes every cookie issued before – on all devices.
"""

import time
from typing import TYPE_CHECKING, Any
from uuid import UUID

from litestar import Request
from litestar.connection import ASGIConnection
from litestar.exceptions import HTTPException, NotAuthorizedException
from litestar.handlers.base import BaseRouteHandler
from litestar.response import Redirect, Response
from litestar.status_codes import HTTP_401_UNAUTHORIZED

from atem.application.dto.auth import UserResponseDTO
from atem.infrastructure.config.settings import get_settings
from atem.presentation.bootstrap import build_auth_service

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

SESSION_USER_KEY = "user"
SESSION_PENDING_KEY = "pending_2fa"
PENDING_2FA_TTL_SECONDS = 300
_STATE_CACHE_KEY = "_admin_user"
# Routes the guard allows while 2FA setup or a password change is still pending.
ALLOW_PENDING_SECURITY_OPT = "allow_pending_security"
# Admin endpoints called via fetch()/HTMX – they answer 401 instead of redirecting.
API_PATH_PREFIXES = ("/admin/content/", "/admin/images/")


class SecuritySetupRequiredException(NotAuthorizedException):
    """The admin must finish 2FA enrolment and/or change the initial password first."""


def store_authenticated_session(request: Request[Any, Any, Any], user: UserResponseDTO) -> None:
    """Issue a fresh authenticated session (drops any previous session data)."""
    request.clear_session()
    request.set_session(
        {
            SESSION_USER_KEY: {
                "id": str(user.id),
                "email": user.email,
                "role": user.role.value,
                "sv": user.session_version,
            }
        }
    )


def store_pending_second_factor(request: Request[Any, Any, Any], user: UserResponseDTO) -> None:
    """Remember that the password step succeeded and the TOTP step is outstanding."""
    request.clear_session()
    request.set_session(
        {
            SESSION_PENDING_KEY: {
                "id": str(user.id),
                "sv": user.session_version,
                "exp": int(time.time()) + PENDING_2FA_TTL_SECONDS,
            }
        }
    )


def pending_second_factor_user_id(request: Request[Any, Any, Any]) -> UUID | None:
    """Return the user id of a not yet expired pending 2FA login."""
    pending = request.session.get(SESSION_PENDING_KEY) if request.session else None
    if not pending or int(pending.get("exp", 0)) < time.time():
        return None
    try:
        return UUID(pending["id"])
    except (KeyError, ValueError):
        return None


async def load_session_user(
    connection: ASGIConnection[Any, Any, Any, Any],
) -> UserResponseDTO | None:
    """Return the logged-in admin if the session cookie is still valid (DB check, cached)."""
    if _STATE_CACHE_KEY in connection.state:
        cached: UserResponseDTO | None = connection.state[_STATE_CACHE_KEY]
        return cached

    user: UserResponseDTO | None = None
    data = connection.session.get(SESSION_USER_KEY) if connection.scope.get("session") else None
    if isinstance(data, dict) and "id" in data and "sv" in data:
        try:
            user_id = UUID(str(data["id"]))
        except ValueError:
            user_id = None
        if user_id is not None:
            factory: async_sessionmaker[AsyncSession] = connection.app.state.session_factory
            async with factory() as db_session:
                user = await build_auth_service(db_session).get_session_user(
                    user_id, int(data["sv"])
                )
    connection.state[_STATE_CACHE_KEY] = user
    return user


def security_setup_pending(user: UserResponseDTO) -> bool:
    """True while the admin still has to enrol 2FA or change the initial password."""
    return user.must_change_password or (get_settings().require_2fa and not user.totp_enabled)


async def require_admin(
    connection: ASGIConnection[Any, Any, Any, Any], route_handler: BaseRouteHandler
) -> None:
    """Litestar guard protecting every admin route."""
    user = await load_session_user(connection)
    if user is None:
        raise NotAuthorizedException("Anmeldung erforderlich.")
    if security_setup_pending(user) and not route_handler.opt.get(ALLOW_PENDING_SECURITY_OPT):
        raise SecuritySetupRequiredException("Sicherheitseinrichtung erforderlich.")


def unauthorized_handler(request: Request[Any, Any, Any], exc: HTTPException) -> Response[Any]:
    """Redirect browsers to the login (or security setup); answer API/HTMX calls with 401."""
    target = (
        "/admin/security" if isinstance(exc, SecuritySetupRequiredException) else "/admin/login"
    )
    is_htmx = request.headers.get("hx-request") == "true"
    if is_htmx or request.url.path.startswith(API_PATH_PREFIXES):
        headers = {"HX-Redirect": target} if is_htmx else {}
        return Response(
            content={"detail": exc.detail}, status_code=HTTP_401_UNAUTHORIZED, headers=headers
        )
    return Redirect(path=target)
