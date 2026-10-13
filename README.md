# PUSTERUM – Praxis für Atem- und Körpertherapie (Webapplikation)

[![CI](https://github.com/winSC1ENCE/atem/actions/workflows/ci.yml/badge.svg)](https://github.com/winSC1ENCE/atem/actions/workflows/ci.yml)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/release/python-3120/)
[![Litestar](https://img.shields.io/badge/framework-Litestar-gold.svg)](https://litestar.dev)
[![Code Style: Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Types: Mypy Strict](https://img.shields.io/badge/types-mypy%20strict-blue.svg)](https://mypy-lang.org/)
[![Architecture: Clean](https://img.shields.io/badge/architecture-Clean%20%2F%20Hexagonal-green.svg)](docs/adr/ADR-0001-tech-stack-and-architecture-blueprint.md)

Eine moderne, leichtgewichtige und sichere Single-Page-Webapplikation für **PUSTERUM** – Praxis für Atem- und Körpertherapie (dän. *pusterum* = „Raum zum Atmen“).

---

## 🏛️ Architektur & Dokumentation

- **Projekt-Playbook:** [`GEMINI.md`](GEMINI.md) · Claude Code: [`CLAUDE.md`](CLAUDE.md)
- **Architektur-Übersicht (Klassen- & Sequenzdiagramme, alle ADRs/TDRs):** [`docs/architecture/`](docs/architecture/README.md)
- **Tech-Stack:** [`ADR-0001`](docs/adr/ADR-0001-tech-stack-and-architecture-blueprint.md) · **Security-Architektur:** [`ADR-0004`](docs/adr/ADR-0004-security-architecture.md)
- **Betrieb (Deployment, Backups, Restore, Notfälle):** [`docs/ops/runbook.md`](docs/ops/runbook.md)
- **ADR-Vorlage:** [`docs/adr/template.md`](docs/adr/template.md)
- **TDR / Micro-ADR Vorlage:** [`docs/tdr/template.md`](docs/tdr/template.md)

---

## 🚀 Quick Start (Lokal)

### 1. Voraussetzungen
- Python 3.12+
- Astral `uv` (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Docker & Docker Compose (optional für PostgreSQL)

### 2. Installation & Setup

```bash
# Repository klonen & Abhängigkeiten synchronisieren
uv sync

# Pre-Commit Hooks installieren
uv run pre-commit install

# Umgebungsvariablen initialisieren (Entwicklung)
cp config/env.development.example .env

# CSS kompilieren (Tailwind Standalone-CLI, kein Node.js nötig)
scripts/build-css.sh
```

### 3. Datenbank starten & migrieren

Starten Sie nur den PostgreSQL-Container:

```bash
# PostgreSQL im Hintergrund starten
docker compose up -d db

# Datenbank-Migrationen anwenden
uv run alembic upgrade head   # Schema + Datenmigrationen (Pflicht, kein create_all mehr)
```

### 4. Lokalen Entwicklungs-Server starten

> **Wichtig:** Da `create_app` eine Application-Factory ist, muss beim Granian-Aufruf das Flag `--factory` übergeben werden.

```bash
uv run granian --interface asgi --factory --reload --reload-paths src --host 127.0.0.1 --port 8000 atem.presentation.app:create_app
```

> **Tipp (Offline / Unterwegs):**
> Nutzen Sie `--no-sync`, um externe PyPI-Netzwerkprüfungen beim Start zu überspringen:
> ```bash
> uv run --no-sync granian --interface asgi --factory --reload --reload-paths src --host 127.0.0.1 --port 8000 atem.presentation.app:create_app
> ```

### ⚠️ Hinweis: Port-Konflikte (Docker vs. Lokaler Server)

Falls zuvor der gesamte Compose-Stack via `docker compose up -d` gestartet wurde, belegt der Container `atem_app` bereits Port 8000. Stoppen Sie in diesem Fall den App-Container, damit der Port für Ihren lokalen Granian-Server frei wird:

```bash
# App-Container stoppen (gibt Port 8000 frei):
docker compose stop app
# oder direkt über den Containernamen:
docker stop atem_app

# Sicherstellen, dass die Datenbank weiterhin läuft:
docker compose up -d db

# Danach lokalen Granian-Server wie gewohnt starten:
uv run granian --interface asgi --factory --reload --reload-paths src --host 127.0.0.1 --port 8000 atem.presentation.app:create_app
```

### 5. URLs & Endpunkte

- **Website:** [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Admin-Login:** [http://127.0.0.1:8000/admin/login](http://127.0.0.1:8000/admin/login) (nur development: `entwicklung@pusterum.be` / `admin-secure-init-pass-change-me`; 2FA optional unter `/admin/security`)
- **Health-Check:** [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)
- Ausführliche Kurzanleitung: siehe [`DEV_START.md`](DEV_START.md)

---

## 🧪 Tests & Qualitätssicherung

```bash
# Unit-/Integrationstests mit Coverage (SQLite, Schwelle 90 %)
uv run pytest

# Dieselbe Suite gegen PostgreSQL (wie in CI)
TEST_DATABASE_URL=postgresql+asyncpg://atem:<pw>@localhost:5432/atem_test uv run pytest

# Browser-E2E (Playwright; CSP-Verletzungen und JS-Fehler lassen Tests scheitern)
uv run playwright install chromium   # einmalig
uv run pytest tests_e2e --no-cov

# Alle Gates (ruff, mypy strict, bandit, deptry, vulture, gitleaks, …)
uv run pre-commit run --all-files
```

Die CI (`.github/workflows/ci.yml`) führt zusätzlich `pip-audit`, Lizenzprüfung, Alembic-Up/Down-Checks
gegen PostgreSQL, einen Trivy-Image-Scan und einen Smoke-Start im Produktionsmodus aus.

---

## 🚢 Deployment (Cloud-Server)

Produktions-Domain: **https://www.pusterum.be** (`.be` = Bern). In `.env` `DOMAIN=www.pusterum.be` setzen; die Apex-Domain `pusterum.be` wird im `Caddyfile` permanent auf `www` umgeleitet. DNS: A/AAAA-Records für `pusterum.be` **und** `www.pusterum.be` auf den Server.

```bash
# Docker Compose mit Caddy Reverse Proxy & automatischem TLS
docker compose -f docker-compose.prod.yml up -d --build

# Migrationen + Standard-Inhalte laufen automatisch im Container-Entrypoint.
# Einmalig: ersten Admin anlegen (Passwort wird interaktiv abgefragt)
docker compose -f docker-compose.prod.yml exec app python -m atem.cli create-admin \
  --email vorname.name@example.ch   # persönliche Adresse = Login
```

Produktions-Secrets: `cp config/env.production.example .env`, `cp config/db.env.production.example db.env`,
`cp config/backup.env.production.example backup.env` und alle `CHANGE_ME` ersetzen – die App verweigert den
Start mit unsicheren Werten. Beim ersten Login wird die Zwei-Faktor-Anmeldung (TOTP) erzwungen.
Server-Härtung (`ops/server/cloud-init.yaml`), Backups/Restore und Notfälle: [`docs/ops/runbook.md`](docs/ops/runbook.md).

**Updates** deployen automatisch: Pull Request `develop` → `main` (Merge-Commit) → grüne CI → der Job
«Promote to production» setzt den Branch `production` → ein systemd-Timer auf dem Server übernimmt ihn innerhalb
von ~5 Minuten, prüft `/health/ready` und rollt bei Fehlern zurück (`ops/deploy/`, [ADR-0005](docs/adr/ADR-0005-continuous-deployment.md)).

> **Hinweis:** `docs/ops/runbook.md` ist mit [git-crypt](https://github.com/AGWA/git-crypt) verschlüsselt und
> auf GitHub nur als Binärdatei sichtbar. Mit dem Schlüssel entsperren: `git-crypt unlock /pfad/zum/pusterum.key`.
