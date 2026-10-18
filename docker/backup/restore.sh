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

# The deletion log must survive the restore (ADR-0006, TDR-0013): the snapshot holds an older
# copy. Save the current entries, restore, merge them back; the app's entrypoint then deletes
# the logged messages again (reapply-deletions).
SAVED=/var/backup/deletion_log.before-restore.csv
COLUMNS="id, message_id, reason, email_hash, actor_id, created_at, updated_at"
rm -f "$SAVED"
if [ "$(psql -At -c "SELECT to_regclass('public.deletion_log')" 2>/dev/null)" = "deletion_log" ]; then
    echo "[restore] Löschprotokoll sichern ..."
    psql -v ON_ERROR_STOP=1 -c "\copy (SELECT $COLUMNS FROM deletion_log) TO '$SAVED' WITH CSV"
fi

echo "[restore] Datenbank ..."
pg_restore --clean --if-exists --no-owner --single-transaction \
    --dbname="$PGDATABASE" "$TARGET/var/backup/staging/atem_db.dump"

if [ -s "$SAVED" ]; then
    if [ "$(psql -At -c "SELECT to_regclass('public.deletion_log')")" = "deletion_log" ]; then
        echo "[restore] Löschprotokoll zusammenführen ..."
        psql -v ON_ERROR_STOP=1 <<SQL
CREATE TEMP TABLE saved_deletions (id uuid, message_id uuid, reason varchar(20),
    email_hash varchar(64), actor_id uuid, created_at timestamptz, updated_at timestamptz);
\copy saved_deletions FROM '$SAVED' WITH CSV
INSERT INTO deletion_log ($COLUMNS)
SELECT s.id, s.message_id, s.reason, s.email_hash, u.id, s.created_at, s.updated_at
  FROM saved_deletions s LEFT JOIN users u ON u.id = s.actor_id
ON CONFLICT (id) DO NOTHING;
SQL
        rm -f "$SAVED"
    else
        echo "[restore] WARNUNG: Snapshot ist älter als das Löschprotokoll. Gesicherte Einträge in"
        echo "          $SAVED - nach dem App-Start von Hand einspielen (Runbook 7.3)."
    fi
fi

if [ -d "$TARGET/media" ]; then
    echo "[restore] Medien ..."
    cp -a "$TARGET/media/." /media/
fi
echo "[restore] fertig – App wieder starten: docker compose up -d app"
