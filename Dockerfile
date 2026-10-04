# ==============================================================================
# Multi-Stage Dockerfile for Atemtherapie Application
# ==============================================================================

# Stage 1: Build stage with uv
FROM python:3.12-slim-bookworm AS builder

# Install curl and build tools if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv from official binary
COPY --from=ghcr.io/astral-sh/uv:0.5.8 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# Install project dependencies first (for docker layer caching)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

# Copy application source code
COPY src ./src
COPY README.md ./
RUN uv sync --frozen --no-dev

# ------------------------------------------------------------------------------
# Stage 2: Frontend assets – compile Tailwind CSS (standalone CLI, pinned + SHA256)
# ------------------------------------------------------------------------------
FROM debian:bookworm-slim AS assets
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
# Stage 3: Final Runtime Image
# ------------------------------------------------------------------------------
FROM python:3.12-slim-bookworm AS runner

# Create non-root user
RUN groupadd -r atem && useradd -r -g atem -d /app -s /sbin/nologin atem

# Install libpq for PostgreSQL runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder --chown=atem:atem /app/.venv /app/.venv
COPY --chown=atem:atem src /app/src
COPY --from=assets --chown=atem:atem /build/src/atem/presentation/static/css/app.css \
    /app/src/atem/presentation/static/css/app.css
COPY --chown=atem:atem pyproject.toml alembic.ini /app/
COPY --chown=atem:atem migrations /app/migrations
COPY --chown=atem:atem --chmod=0755 docker/entrypoint.sh /app/docker/entrypoint.sh

# Create persistent storage directories with non-root user permissions
RUN mkdir -p /app/storage/uploads && chown -R atem:atem /app/storage

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000 \
    HOST=0.0.0.0

USER atem

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Migrate + seed once, then run granian
ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["granian", "--interface", "asgi", "--factory", "--host", "0.0.0.0", "--port", "8000", "--workers", "2", "atem.presentation.app:create_app"]
