# PROJECT PLAYBOOK: PUSTERUM WEBAPPLIKATION

> **Projektziel:** Hochwertige, performante und sichere Single-Page Webapplikation für **PUSTERUM** – Praxis für Atem- und Körpertherapie mit integrierter Inhalts- und Anfragenverwaltung.

---

## 1. Architekturübersicht (Clean Architecture & OOP / ABC)

Das Projekt folgt strikt den Prinzipien der **Clean Architecture / Ports & Adapters**:

```
src/atem/
├── cli.py                   # Betriebs-CLI: create-admin, reset-2fa, unlock, seed-content, purge-messages
├── domain/                  # Reine Geschäftslogik & Entitäten (Framework-agnostisch)
│   ├── exceptions.py        # Domänen-spezifische Ausnahmen
│   ├── models/              # Entitäten mit Verhalten (User, Offering, ContentBlock, Theme, ContactMessage)
│   └── interfaces/          # Ports (ABCs): Repositories, IEmailService, ICaptcha, ITotpProvider,
│                            #   ISecretCipher, IImageSanitizer, IPasswordHasher
│
├── application/             # Use Cases & Orchestrierung
│   ├── dto/                 # Pydantic DTOs & Validierungsschemata
│   └── services/            # Auth, Contact, Content, Offering, Theme, Media
│
├── infrastructure/          # Externe Adapter & Implementierungen
│   ├── config/              # Pydantic Settings inkl. Produktions-Validierung & HKDF-Schlüsselableitung
│   ├── logging/             # Structlog (JSON in Prod, Farbe in Dev)
│   ├── database/            # SQLAlchemy 2.0 Async & asyncpg
│   │   ├── models/          # ORM-Tabellendefinitionen (Schema gehört Alembic)
│   │   ├── repositories/    # Generisches SqlAlchemyRepository + konkrete Repositories
│   │   └── seed/            # content_defaults.py – einzige Quelle der Standardtexte
│   ├── email/               # SmtpEmailService (TLS/STARTTLS), MockEmailService
│   ├── captcha/             # ALTCHA (self-hosted Proof-of-Work)
│   ├── media/               # Pillow-Re-Encoding, Dateiablage
│   └── security/            # Argon2id, Fernet-Verschlüsselung, TOTP
│
└── presentation/            # Web-Auslieferung
    ├── app.py               # Litestar Application Factory (`create_app`)
    ├── bootstrap.py         # Lifespan: Dev-Seeding, Aufräum-Task für Nachrichten
    ├── controllers/         # Public, Health, admin/ (auth, security, dashboard, design, content, media, services)
    ├── security/            # Guard require_admin, Security-Header/CSP, Host-, Proxy-Validierung, Form-Token
    ├── errors.py            # Globale Exception-Handler & Fehlerseiten
    ├── assets/              # Tailwind-Quelle (kompiliert nach static/css/app.css)
    ├── templates/           # Jinja2 (HTMX, Alpine.js CSP-Build) – kein Inline-JS
    └── static/              # CSS, JS-Komponenten, lokale Fonts, vendor/ (gepinnt + SHA-256)
```

Querschnitt Sicherheit: siehe [ADR-0004](docs/adr/ADR-0004-security-architecture.md) und
[`docs/architecture/`](docs/architecture/README.md).

---

## 2. Tech-Stack Matrix

| Komponente | Technologie / Tool | Zweck |
| :--- | :--- | :--- |
| **Runtime & Language** | Python 3.12+ | Moderne Async Python Basis |
| **Package Manager** | Astral `uv` | Blitzschnelle, deterministische Paketverwaltung via `pyproject.toml` |
| **Web Framework** | `Litestar` | Stark typisiertes ASGI-Framework mit Dependency Injection & OOP |
| **ORM / Database** | `SQLAlchemy 2.0 Async` + `asyncpg` + `PostgreSQL 16` | Robustes Datenmodell mit sauberer Interface-Abstraktion |
| **Migrations** | `Alembic` | Asynchrone Datenbankschema-Migrationen |
| **Frontend UI** | `Jinja2` + `HTMX` + `Alpine.js` (CSP-Build) + `Tailwind CSS` (Standalone-CLI) | Single-Page-Erlebnis ohne Node.js, strikte CSP ohne Inline-Skripte |
| **Admin-Sicherheit** | `pyotp` + `segno` + `cryptography` (Fernet) | TOTP-2FA mit QR-Code, Recovery-Codes, verschlüsselte Secrets |
| **Spam-Schutz** | `ALTCHA` (self-hosted) | Proof-of-Work-CAPTCHA ohne Drittanbieter |
| **Bild-Uploads** | `Pillow` | Verifikation & Re-Encoding (entfernt EXIF/GPS) |
| **Logging** | `structlog` | Strukturierte JSON-Logs für Produktion, lesbare Farbkonsole lokal |
| **Passwort-Sicherheit** | `Argon2id` (`argon2-cffi`) | Aktueller State-of-the-Art Standard für Passwort-Hashing |
| **Reverse Proxy** | `Caddy 2` + `caddy-ratelimit` | Automatisches HTTPS, HSTS, Rate-Limits, Security-Header |
| **Backups** | `restic` → SFTP-Backup-Speicher | Verschlüsselte, tägliche Datenbank- & Medien-Backups |
| **Container** | Docker & Docker Compose | Lokales Development & Produktionsbetrieb |

---

## 3. Qualitäts-, Sicherheits- & Linter-Gates

Das Projekt unterliegt strengen Qualitätsprüfungen. Alle Prüfungen sind in `.pre-commit-config.yaml` und GitHub Actions CI (`.github/workflows/ci.yml`) integriert:

```bash
# 1. Linting & Formatting
uv run ruff check src tests tests_e2e migrations
uv run ruff format --check src tests tests_e2e migrations

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

# 7. Automatisierte Tests & Code-Coverage (mindestens 90 %; TEST_DATABASE_URL für PostgreSQL)
uv run pytest

# 8. Browser-E2E mit CSP-Prüfung (Playwright)
uv run pytest tests_e2e --no-cov
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

# 3. Entwicklungs-Konfiguration (Default-ENVIRONMENT ist production!)
cp config/env.development.example .env

# 4. Datenbank via Docker starten und migrieren
docker compose up -d db
uv run alembic upgrade head

# 5. CSS kompilieren (--watch während der Template-Arbeit)
scripts/build-css.sh

# 6. Entwicklungs-Server starten
uv run granian --interface asgi --factory --reload --host 127.0.0.1 --port 8000 atem.presentation.app:create_app
```

### 5.2 Produktions-Deployment auf Hosting

```bash
# Auf dem gehärteten Server (ops/server/cloud-init.yaml):
cp config/env.production.example .env           # alle CHANGE_ME ersetzen
cp config/db.env.production.example db.env
cp config/backup.env.production.example backup.env

# Caddy, App (migriert & seedet im Entrypoint), PostgreSQL und Backup-Dienst starten
docker compose -f docker-compose.prod.yml up -d --build

# Ersten Admin anlegen; beim ersten Login wird 2FA eingerichtet
docker compose -f docker-compose.prod.yml exec app python -m atem.cli create-admin \
  --username <benutzername> --email kontakt@pusterum.be
```

Backups, Restore-Test, Rollback und Notfälle: [`docs/ops/runbook.md`](docs/ops/runbook.md).
