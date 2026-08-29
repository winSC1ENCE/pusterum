# Praxis für Atemtherapie – Webapplikation

[![CI](https://github.com/winSC1ENCE/atem/actions/workflows/ci.yml/badge.svg)](https://github.com/winSC1ENCE/atem/actions/workflows/ci.yml)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/release/python-3120/)
[![Litestar](https://img.shields.io/badge/framework-Litestar-gold.svg)](https://litestar.dev)
[![Code Style: Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Types: Mypy Strict](https://img.shields.io/badge/types-mypy%20strict-blue.svg)](https://mypy-lang.org/)
[![Architecture: Clean](https://img.shields.io/badge/architecture-Clean%20%2F%20Hexagonal-green.svg)](docs/adr/ADR-0001-tech-stack-and-architecture-blueprint.md)

Eine moderne, leichtgewichtige und sichere Single-Page-Webapplikation für eine Atemtherapie-Praxis (Komplementärtherapie OdA KT).

---

## 🏛️ Architektur & Dokumentation

- **Projekt-Playbook:** [`GEMINI.md`](GEMINI.md)
- **Architekturentscheidung & UML-Diagramme:** [`ADR-0001: Tech-Stack & Architecture Blueprint`](docs/adr/ADR-0001-tech-stack-and-architecture-blueprint.md)
- **ADR-Vorlage:** [`docs/adr/template.md`](docs/adr/template.md)
- **TDR / Micro-ADR Vorlage:** [`docs/tdr/template.md`](docs/tdr/template.md)

---

## 🚀 Quick Start (Lokal)

### 1. Voraussetzungen
- Python 3.12+
- Astral `uv` (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Docker & Docker Compose (optional für PostgreSQL)

### 2. Installation & Start

```bash
# Repository klonen & Abhängigkeiten synchronisieren
uv sync

# Pre-Commit Hooks installieren
uv run pre-commit install

# Umgebungsvariablen initialisieren
cp .env.example .env

# Server im Entwicklungsmodus starten
uv run granian --interface asgi --reload --host 127.0.0.1 --port 8000 atem.presentation.app:create_app
```

Öffnen Sie nun [http://localhost:8000](http://localhost:8000) im Browser.
Das Admin-Dashboard finden Sie unter [http://localhost:8000/admin](http://localhost:8000/admin).

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

```bash
# Docker Compose mit Caddy Reverse Proxy & automatischem TLS
docker compose -f docker-compose.prod.yml up -d --build
```
