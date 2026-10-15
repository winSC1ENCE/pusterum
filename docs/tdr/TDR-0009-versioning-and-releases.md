# TDR-0009: Versionierung und Releases

* **Status:** accepted
* **Date:** 2026-10-14
* **Author:** Nicolas Mischler
* **Scope:** `pyproject.toml`, `uv.lock`, `CHANGELOG.md`, `scripts/release-notes.sh`, `.github/workflows/ci.yml`

## Problem / Scope

Bis 2026-10-14 stand die Version unverändert auf `0.1.0`, obwohl die Website live war und
regelmässig Releases (`develop` → `main` → automatisches Deployment, ADR-0005) ausgerollt wurden.
Es fehlten Tags, Releases und ein Changelog. Im Nachhinein liess sich deshalb kaum sagen, welcher
Stand wann live ging und was er enthielt.

## Technical Decision

* **Eine Quelle:** `[project].version` in `pyproject.toml`, nach Semantic Versioning:
  * MAJOR: inkompatible Änderung oder Umstellung mit Handarbeit im Betrieb;
  * MINOR: neue Funktion;
  * PATCH: Fehlerbehebung oder Update von Abhängigkeiten.

  `uv.lock` wird mit `uv lock` nachgeführt. Gestartet wird mit **1.0.0** (erste versionierte
  Ausgabe, live seit 2026-10-13).
* **`CHANGELOG.md`** nach Keep a Changelog, auf Deutsch:
  * Änderungen kommen laufend unter `## [Unreleased]`.
  * Der Release-PR `develop` → `main` erhöht die Version und benennt den Abschnitt in
    `## [x.y.z] – YYYY-MM-DD` um.
* **Prüfungen:**
  * `tests/test_versioning.py` (jede CI) prüft, dass pyproject, Lockfile und die neueste
    Changelog-Version übereinstimmen.
  * Ein Schritt im Job `code-quality` bricht PRs nach `main` ab, wenn der Tag `v<version>` schon
    existiert oder wenn der Changelog-Abschnitt fehlt. Ein Release ohne neue Version ist damit nicht
    möglich. Da der Schritt in einem bestehenden Pflicht-Check läuft, muss das Ruleset nicht angepasst
    werden.
* **Tag und Release:**
  * Erstellt der Job `promote` nach grüner CI auf `main`, direkt nach dem Verschieben von
    `production`: `gh release create v<version> --target <commit>`.
  * Die Release-Notes sind der Changelog-Abschnitt (`scripts/release-notes.sh`).
  * Der Tag zeigt damit genau auf den Commit, den der Server deployt.
  * Existiert der Tag schon, gibt es nur eine Warnung.
* **Quell-Branches für `main`:** nur `develop` (Release) und `hotfix/*` aus diesem Repo. Das
  prüft der Schritt «Source branch allowed for main» im Pflicht-Check. Rulesets können den
  Quell-Branch nicht einschränken. Das Ruleset hat keine Bypass-Liste, also gilt das auch für
  Admins.
* **Dependabot-PRs** gehen nach `develop` und brauchen keinen eigenen Eintrag. Der nächste Release
  fasst sie als PATCH oder MINOR zusammen («Abhängigkeiten aktualisiert»).

## Rationale & Trade-offs

* **Why this approach:**
  * Die Version steht dort, wo Python-Werkzeuge sie ohnehin erwarten.
  * Tags entstehen erst nach grüner CI und nur auf dem freigegebenen Commit.
  * Es braucht weder ein zusätzliches Werkzeug noch ein Token. Der `GITHUB_TOKEN` des Jobs `promote`
    hat bereits `contents: write`.
* **Alternatives evaluated:**
  * Version aus Git-Tags ableiten (z. B. `setuptools-scm`, `hatch-vcs`): Docker-Builds ohne
    `.git` bräuchten Workarounds.
  * release-please oder semantic-release, die Version und Changelog aus Conventional Commits
    erzeugen: ein zusätzlicher Bot mit eigenen PRs; für ein Ein-Personen-Projekt mit Release-PRs
    unnötig schwer.
  * Tags von Hand: wurden bisher vergessen.
* **Impact on existing code:**
  * Jeder Release-PR braucht einen Versionssprung und einen Changelog-Eintrag. Die CI erzwingt beides.
  * Ältere Stände bis 2026-10-13 tragen keine Tags.
