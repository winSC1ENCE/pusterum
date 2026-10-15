# TDR-0008: Abhängigkeits- und Image-Updates mit Dependabot

* **Status:** accepted
* **Date:** 2026-10-14
* **Author:** Nicolas Mischler
* **Scope:** `.github/dependabot.yml`, `.github/workflows/ci.yml`, Dockerfiles, `docker-compose.prod.yml`

## Problem / Scope

Python-Pakete (`uv.lock`), GitHub Actions und Container-Basis-Images (Python, Debian, Caddy,
PostgreSQL) sind bewusst exakt gepinnt (Lockfile, Commit-SHA, Image-Digest). Ohne regelmässige
Aktualisierung veralten sie aber und erhalten keine Sicherheits-Fixes; neue CVEs fielen bisher nur
auf, wenn zufällig ein Push die CI auslöste. Zudem lief die CI noch mit Node-20-Actions, die
GitHub seit 2026-09-16 nicht mehr unterstützt.

## Technical Decision

* **Dependabot** (GitHub-eigen, keine zusätzliche App mit Schreibrechten) erstellt wöchentlich
  (Montag 06:00) Update-PRs nach `develop` für `uv`, `github-actions` und `docker`; Minor/Patch
  werden je Ökosystem gruppiert. Ausgenommen: PostgreSQL-Major (braucht Dump/Restore), Python-
  Minor/Major (Version in `pyproject.toml`), Caddy-Major.
* Dependabot liest Basis-Images nur aus wörtlichen `FROM image:tag@sha256:…`-Zeilen – die
  Dockerfiles pinnen deshalb direkt im `FROM` statt über `ARG`.
* PostgreSQL kommt an Stellen vor, die Dependabot nicht liest (`docker-compose.prod.yml`, CI-
  Service-Container). Quelle ist `docker/backup/Dockerfile`; `tests/test_image_pins.py` erkennt
  Abweichungen, `scripts/sync-image-pins.sh` gleicht sie auf dem Update-PR an.
* Caddy: Dependabot hebt nur das Laufzeit-Image (`caddy:X.Y-alpine`), nicht die Builder-Variante
  (`caddy:X.Y-builder-alpine`), die die tatsächlich kompilierte Caddy-Version bestimmt (erstmals
  bei 2.10 → 2.11 aufgefallen). Der Test verlangt dieselbe Version, das Skript zieht den Builder
  samt Digest nach.
* `uv` kennt bei Dependabot keine `versioning-strategy`: Updates heben immer auch die Untergrenze in
  `pyproject.toml` auf die gelockte Version. Gewollt (Untergrenze = getesteter Stand); die ersten
  PRs, die nur Untergrenzen nachziehen, werden gemergt.
* `.github/dependabot.yml` ohne YAML-Anker/-Aliase: gültiges YAML und Schema, aber der
  Dependabot-Parser lehnt sonst die ganze Datei ab («YAML aliases are not supported»).
  `tests/test_image_pins.py` prüft das.
* Die CI läuft zusätzlich **wöchentlich** (Montag, auf `main`) und manuell: pip-audit und der
  Trivy-Image-Scan melden neue CVEs auch ohne Push (GitHub benachrichtigt bei Fehlschlag).
* Alle Actions auf Node-24-Versionen gehoben (weiterhin per Commit-SHA gepinnt).

## Rationale & Trade-offs

* **Why this approach:** erstanbieterseitig, ohne Installation und ohne Token; Updates laufen wie
  Code durch PR, CI und das automatische Deployment (ADR-0005) – getestet und mit Rollback.
* **Alternatives evaluated:** Renovate (versteht `ARG`, Compose und Workflow-Services, aber eine
  Dritt-App mit Schreibrechten oder ein selbst betriebener Bot mit Token); automatisches
  Image-Pulling auf dem Server (ungetestete Stände in Produktion, umgeht die Pins).
* **Impact on existing code:** Dockerfiles ohne `ARG`-Pins (gleiche Digests); PostgreSQL-Updates
  brauchen einen Handgriff (`scripts/sync-image-pins.sh`) auf dem Dependabot-PR.
