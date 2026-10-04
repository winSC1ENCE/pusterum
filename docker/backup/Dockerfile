# Backup sidecar: pg_dump (matching PostgreSQL major version) + restic → SFTP-Backup-Speicher.
ARG POSTGRES_IMAGE=postgres:16-alpine@sha256:721873c34ceb9f8d8fc265984940dc982404c105f19ad51be9fdc5970a6080ea
FROM ${POSTGRES_IMAGE}

RUN apk add --no-cache restic openssh-client curl tzdata

COPY --chmod=0755 backup.sh restore.sh check.sh entrypoint.sh /usr/local/bin/

ENV TZ=Europe/Zurich \
    BACKUP_CRON="30 2 * * *" \
    CHECK_CRON="15 4 * * 0" \
    RESTIC_CACHE_DIR=/var/cache/restic

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
