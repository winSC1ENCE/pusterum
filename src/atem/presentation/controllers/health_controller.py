"""Health check and readiness endpoints."""

import structlog
from litestar import Controller, get
from litestar.response import Response
from litestar.status_codes import HTTP_200_OK, HTTP_503_SERVICE_UNAVAILABLE
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)


class HealthController(Controller):
    """Liveness and readiness probes (container health check, uptime monitoring)."""

    path = "/health"
    include_in_schema = False

    @get(cache=False)
    async def check_health(self) -> dict[str, str]:
        """Liveness probe – the process is up (no dependencies checked)."""
        return {"status": "ok"}

    @get("/ready", cache=False)
    async def check_readiness(self, db_session: AsyncSession) -> Response[dict[str, str]]:
        """Readiness probe – verifies the database connection with ``SELECT 1``."""
        try:
            await db_session.execute(text("SELECT 1"))
        except (SQLAlchemyError, OSError):
            logger.exception("readiness_check_failed")
            return Response(
                content={"status": "unavailable", "database": "error"},
                status_code=HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response(content={"status": "ready", "database": "ok"}, status_code=HTTP_200_OK)
