#!/bin/sh
# Compile Tailwind CSS (standalone CLI, no Node.js). Usage:
#   scripts/build-css.sh          # one-off minified build
#   scripts/build-css.sh --watch  # rebuild on template changes (development)
set -eu

TAILWIND_VERSION="3.4.17"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TOOLS="$ROOT/.tools"
CLI="$TOOLS/tailwindcss-$TAILWIND_VERSION"

case "$(uname -s)-$(uname -m)" in
    Linux-x86_64) ASSET="tailwindcss-linux-x64"; SHA256="7d24f7fa191d2193b78cd5f5a42a6093e14409521908529f42d80b11fde1f1d4" ;;
    Linux-aarch64) ASSET="tailwindcss-linux-arm64"; SHA256="69b1378b8133192d7d2feb12a116fa12d035594f58db3eff215879e4ad8cf39b" ;;
    Darwin-arm64) ASSET="tailwindcss-macos-arm64"; SHA256="" ;;
    Darwin-x86_64) ASSET="tailwindcss-macos-x64"; SHA256="" ;;
    *) echo "Nicht unterstützte Plattform: $(uname -s)-$(uname -m)" >&2; exit 1 ;;
esac

if [ ! -x "$CLI" ]; then
    mkdir -p "$TOOLS"
    echo "Lade Tailwind CLI v$TAILWIND_VERSION ($ASSET) ..."
    curl -sfL "https://github.com/tailwindlabs/tailwindcss/releases/download/v$TAILWIND_VERSION/$ASSET" -o "$CLI.tmp"
    if [ -n "$SHA256" ]; then
        echo "$SHA256  $CLI.tmp" | sha256sum -c - >/dev/null
    fi
    mv "$CLI.tmp" "$CLI"
    chmod +x "$CLI"
fi

cd "$ROOT"
exec "$CLI" \
    --config tailwind.config.js \
    --input src/atem/presentation/assets/tailwind.input.css \
    --output src/atem/presentation/static/css/app.css \
    --minify "$@"
