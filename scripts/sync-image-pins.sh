#!/bin/sh
# Bring image pins in line that Dependabot cannot update itself (TDR-0008):
# - PostgreSQL: copy the pin from docker/backup/Dockerfile to docker-compose.prod.yml (db) and
#   the CI service containers.
# - Caddy: Dependabot bumps the runtime image (caddy:X.Y-alpine) but not the builder variant
#   (caddy:X.Y-builder-alpine), which decides the Caddy version that is actually compiled. The
#   builder is moved to the runtime's X.Y with its current digest (needs `docker buildx`).
# Usage, e.g. on a Dependabot PR branch whose CI fails in tests/test_image_pins.py:
#   scripts/sync-image-pins.sh && git commit -am "chore(deps): sync image pins" && git push
set -eu

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SOURCE="$ROOT/docker/backup/Dockerfile"
CADDY="$ROOT/docker/caddy/Dockerfile"

PIN="$(sed -n 's/^FROM \(postgres:[^ ]*@sha256:[0-9a-f]\{64\}\).*/\1/p' "$SOURCE" | head -n 1)"
if [ -z "$PIN" ]; then
    echo "Kein gepinntes postgres-Image in $SOURCE gefunden." >&2
    exit 1
fi
for target in "$ROOT/docker-compose.prod.yml" "$ROOT/.github/workflows/ci.yml"; do
    sed -i "s|image: postgres:[^ ]*@sha256:[0-9a-f]\{64\}|image: $PIN|" "$target"
done
echo "PostgreSQL-Pin übernommen: $PIN"

RUNTIME="$(sed -n 's/^FROM caddy:\([0-9.]*\)-alpine@.*/\1/p' "$CADDY" | head -n 1)"
BUILDER="$(sed -n 's/^FROM caddy:\([0-9.]*\)-builder-alpine@.*/\1/p' "$CADDY" | head -n 1)"
if [ -z "$RUNTIME" ] || [ -z "$BUILDER" ]; then
    echo "Caddy-Images in $CADDY nicht gefunden." >&2
    exit 1
fi
if [ "$RUNTIME" = "$BUILDER" ]; then
    echo "Caddy-Builder passt bereits: $BUILDER"
    exit 0
fi
DIGEST="$(docker buildx imagetools inspect "caddy:$RUNTIME-builder-alpine" --format '{{.Manifest.Digest}}')"
case "$DIGEST" in
sha256:*) ;;
*)
    echo "Digest für caddy:$RUNTIME-builder-alpine nicht ermittelbar: $DIGEST" >&2
    exit 1
    ;;
esac
sed -i "s|^FROM caddy:[0-9.]*-builder-alpine@sha256:[0-9a-f]\{64\}|FROM caddy:$RUNTIME-builder-alpine@$DIGEST|" "$CADDY"
echo "Caddy-Builder: $BUILDER → $RUNTIME ($DIGEST)"
