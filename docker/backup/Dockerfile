# Backup sidecar: pg_dump (matching PostgreSQL major version) + restic → SFTP backup target.
FROM postgres:16-alpine@sha256:0cefaabd882e42bcb2a2f3dc56d3ce4770560ba62fd7f197f1a2e008fd5731ab

RUN apk add --no-cache restic openssh-client curl tzdata

COPY --chmod=0755 backup.sh restore.sh check.sh entrypoint.sh /usr/local/bin/

ENV TZ=Europe/Zurich \
    BACKUP_CRON="30 2 * * *" \
    CHECK_CRON="15 4 * * 0" \
    RESTIC_CACHE_DIR=/var/cache/restic

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
