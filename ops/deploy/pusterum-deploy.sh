#!/usr/bin/env bash
# Pull-based deployment (ADR-0005): CI moves the branch `production` only after a green run on
# `main`; this script (systemd timer, user `deploy`) fast-forwards the server checkout to it,
# rebuilds, checks /health/ready and rolls back to the previous commit if the check fails.
# Every run also checks the live site and reports the result to a healthcheck service
# (DEPLOY_PING_URL in deploy.env, optional): `<url>` = ok, `<url>/fail` = alarm; missing pings
# alarm as well (server down, timer stopped).
#
#   ops/deploy/pusterum-deploy.sh            # deploy if `production` has a new commit
#   ops/deploy/pusterum-deploy.sh --dry-run  # only report what would happen (no ping)
#
# Wrapped in main() so bash has parsed the whole file before `git merge` replaces it on disk.
set -euo pipefail

ping_url=""
last_msg=""
ping_mode="" # "" = by exit code, "fail" = report failure despite exit 0, "skip" = no ping

log() {
    last_msg="$*"
    echo "$*"
}

# shellcheck disable=SC2329 # invoked by `trap report EXIT`
report() {
    local rc=$? path=""
    [ -n "$ping_url" ] && [ "$ping_mode" != "skip" ] || return "$rc"
    if [ "$rc" -ne 0 ] || [ "$ping_mode" = "fail" ]; then
        path="/fail"
        case "$last_msg" in
        FEHLER* | ABBRUCH* | KRITISCH* | Deployment*) ;;
        *) last_msg="Unerwarteter Fehler (Exit $rc) nach «${last_msg}» – journalctl -u pusterum-deploy" ;;
        esac
    fi
    curl -fsS -m 10 --retry 3 --data-raw "${last_msg:-ok}" "$ping_url$path" >/dev/null 2>&1 || true
    return "$rc"
}

main() {
    local repo_dir="${REPO_DIR:-/opt/pusterum}"
    local branch="${DEPLOY_BRANCH:-production}"
    local health_url="${HEALTH_URL:-https://www.pusterum.be/health/ready}"
    local state_dir="${STATE_DIR:-$HOME/.local/state/pusterum}"
    local dry_run=0
    [ "${1:-}" = "--dry-run" ] && dry_run=1 && ping_mode="skip"

    # Only this one line is read – deploy.env is never executed as shell code
    ping_url="${DEPLOY_PING_URL:-}"
    if [ -z "$ping_url" ] && [ -f "$repo_dir/deploy.env" ]; then
        ping_url="$(sed -n 's/^DEPLOY_PING_URL=//p' "$repo_dir/deploy.env" | tail -n 1)"
    fi
    trap report EXIT

    exec 9>"${TMPDIR:-/tmp}/pusterum-deploy.lock"
    if ! flock -n 9; then
        ping_mode="skip" # the running deployment reports
        log "Ein anderes Deployment läuft bereits – übersprungen."
        return 0
    fi

    cd "$repo_dir"
    git fetch --quiet origin "$branch"
    local current target
    current="$(git rev-parse HEAD)"
    target="$(git rev-parse "origin/$branch")"

    if [ "$current" = "$target" ]; then
        check_live "$health_url" || return 1 # nothing new – quiet in the journal unless down
        return 0
    fi
    # A commit that already failed is not retried every 5 minutes (each try means downtime);
    # the alarm stays on until a new commit deploys
    if [ "$(cat "$state_dir/failed" 2>/dev/null)" = "$target" ]; then
        check_live "$health_url" || return 1
        ping_mode="${ping_mode:-fail}"
        last_msg="Deployment ${target:0:7} fehlgeschlagen, ${current:0:7} läuft – wartet auf einen neuen Commit."
        return 0
    fi
    if ! git diff --quiet || ! git diff --cached --quiet; then
        log "ABBRUCH: lokale Änderungen im Checkout (git status) – bitte zuerst bereinigen."
        return 1
    fi
    if ! git merge-base --is-ancestor "$current" "$target"; then
        log "ABBRUCH: origin/$branch ist kein Nachfolger von ${current:0:7} (kein Fast-Forward)."
        return 1
    fi

    log "Neuer Stand: ${current:0:7} → ${target:0:7}"
    git log --oneline "$current..$target" | sed 's/^/  /'
    if [ "$dry_run" -eq 1 ]; then
        log "Trockenlauf – nichts geändert."
        return 0
    fi

    git merge --quiet --ff-only "$target"
    if build_and_check "$health_url"; then
        log "Deployment ${target:0:7} erfolgreich."
        docker image prune -f >/dev/null || true
        return 0
    fi

    log "FEHLER: Health-Check fehlgeschlagen – Rollback auf ${current:0:7}."
    mkdir -p "$state_dir" && echo "$target" >"$state_dir/failed"
    git reset --quiet --hard "$current"
    if build_and_check "$health_url"; then
        log "Deployment ${target:0:7} fehlgeschlagen, Rollback auf ${current:0:7} erfolgreich." \
            "${target:0:7} wird erst mit einem neuen Commit erneut versucht."
    else
        log "KRITISCH: auch der Rollback ist nicht gesund – manuell eingreifen (Runbook 2)."
    fi
    return 1
}

check_live() {
    if curl -fsS --max-time 10 "$1" >/dev/null 2>&1; then
        return 0
    fi
    log "FEHLER: Website antwortet nicht ($1)."
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
