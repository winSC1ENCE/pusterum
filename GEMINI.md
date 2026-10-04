# PROJECT PLAYBOOK: PUSTERUM WEBAPPLIKATION

> **Projektziel:** Hochwertige, performante und sichere Single-Page Webapplikation für **PUSTERUM** – Praxis für Atem- und Körpertherapie mit integrierter Inhalts- und Anfragenverwaltung.

---

## 1. Architekturübersicht (Clean Architecture & OOP / ABC)

Das Projekt folgt strikt den Prinzipien der **Clean Architecture / Ports & Adapters**:

```
src/atem/
├── domain/                  # Reine Geschäftslogik & Entitäten (Framework-agnostisch)
│   ├── exceptions.py        # Domänen-spezifische Ausnahmen
│   ├── models/              # Dataclass/Entity-Modelle (TherapistProfile, ServiceOffering, ContactMessage, User)
│   └── interfaces/          # Abstract Base Classes (ABCs / Ports): IProfileRepository, IContactRepository, etc.
│
├── application/             # Use Cases & Orchestrierung
│   ├── dto/                 # Pydantic DTOs & Validierungsschemata
│   └── services/            # Anwendungsdienste (ProfileService, ContactService, AuthService)
│
├── infrastructure/          # Externe Adapter & Implementierungen
│   ├── config/              # Pydantic Settings & Umgebungs-Konfiguration
│   ├── logging/             # Structlog Logging-Setup (JSON in Prod, Farbe in Dev)
│   ├── database/            # SQLAlchemy 2.0 Async & Asyncpg
│   │   ├── base.py          # Declarative Base & Mixins
│   │   ├── session.py       # Async Engine & Sessionmaker
│   │   ├── models/          # ORM-Tabellendefinitionen
│   │   └── repositories/    # Konkrete SQLAlchemy Repository-Implementierungen
│   ├── email/               # E-Mail Adapter (SmtpEmailService, MockEmailService)
│   └── security/            # Argon2id Passwort-Hashing
│
└── presentation/            # Web-Auslieferung & API
    ├── app.py               # Litestar Application Factory & Lifespan Hooks
    ├── controllers/         # Litestar Controller (Public, Admin, Health)
    ├── templates/           # Jinja2 Templates (HTML5, HTMX, Alpine.js, Tailwind CSS)
    └── static/              # Statische Ressourcen (CSS, JS, Bilder)
```

---

## 2. Tech-Stack Matrix

| Komponente | Technologie / Tool | Zweck |
| :--- | :--- | :--- |
| **Runtime & Language** | Python 3.12+ | Moderne Async Python Basis |
| **Package Manager** | Astral `uv` | Blitzschnelle, deterministische Paketverwaltung via `pyproject.toml` |
| **Web Framework** | `Litestar` | Stark typisiertes ASGI-Framework mit Dependency Injection & OOP |
| **ORM / Database** | `SQLAlchemy 2.0 Async` + `asyncpg` + `PostgreSQL 16` | Robustes Datenmodell mit sauberer Interface-Abstraktion |
| **Migrations** | `Alembic` | Asynchrone Datenbankschema-Migrationen |
| **Frontend UI** | `Jinja2` + `HTMX` + `Alpine.js` + `Tailwind CSS` | Schnelles Single-Page-Erlebnis ohne Node.js-Overhead |
| **Logging** | `structlog` | Strukturierte JSON-Logs für Produktion, lesbare Farbkonsole lokal |
| **Passwort-Sicherheit** | `Argon2id` (`argon2-cffi`) | Aktueller State-of-the-Art Standard für Passwort-Hashing |
| **Reverse Proxy** | `Caddy 2` | Automatisches HTTPS (Let's Encrypt), HTTP/3, Security Headers |
| **Container** | Docker & Docker Compose | Lokales Development & Produktionsbetrieb |

---

## 3. Qualitäts-, Sicherheits- & Linter-Gates

Das Projekt unterliegt strengen Qualitätsprüfungen. Alle Prüfungen sind in `.pre-commit-config.yaml` und GitHub Actions CI (`.github/workflows/ci.yml`) integriert:

```bash
# 1. Linting & Formatting
uv run ruff check src tests
uv run ruff format --check src tests

# 2. Strikte statische Typisierung (keine ungetypten Signaturen)
uv run mypy src

# 3. Sicherheitsprüfung des Codes
uv run bandit -c pyproject.toml -r src

# 4. Abhängigkeiten-Integrität (ungewollte/fehlende Abhängigkeiten)
uv run deptry .

# 5. Toter Code & ungenutzte Symbole
uv run vulture src

# 6. Geheimnis- & Token-Erkennung
gitleaks detect --source . -v

# 7. Automatisierte Tests & Code-Coverage (Mindestens 85%)
uv run pytest
```

---

## 4. ADR / TDR Governance (Architektur-Entscheidungen)

Jede wesentliche architektonische oder technische Änderung muss dokumentiert werden:
1. **ADR (Architecture Decision Records):** In `docs/adr/` nach dem MADR-Standard (siehe `docs/adr/template.md`).
2. **TDR / Micro-ADR (Technical Decision Records):** In `docs/tdr/` für kleinere Implementierungsentscheidungen (Bibliotheksversionen, Parsing-Logik, CSS-Regeln).
3. **Diagramme:** Alle Architektur-, Klassen- und Sequenzdiagramme werden direkt mit **Mermaid** in den Dokumenten gepflegt.

---

## 5. Entwicklungs-Workflows

### 5.1 Lokale Umgebung starten

```bash
# 1. Abhängigkeiten installieren
uv sync

# 2. Pre-Commit Hooks installieren
uv run pre-commit install

# 3. Datenbank via Docker starten (optional für lokalen PostgreSQL)
docker compose up -d db

# 4. Datenbank-Migrationen ausführen
uv run alembic upgrade head

# 5. Entwicklungs-Server starten
uv run granian --interface asgi --factory --reload --host 127.0.0.1 --port 8000 atem.presentation.app:create_app
# oder
uv run uvicorn atem.presentation.app:create_app --factory --reload --port 8000
```

### 5.2 Produktions-Deployment auf Hosting

```bash
# Auf dem Cloud-Server:
cp config/env.production.example .env
# .env mit sicheren Produktionspasswörtern und Domains ausfüllen

# Container mit Caddy Reverse Proxy & Postgres bauen und starten
docker compose -f docker-compose.prod.yml up -d --build
```
