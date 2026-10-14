#!/bin/sh
# Copy the PostgreSQL image pin from docker/backup/Dockerfile (updated by Dependabot) to the
# places Dependabot cannot update: docker-compose.prod.yml (db) and the CI service containers.
# Usage, e.g. on a Dependabot PR branch whose CI fails in tests/test_image_pins.py:
#   scripts/sync-image-pins.sh && git commit -am "chore(deps): sync postgres image pins" && git push
set -eu

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SOURCE="$ROOT/docker/backup/Dockerfile"

PIN="$(sed -n 's/^FROM \(postgres:[^ ]*@sha256:[0-9a-f]\{64\}\).*/\1/p' "$SOURCE" | head -n 1)"
if [ -z "$PIN" ]; then
    echo "Kein gepinntes postgres-Image in $SOURCE gefunden." >&2
    exit 1
fi

for target in "$ROOT/docker-compose.prod.yml" "$ROOT/.github/workflows/ci.yml"; do
    sed -i "s|image: postgres:[^ ]*@sha256:[0-9a-f]\{64\}|image: $PIN|" "$target"
done
echo "PostgreSQL-Pin übernommen: $PIN"
