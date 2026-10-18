#!/bin/sh
# Container entrypoint: migrate and seed exactly once, then hand over to the web server.
# Concurrent starts are serialised by a PostgreSQL advisory lock in migrations/env.py.
set -eu

echo "[entrypoint] Datenbank-Migrationen (alembic upgrade head) ..."
alembic upgrade head

echo "[entrypoint] Standard-Inhalte ergänzen ..."
python -m atem.cli seed-content

# After a restore from backup, deleted messages may be back (ADR-0006); idempotent otherwise.
echo "[entrypoint] Löschprotokoll anwenden ..."
python -m atem.cli reapply-deletions

echo "[entrypoint] Starte: $*"
exec "$@"
