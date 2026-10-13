#!/usr/bin/env bash
# Pull-based deployment (ADR-0005): CI moves the branch `production` only after a green run on
# `main`; this script (systemd timer, user `deploy`) fast-forwards the server checkout to it,
# rebuilds, checks /health/ready and rolls back to the previous commit if the check fails.
#
#   ops/deploy/pusterum-deploy.sh            # deploy if `production` has a new commit
#   ops/deploy/pusterum-deploy.sh --dry-run  # only report what would happen
#
# Wrapped in main() so bash has parsed the whole file before `git merge` replaces it on disk.
set -euo pipefail

main() {
    local repo_dir="${REPO_DIR:-/opt/pusterum}"
    local branch="${DEPLOY_BRANCH:-production}"
    local health_url="${HEALTH_URL:-https://www.pusterum.be/health/ready}"
    local state_dir="${STATE_DIR:-$HOME/.local/state/pusterum}"
    local dry_run=0
    [ "${1:-}" = "--dry-run" ] && dry_run=1

    exec 9>"${TMPDIR:-/tmp}/pusterum-deploy.lock"
    if ! flock -n 9; then
        echo "Ein anderes Deployment läuft bereits – übersprungen."
        return 0
    fi

    cd "$repo_dir"
    git fetch --quiet origin "$branch"
    local current target
    current="$(git rev-parse HEAD)"
    target="$(git rev-parse "origin/$branch")"

    if [ "$current" = "$target" ]; then
        return 0 # nothing new – stay quiet in the journal
    fi
    # A commit that already failed is not retried every 5 minutes (each try means downtime)
    if [ "$(cat "$state_dir/failed" 2>/dev/null)" = "$target" ]; then
        return 0
    fi
    if ! git diff --quiet || ! git diff --cached --quiet; then
        echo "ABBRUCH: lokale Änderungen im Checkout (git status) – bitte zuerst bereinigen."
        return 1
    fi
    if ! git merge-base --is-ancestor "$current" "$target"; then
        echo "ABBRUCH: origin/$branch ist kein Nachfolger von ${current:0:7} (kein Fast-Forward)."
        return 1
    fi

    echo "Neuer Stand: ${current:0:7} → ${target:0:7}"
    git log --oneline "$current..$target" | sed 's/^/  /'
    if [ "$dry_run" -eq 1 ]; then
        echo "Trockenlauf – nichts geändert."
        return 0
    fi

    git merge --quiet --ff-only "$target"
    if build_and_check "$health_url"; then
        echo "Deployment ${target:0:7} erfolgreich."
        docker image prune -f >/dev/null || true
        return 0
    fi

    echo "FEHLER: Health-Check fehlgeschlagen – Rollback auf ${current:0:7}."
    mkdir -p "$state_dir" && echo "$target" >"$state_dir/failed"
    git reset --quiet --hard "$current"
    if build_and_check "$health_url"; then
        echo "Rollback auf ${current:0:7} erfolgreich. ${target:0:7} wird erst mit einem neuen" \
            "Commit erneut versucht."
    else
        echo "KRITISCH: auch der Rollback ist nicht gesund – manuell eingreifen (Runbook 2)."
    fi
    return 1
}

build_and_check() {
    local url="$1"
    local retries="${HEALTH_RETRIES:-60}" delay="${HEALTH_DELAY:-5}" i
    # Explicit check: set -e is off inside `if build_and_check`, and a failed build would
    # otherwise leave the old container running and pass the health check.
    docker compose -f docker-compose.prod.yml up -d --build --remove-orphans || return 1
    for ((i = 1; i <= retries; i++)); do
        if curl -fsS --max-time 10 "$url" >/dev/null 2>&1; then
            return 0
        fi
        sleep "$delay"
    done
    return 1
}

main "$@"
exit $?
