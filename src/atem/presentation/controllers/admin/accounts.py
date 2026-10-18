"""Read-only overview of all admin accounts (tech-debt #16); changes go through the CLI."""

from typing import Any

from litestar import Controller, Request, get
from litestar.di import NamedDependency
from litestar.response import Template

from atem.application.services.auth_service import AuthService
from atem.application.services.theme_service import ThemeService
from atem.infrastructure.config.settings import get_settings
from atem.presentation.controllers.admin.common import admin_page
from atem.presentation.security.admin_auth import require_admin


class AdminAccountsController(Controller):
    """Who has access, with 2FA and last login - supports the half-yearly access review."""

    path = "/admin/accounts"
    guards = [require_admin]  # noqa: RUF012 - Litestar controller attribute
    include_in_schema = False

    @get("")
    async def accounts_page(
        self,
        request: Request[Any, Any, Any],
        auth_service: NamedDependency[AuthService],
        theme_service: NamedDependency[ThemeService],
    ) -> Template:
        """List every account with its security state."""
        return await admin_page(
            request,
            theme_service,
            "admin/accounts.html",
            accounts=await auth_service.list_accounts(),
            require_2fa=get_settings().require_2fa,
        )
