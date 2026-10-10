"""Admin area controllers (all guarded by ``require_admin`` except the login flow)."""

from atem.presentation.controllers.admin.auth import AdminAuthController
from atem.presentation.controllers.admin.content import AdminContentController
from atem.presentation.controllers.admin.dashboard import AdminDashboardController
from atem.presentation.controllers.admin.design import AdminDesignController
from atem.presentation.controllers.admin.media import AdminMediaController
from atem.presentation.controllers.admin.security import AdminSecurityController
from atem.presentation.controllers.admin.services import AdminServicesController

ADMIN_CONTROLLERS = (
    AdminAuthController,
    AdminSecurityController,
    AdminDashboardController,
    AdminDesignController,
    AdminContentController,
    AdminMediaController,
    AdminServicesController,
)

__all__ = ["ADMIN_CONTROLLERS"]
