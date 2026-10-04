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
- **Architekturentscheidung & UML-Diagramme:** [`ADR-0001: Tech-Stack & Architecture Blueprint`](docs/adr/ADR-0001-tech-stack-and-architecture-blueprint.md)
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
uv run granian --interface asgi --factory --reload --host 127.0.0.1 --port 8000 atem.presentation.app:create_app
```

> **Tipp (Offline / Unterwegs):**
> Nutzen Sie `--no-sync`, um externe PyPI-Netzwerkprüfungen beim Start zu überspringen:
> ```bash
> uv run --no-sync granian --interface asgi --factory --reload --host 127.0.0.1 --port 8000 atem.presentation.app:create_app
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
uv run granian --interface asgi --factory --reload --host 127.0.0.1 --port 8000 atem.presentation.app:create_app
```

### 5. URLs & Endpunkte

- **Website:** [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Admin-Login:** [http://127.0.0.1:8000/admin/login](http://127.0.0.1:8000/admin/login) (Standard: `admin` / `admin-secure-init-pass-change-me`)
- **Health-Check:** [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)
- Ausführliche Kurzanleitung: siehe [`DEV_START.md`](DEV_START.md)

---

## 🧪 Tests & Qualitätssicherung

```bash
# Alle Tests mit Code Coverage ausführen
uv run pytest

# Linters & Typprüfung
uv run ruff check src tests
uv run ruff format --check src tests
uv run mypy src
uv run bandit -c pyproject.toml -r src
uv run deptry .
uv run vulture src
```

---

## 🚢 Deployment (Hosting Server)

Produktions-Domain: **https://www.pusterum.be** (`.be` = Bern). In `.env` `DOMAIN=www.pusterum.be` setzen; die Apex-Domain `pusterum.be` wird im `Caddyfile` permanent auf `www` umgeleitet. DNS: A/AAAA-Records für `pusterum.be` **und** `www.pusterum.be` auf den Cloud-Server.

```bash
# Docker Compose mit Caddy Reverse Proxy & automatischem TLS
docker compose -f docker-compose.prod.yml up -d --build

# Migrationen + Standard-Inhalte laufen automatisch im Container-Entrypoint.
# Einmalig: ersten Admin anlegen (Passwort wird interaktiv abgefragt)
docker compose -f docker-compose.prod.yml exec app python -m atem.cli create-admin \
  --username stephanie --email kontakt@pusterum.be
```

Produktions-`.env`: `cp config/env.production.example .env` und alle `CHANGE_ME` ersetzen – die App
verweigert den Start mit unsicheren Werten.
