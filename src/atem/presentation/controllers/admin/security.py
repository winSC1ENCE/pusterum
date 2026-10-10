"""Admin account security: password change, TOTP enrolment and recovery codes."""

from typing import Any

import segno
from litestar import Controller, Request, get, post
from litestar.response import Template
from markupsafe import Markup

from atem.application.dto.auth import UserResponseDTO
from atem.application.services.auth_service import AuthService
from atem.application.services.theme_service import ThemeService
from atem.domain.exceptions import ValidationException
from atem.infrastructure.config.settings import get_settings
from atem.presentation.controllers.admin.common import FormData
from atem.presentation.security.admin_auth import (
    ALLOW_PENDING_SECURITY_OPT,
    load_session_user,
    require_admin,
    store_authenticated_session,
)
from atem.presentation.security.device_cookie import device_cookie

SESSION_TOTP_SETUP_KEY = "totp_setup_secret"
PASSWORD_FIELD_MAX = 256


def _qr_svg(uri: str) -> Markup:
    """Render the otpauth:// URI as inline SVG (generated locally, no external service)."""
    svg = segno.make(uri, error="m").svg_inline(scale=5, dark="#1E293B", light="#FFFFFF")
    return Markup(svg)  # nosec B704 - SVG generated locally by segno, no user markup


class AdminSecurityController(Controller):
    """Security settings – reachable while 2FA setup / password change is still pending."""

    path = "/admin/security"
    guards = [require_admin]  # noqa: RUF012 - Litestar controller attribute
    opt = {ALLOW_PENDING_SECURITY_OPT: True}  # noqa: RUF012 - Litestar controller attribute
    include_in_schema = False

    async def _render(
        self,
        request: Request[Any, Any, Any],
        auth_service: AuthService,
        theme_service: ThemeService,
        **context: Any,
    ) -> Template:
        session_user = await load_session_user(request)
        assert session_user is not None  # guaranteed by require_admin
        user = await auth_service.get_user(session_user.id)
        theme = await theme_service.get_active_theme()
        return Template(
            template_name="admin/security.html",
            context={
                "user": request.session.get("user"),
                "account": user,
                "require_2fa": get_settings().require_2fa,
                "recovery_codes_left": await auth_service.count_recovery_codes(user.id),
                "theme": theme,
                "theme_css": theme_service.generate_css_variables(theme),
                "error": None,
                "success": None,
                **context,
            },
        )

    async def _current(self, request: Request[Any, Any, Any]) -> UserResponseDTO:
        user = await load_session_user(request)
        assert user is not None  # guaranteed by require_admin
        return user

    @get("")
    async def security_page(
        self,
        request: Request[Any, Any, Any],
        auth_service: AuthService,
        theme_service: ThemeService,
    ) -> Template:
        """Overview of password, 2FA status and recovery codes."""
        return await self._render(request, auth_service, theme_service)

    @post("/password")
    async def change_password(
        self,
        request: Request[Any, Any, Any],
        auth_service: AuthService,
        theme_service: ThemeService,
        data: FormData,
    ) -> Template:
        """Change the password (revokes sessions on all other devices)."""
        user = await self._current(request)
        new_password = data.get("new_password", "")[:PASSWORD_FIELD_MAX]
        if new_password != data.get("new_password_confirm", "")[:PASSWORD_FIELD_MAX]:
            return await self._render(
                request,
                auth_service,
                theme_service,
                error="Die neuen Passwörter stimmen nicht überein.",
            )
        try:
            updated = await auth_service.change_password(
                user.id, data.get("current_password", "")[:PASSWORD_FIELD_MAX], new_password
            )
        except ValidationException as exc:
            return await self._render(request, auth_service, theme_service, error=exc.message)
        store_authenticated_session(request, updated)
        response = await self._render(
            request, auth_service, theme_service, success="Passwort geändert."
        )
        # A password change revokes all trusted devices – except the current one.
        response.set_cookie(device_cookie(updated.id))
        return response

    @post("/totp/start")
    async def start_totp(
        self,
        request: Request[Any, Any, Any],
        auth_service: AuthService,
        theme_service: ThemeService,
    ) -> Template:
        """Generate a new secret and show the QR code for the authenticator app."""
        user = await self._current(request)
        setup = auth_service.start_totp_setup(user)
        request.session[SESSION_TOTP_SETUP_KEY] = setup.secret
        return await self._render(
            request,
            auth_service,
            theme_service,
            totp_setup={"secret": setup.secret, "qr": _qr_svg(setup.provisioning_uri)},
        )

    @post("/totp/confirm")
    async def confirm_totp(
        self,
        request: Request[Any, Any, Any],
        auth_service: AuthService,
        theme_service: ThemeService,
        data: FormData,
    ) -> Template:
        """Activate 2FA after the first valid code; show the recovery codes once."""
        user = await self._current(request)
        secret = request.session.get(SESSION_TOTP_SETUP_KEY)
        if not secret:
            return await self._render(
                request,
                auth_service,
                theme_service,
                error="Die Einrichtung ist abgelaufen. Bitte neu starten.",
            )
        try:
            codes = await auth_service.confirm_totp_setup(
                user.id, str(secret), data.get("code", "")[:16]
            )
        except ValidationException as exc:
            return await self._render(
                request,
                auth_service,
                theme_service,
                error=exc.message,
                totp_setup={
                    "secret": secret,
                    "qr": _qr_svg(auth_service.totp_provisioning_uri(user, str(secret))),
                },
            )
        store_authenticated_session(request, await auth_service.get_user(user.id))
        return await self._render(
            request,
            auth_service,
            theme_service,
            recovery_codes=codes,
            success="Zwei-Faktor-Anmeldung aktiviert.",
        )

    @post("/totp/disable")
    async def disable_totp(
        self,
        request: Request[Any, Any, Any],
        auth_service: AuthService,
        theme_service: ThemeService,
        data: FormData,
    ) -> Template:
        """Disable 2FA (not allowed where 2FA is mandatory)."""
        user = await self._current(request)
        if get_settings().require_2fa:
            return await self._render(
                request,
                auth_service,
                theme_service,
                error="Die Zwei-Faktor-Anmeldung ist in Produktion obligatorisch.",
            )
        try:
            updated = await auth_service.disable_totp(
                user.id, data.get("password", "")[:PASSWORD_FIELD_MAX]
            )
        except ValidationException as exc:
            return await self._render(request, auth_service, theme_service, error=exc.message)
        store_authenticated_session(request, updated)
        return await self._render(
            request, auth_service, theme_service, success="Zwei-Faktor-Anmeldung deaktiviert."
        )

    @post("/recovery-codes")
    async def regenerate_recovery_codes(
        self,
        request: Request[Any, Any, Any],
        auth_service: AuthService,
        theme_service: ThemeService,
        data: FormData,
    ) -> Template:
        """Replace all recovery codes and show the new ones once."""
        user = await self._current(request)
        try:
            codes = await auth_service.regenerate_recovery_codes(
                user.id, data.get("password", "")[:PASSWORD_FIELD_MAX]
            )
        except ValidationException as exc:
            return await self._render(request, auth_service, theme_service, error=exc.message)
        return await self._render(
            request,
            auth_service,
            theme_service,
            recovery_codes=codes,
            success="Neue Wiederherstellungscodes erstellt.",
        )
