# CLAUDE.md

Leitfaden für Claude Code in diesem Repository. Das ausführliche Projekt-Playbook ist [`GEMINI.md`](GEMINI.md) –
dieses Dokument fasst das Wichtigste zusammen und ergänzt Stolperfallen.

## Projekt

**PUSTERUM** – Praxis für Atem- und Körpertherapie (Therapeutin: Stephanie, Ausbildung Ganzheitlich-Integrative
Atemtherapie IKP), eingebettet in eine Physiotherapie-Gemeinschaftspraxis. *Pusterum* ist dänisch für
„Raum zum Atmen“. Leitmotiv: Pusteblume. Der frühere Name «Atemtherapie Hā Ola» ist abgelöst und darf nicht
mehr auftauchen. Keine Krankenkassen-/EMR-/ASCA-/OdA-KT-Anerkennungen behaupten.

Single-Page-Webapp mit Inline-Content-Editing für die Praxisinhaberin.
UI-Texte und Doku auf Deutsch, Schweizer Schreibweise („ss“ statt „ß“), Anführungszeichen «…».

## Stack & Architektur

Python 3.12 · `uv` · Litestar (ASGI, DI) · SQLAlchemy 2.0 async + asyncpg · PostgreSQL 16 · Alembic ·
Jinja2 + HTMX + Alpine.js + Tailwind (Play-CDN, kein Node) · structlog · Argon2id · Caddy 2 · Docker.

Clean Architecture unter `src/atem/` (Abhängigkeiten zeigen nur nach innen):

- `domain/` – Entitäten (`models/`), Ports als ABCs (`interfaces/`), Exceptions. Framework-frei.
- `application/` – Services (Use Cases) und Pydantic-DTOs.
- `infrastructure/` – Settings, Logging, DB (ORM-Modelle, Repositories), E-Mail, Security.
- `presentation/` – `app.py` (Application Factory `create_app`), Controller, Templates, Static.

## Befehle

```bash
uv sync && uv run pre-commit install
docker compose up -d db                     # nur PostgreSQL
uv run alembic upgrade head                 # Datenmigrationen
uv run granian --interface asgi --factory --reload --host 127.0.0.1 --port 8000 atem.presentation.app:create_app
```

`--factory` ist Pflicht (`create_app` ist eine Factory). Läuft der Container `atem_app`, belegt er Port 8000 →
`docker compose stop app`. Admin lokal: `/admin/login` (`admin` / `admin-secure-init-pass-change-me`).

Quality-Gates (alle müssen grün sein, auch via pre-commit/CI):

```bash
uv run ruff check src tests migrations && uv run ruff format --check src tests migrations
uv run mypy src                             # strict
uv run bandit -c pyproject.toml -r src
uv run deptry . && uv run vulture src
uv run pytest                               # Coverage >= 85 %, Tests nutzen SQLite (aiosqlite)
```

Ruff: Zeilenlänge 100 – lange deutsche Texte als implizit verkettete String-Literale umbrechen.
pre-commit `check-added-large-files` blockiert Dateien > 500 KB → Bilder vorher verkleinern
(`magick in.jpg -auto-orient -resize '1200x1200>' -strip -quality 82 out.jpg`).

## Content-System (wichtig)

- Alle editierbaren Texte/Bilder sind Content-Blöcke: Defaults in `DEFAULT_CONTENT_BLOCKS`
  (`infrastructure/database/repositories/sqlalchemy_content_repository.py`), gerendert über das Macro
  `editable(key, fallback, ...)` aus `templates/components/editable_block.html`. Versionierung: ADR-0002.
- Der Template-Fallback sollte dem Default entsprechen.
- `_ensure_seed_data` fügt nur **fehlende** Keys ein. Wird ein bestehender Default-Text geändert, braucht es
  eine **Alembic-Datenmigration** (Muster: `migrations/versions/…0001_pusterum_rebranding_content.py`,
  nur exakt unveränderte Blöcke ersetzen, als neue Version schreiben). Siehe TDR-0003.
- Das DB-Schema wird beim App-Start per `Base.metadata.create_all` erzeugt (`presentation/app.py`);
  Alembic-Revisionen sind bisher reine Datenmigrationen und müssen die Existenz der Tabellen prüfen.
- Profil/Praxis-Daten (`sqlalchemy_profile_repository.py`) liefern Platzhalter, wenn die Tabellen leer sind.
  Keine Fakten (Preise, Adressen, Anerkennungen) erfinden – Services werden im Admin gepflegt.

## Dokumentation & Governance

- Architekturentscheide: `docs/adr/` (MADR, `template.md`); kleinere technische Entscheide: `docs/tdr/`.
- Diagramme in Mermaid (`docs/architecture/`).
- Umsetzungspläne: `docs/plans/` (z. B. `2026-10-04-pusterum-rebranding.md`).
- Commits: Conventional Commits (`feat(scope): …`, `fix(…)`, `chore: …`).

## Deployment

Hosting, `docker compose -f docker-compose.prod.yml up -d --build` (Caddy mit Auto-TLS, `.env` aus
`.env.example`). Danach Datenmigrationen im Container: `docker compose -f docker-compose.prod.yml exec app alembic upgrade head`.
