# ==============================================================================
# Multi-Stage Dockerfile – PUSTERUM web application
# Base images are pinned by digest directly in the FROM lines (Dependabot only updates those;
# manually: `docker buildx imagetools inspect <image:tag>`).
# ==============================================================================

# ------------------------------------------------------------------------------
# Stage 1: Python dependencies (uv)
# ------------------------------------------------------------------------------
FROM python:3.12-slim-bookworm@sha256:6a0e06f5ba0b373d051aabd3fffb9b873f27f9a2a3a14bcbe37dee6f0e3bbc70 AS builder

RUN apt-get update && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.12.23 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# Dependencies first (layer caching)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

COPY src ./src
COPY README.md ./
RUN uv sync --frozen --no-dev

# ------------------------------------------------------------------------------
# Stage 2: Frontend assets – compile Tailwind CSS (standalone CLI, pinned + SHA256)
# ------------------------------------------------------------------------------
FROM debian:bookworm-slim@sha256:7ff6ba31527b9e336162fa061746c366c4b2032f4d2cff2078bea43f78efe3f8 AS assets
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /build
COPY scripts/build-css.sh scripts/build-css.sh
COPY tailwind.config.js ./
COPY src/atem/presentation/assets src/atem/presentation/assets
COPY src/atem/presentation/templates src/atem/presentation/templates
COPY src/atem/presentation/static/js src/atem/presentation/static/js
RUN mkdir -p src/atem/presentation/static/css && sh scripts/build-css.sh

# ------------------------------------------------------------------------------
# Stage 3: Runtime image (non-root, no compilers, no curl)
# ------------------------------------------------------------------------------
FROM python:3.12-slim-bookworm@sha256:6a0e06f5ba0b373d051aabd3fffb9b873f27f9a2a3a14bcbe37dee6f0e3bbc70 AS runner

RUN groupadd -r atem && useradd -r -g atem -d /app -s /sbin/nologin atem

# Security updates on top of the pinned base image (CI scans the result with Trivy)
RUN apt-get update && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder --chown=atem:atem /app/.venv /app/.venv
COPY --chown=atem:atem src /app/src
COPY --from=assets --chown=atem:atem /build/src/atem/presentation/static/css/app.css \
    /app/src/atem/presentation/static/css/app.css
COPY --chown=atem:atem pyproject.toml alembic.ini /app/
COPY --chown=atem:atem migrations /app/migrations
COPY --chown=atem:atem --chmod=0755 docker/entrypoint.sh /app/docker/entrypoint.sh

# Persistent upload directory (named volume in production)
RUN mkdir -p /app/storage/uploads && chown -R atem:atem /app/storage

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

USER atem

EXPOSE 8000

# Health check without curl (smaller attack surface)
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"]

# Migrate + seed once (advisory lock), then run granian
ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["granian", "--interface", "asgi", "--factory", "--host", "0.0.0.0", "--port", "8000", \
     "--workers", "2", "--respawn-failed-workers", "atem.presentation.app:create_app"]
