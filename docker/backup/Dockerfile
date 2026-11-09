# Backup sidecar: pg_dump (matching PostgreSQL major version) + restic → SFTP backup target.
FROM postgres:16-alpine@sha256:aa6cb33cf4c19c765cefcf48d96176258800870a9a1e930ad126200f9d825139

RUN apk add --no-cache restic openssh-client curl tzdata

COPY --chmod=0755 backup.sh restore.sh check.sh entrypoint.sh /usr/local/bin/

ENV TZ=Europe/Zurich \
    BACKUP_CRON="30 2 * * *" \
    CHECK_CRON="15 4 * * 0" \
    RESTIC_CACHE_DIR=/var/cache/restic

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
