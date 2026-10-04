#!/bin/sh
# Install the cron schedule and run crond in the foreground.
set -eu
: "${RESTIC_REPOSITORY:?RESTIC_REPOSITORY fehlt (backup.env)}"
: "${RESTIC_PASSWORD:?RESTIC_PASSWORD fehlt (backup.env)}"

# Repository is created on first start (idempotent).
restic cat config >/dev/null 2>&1 || restic init

# One-off commands (e.g. `docker compose run --rm backup restore.sh latest --yes`)
if [ "$#" -gt 0 ]; then
    exec "$@"
fi

{
    echo "${BACKUP_CRON} /usr/local/bin/backup.sh >> /proc/1/fd/1 2>&1"
    echo "${CHECK_CRON} /usr/local/bin/check.sh >> /proc/1/fd/1 2>&1"
} > /etc/crontabs/root

echo "[backup] Zeitplan: Backup '${BACKUP_CRON}', Prüfung '${CHECK_CRON}' (${TZ})"
exec crond -f -l 8
