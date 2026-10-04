#!/bin/sh
# Daily backup: consistent PostgreSQL dump + uploaded media → encrypted restic repository.
set -eu
export PGHOST="${PGHOST:-db}" PGUSER="${POSTGRES_USER}" PGPASSWORD="${POSTGRES_PASSWORD}" \
       PGDATABASE="${POSTGRES_DB}"
STAGING=/var/backup/staging
mkdir -p "$STAGING"
ping_url() { [ -n "${HEALTHCHECK_PING_URL:-}" ] && curl -fsS -m 10 --retry 3 "$1" >/dev/null || true; }

ping_url "${HEALTHCHECK_PING_URL:-}/start"
trap 'ping_url "${HEALTHCHECK_PING_URL:-}/fail"' EXIT

echo "[backup] $(date -Iseconds) pg_dump ..."
pg_dump --format=custom --no-owner --file="$STAGING/atem_db.dump"

echo "[backup] restic backup (Datenbank + Medien) ..."
restic backup --host pusterum --tag daily "$STAGING" /media

echo "[backup] Aufbewahrung: 7 täglich, 4 wöchentlich, 6 monatlich"
restic forget --host pusterum --keep-daily 7 --keep-weekly 4 --keep-monthly 6 --prune

rm -f "$STAGING/atem_db.dump"
trap - EXIT
ping_url "${HEALTHCHECK_PING_URL:-}"
echo "[backup] $(date -Iseconds) fertig"
