#!/bin/sh
# Restore a snapshot (default: latest). Usage inside the backup container:
#   restore.sh [snapshot-id] [--yes]
# Restores media into /media (volume must be mounted read-write for this) and replaces the
# database contents. Stop the app container first:  docker compose stop app
set -eu
SNAPSHOT="${1:-latest}"
CONFIRM="${2:-}"
export PGHOST="${PGHOST:-db}" PGUSER="${POSTGRES_USER}" PGPASSWORD="${POSTGRES_PASSWORD}" \
       PGDATABASE="${POSTGRES_DB}"
TARGET=/var/backup/restore

if [ "$CONFIRM" != "--yes" ]; then
    echo "ACHTUNG: Datenbank '${PGDATABASE}' und Medien werden durch Snapshot '${SNAPSHOT}' ersetzt."
    echo "Erneut ausführen mit:  restore.sh ${SNAPSHOT} --yes"
    exit 1
fi

rm -rf "$TARGET" && mkdir -p "$TARGET"
restic restore "$SNAPSHOT" --host pusterum --target "$TARGET"

echo "[restore] Datenbank ..."
pg_restore --clean --if-exists --no-owner --single-transaction \
    --dbname="$PGDATABASE" "$TARGET/var/backup/staging/atem_db.dump"

if [ -d "$TARGET/media" ]; then
    echo "[restore] Medien ..."
    cp -a "$TARGET/media/." /media/
fi
echo "[restore] fertig – App wieder starten: docker compose up -d app"
