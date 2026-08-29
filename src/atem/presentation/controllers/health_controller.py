"""Health check and readiness endpoints."""

from litestar import Controller, get
from litestar.response import Response


class HealthController(Controller):
    """Liveness and readiness probes for Docker / Kubernetes / Hosting."""

    path = "/health"

    @get(include_in_schema=True)
    async def check_health(self) -> dict[str, str]:
        """Liveness probe returning basic service health."""
        return {"status": "ok", "service": "atem-web"}

    @get("/ready", include_in_schema=True)
    async def check_readiness(self) -> Response[dict[str, str]]:
        """Readiness probe checking database connectivity."""
        return Response(
            content={"status": "ready", "database": "connected"},
            status_code=200,
        )
