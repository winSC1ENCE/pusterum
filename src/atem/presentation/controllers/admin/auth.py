"""Admin login (password + TOTP second factor) and logout."""

from typing import Any

from litestar import Controller, Request, get, post
from litestar.response import Redirect, Template
from pydantic import ValidationError

from atem.application.dto.auth import LoginRequestDTO
from atem.application.services.auth_service import AuthService
from atem.application.services.theme_service import ThemeService
from atem.domain.exceptions import AuthenticationException, RateLimitedException
from atem.presentation.controllers.admin.common import FormData
from atem.presentation.security.admin_auth import (
    load_session_user,
    pending_second_factor_user_id,
    store_authenticated_session,
    store_pending_second_factor,
)
from atem.presentation.security.device_cookie import device_claim, device_cookie

LOGIN_ERROR_INVALID_INPUT = "Bitte E-Mail-Adresse und Passwort eingeben."


def client_ip(request: Request[Any, Any, Any]) -> str:
    """Client IP as resolved by ProxyHeadersMiddleware."""
    return request.client.host if request.client else "unknown"


class AdminAuthController(Controller):
    """Two-step login flow: password → TOTP (if enabled) → session."""

    path = "/admin"
    include_in_schema = False

    async def _render(self, template: str, theme_service: ThemeService, **context: Any) -> Template:
        theme = await theme_service.get_active_theme()
        return Template(
            template_name=template,
            context={
                "theme": theme,
                "theme_css": theme_service.generate_css_variables(theme),
                **context,
            },
        )

    @get("/login")
    async def login_page(
        self, request: Request[Any, Any, Any], theme_service: ThemeService
    ) -> Template | Redirect:
        """Render the login form (or skip it when already logged in)."""
        if await load_session_user(request):
            return Redirect(path="/admin")
        return await self._render("admin/login.html", theme_service, error=None)

    @post("/login")
    async def process_login(
        self,
        request: Request[Any, Any, Any],
        auth_service: AuthService,
        theme_service: ThemeService,
        data: FormData,
    ) -> Template | Redirect:
        """Verify the password; continue with the second factor if enabled."""
        email = data.get("email", "")
        try:
            dto = LoginRequestDTO(email=email, password=data.get("password", ""))
            result = await auth_service.authenticate(dto, client_ip(request), device_claim(request))
        except ValidationError:
            error = LOGIN_ERROR_INVALID_INPUT
        except (AuthenticationException, RateLimitedException) as exc:
            error = exc.message
        else:
            if result.requires_totp:
                store_pending_second_factor(request, result.user)
                return Redirect(path="/admin/login/verify")
            store_authenticated_session(request, result.user)
            return Redirect(path="/admin", cookies=[device_cookie(result.user.id)])
        return await self._render("admin/login.html", theme_service, error=error, email=email[:150])

    @get("/login/verify")
    async def verify_page(
        self, request: Request[Any, Any, Any], theme_service: ThemeService
    ) -> Template | Redirect:
        """Render the second-factor form."""
        if pending_second_factor_user_id(request) is None:
            return Redirect(path="/admin/login")
        return await self._render("admin/login_verify.html", theme_service, error=None)

    @post("/login/verify")
    async def process_verify(
        self,
        request: Request[Any, Any, Any],
        auth_service: AuthService,
        theme_service: ThemeService,
        data: FormData,
    ) -> Template | Redirect:
        """Verify the TOTP or recovery code and issue the authenticated session."""
        user_id = pending_second_factor_user_id(request)
        if user_id is None:
            return Redirect(path="/admin/login")
        try:
            user = await auth_service.verify_second_factor(
                user_id, data.get("code", "")[:32], client_ip(request), device_claim(request)
            )
        except AuthenticationException as exc:
            # Wrong codes count towards the lockout (account for unknown, per device for trusted).
            return await self._render("admin/login_verify.html", theme_service, error=exc.message)
        store_authenticated_session(request, user)
        # This browser is now a trusted device: exempt from lockouts caused by others.
        return Redirect(path="/admin", cookies=[device_cookie(user.id)])

    @post("/logout")
    async def logout(self, request: Request[Any, Any, Any], auth_service: AuthService) -> Redirect:
        """Revoke all sessions of the user and clear the cookie."""
        user = await load_session_user(request)
        if user is not None:
            await auth_service.logout(user.id)
        request.clear_session()
        return Redirect(path="/admin/login")
