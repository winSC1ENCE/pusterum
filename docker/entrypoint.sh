#!/bin/sh
# Container entrypoint: migrate and seed exactly once, then hand over to the web server.
# Concurrent starts are serialised by a PostgreSQL advisory lock in migrations/env.py.
set -eu

echo "[entrypoint] Datenbank-Migrationen (alembic upgrade head) ..."
alembic upgrade head

echo "[entrypoint] Standard-Inhalte ergänzen ..."
python -m atem.cli seed-content

echo "[entrypoint] Starte: $*"
exec "$@"
