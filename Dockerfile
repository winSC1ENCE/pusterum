# ==============================================================================
# Multi-Stage Dockerfile – PUSTERUM web application
# Base images are pinned by digest (update via Renovate/Dependabot or manually with
# `docker buildx imagetools inspect <image:tag>`).
# ==============================================================================

ARG PYTHON_IMAGE=python:3.12-slim-bookworm@sha256:54c85f3c47607a77f32adec749d3c81d1348bf25833671f512b26a9b6d778cb3
ARG DEBIAN_IMAGE=debian:bookworm-slim@sha256:3783cc01769c7b2b1b83a5c5ad96c815348e28ed7da68e2e3687004faa906251

# ------------------------------------------------------------------------------
# Stage 1: Python dependencies (uv)
# ------------------------------------------------------------------------------
FROM ${PYTHON_IMAGE} AS builder

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
FROM ${DEBIAN_IMAGE} AS assets
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
FROM ${PYTHON_IMAGE} AS runner

RUN groupadd -r atem && useradd -r -g atem -d /app -s /sbin/nologin atem

RUN apt-get update && apt-get install -y --no-install-recommends libpq5 \
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
