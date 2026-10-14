#!/bin/sh
# Release helper (TDR-0009), used by CI and by hand:
#   scripts/release-notes.sh --version   # project version from pyproject.toml, e.g. 1.0.0
#   scripts/release-notes.sh [VERSION]   # CHANGELOG.md section of VERSION (default: project
#                                        # version) without its heading; exit 1 if missing or empty
set -eu

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

project_version() {
    python3 -c 'import sys, tomllib; print(tomllib.load(open(sys.argv[1], "rb"))["project"]["version"])' \
        "$ROOT/pyproject.toml"
}

if [ "${1:-}" = "--version" ]; then
    project_version
    exit 0
fi

VERSION="${1:-$(project_version)}"
NOTES="$(awk -v heading="## [$VERSION]" '
    /^## \[/ { if (found) exit; found = (index($0, heading) == 1); next }
    found
' "$ROOT/CHANGELOG.md")"

if [ -z "$(printf '%s' "$NOTES" | tr -d '[:space:]')" ]; then
    echo "CHANGELOG.md: kein Abschnitt «## [$VERSION] – Datum» mit Inhalt gefunden." >&2
    exit 1
fi
printf '%s\n' "$NOTES" | sed -e '/./,$!d' # without leading blank lines
