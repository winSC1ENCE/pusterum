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
Jinja2 + HTMX + Alpine.js (CSP-Build) + Tailwind (kompiliert) · structlog · Argon2id · pyotp · ALTCHA ·
Pillow · Caddy 2 (caddy-ratelimit) · restic · Docker.

Clean Architecture unter `src/atem/` (Abhängigkeiten zeigen nur nach innen):

- `domain/` – Entitäten (`models/`), Ports als ABCs (`interfaces/`), Exceptions. Framework-frei.
- `application/` – Services (Use Cases) und Pydantic-DTOs.
- `infrastructure/` – Settings, Logging, DB (ORM-Modelle, Repositories auf Basis `repositories/base.py`,
  Seeds), E-Mail, Security (Argon2, Fernet, TOTP), Captcha, Media (Pillow).
- `presentation/` – `app.py` (Factory `create_app`), `bootstrap.py`, Controller (Admin als Paket
  `controllers/admin/`), `security/` (Guard, Header, Host, Proxy, Form-Token), `errors.py`, Templates, Static.
- `cli.py` – `python -m atem.cli {create-admin|reset-2fa|seed-content|purge-messages}`.

## Befehle

```bash
uv sync && uv run pre-commit install
docker compose up -d db                     # nur PostgreSQL
cp config/env.development.example .env      # einmalig; Default-ENVIRONMENT ist production!
uv run alembic upgrade head                 # Schema (Baseline 0000) + Datenmigrationen
scripts/build-css.sh                        # Tailwind kompilieren (--watch beim Entwickeln)
uv run granian --interface asgi --factory --reload --host 127.0.0.1 --port 8000 atem.presentation.app:create_app
```

`--factory` ist Pflicht (`create_app` ist eine Factory). Läuft der Container `atem_app`, belegt er Port 8000 →
`docker compose stop app`. Admin lokal: `/admin/login` (`admin` / `admin-secure-init-pass-change-me`, wird nur
in development geseedet; 2FA dort optional).

Quality-Gates (alle müssen grün sein, auch via pre-commit/CI):

```bash
uv run ruff check src tests tests_e2e migrations && uv run ruff format --check src tests tests_e2e migrations
uv run mypy src                             # strict
uv run bandit -c pyproject.toml -r src
uv run deptry . && uv run vulture src
uv run pytest                               # SQLite, Coverage >= 90 %
TEST_DATABASE_URL=postgresql+asyncpg://atem:…@localhost:5432/atem_test uv run pytest   # gegen PostgreSQL
uv run pytest tests_e2e --no-cov            # Playwright-E2E (CSP-Verletzungen = Fehler)
```

Ruff: Zeilenlänge 100 – lange deutsche Texte als implizit verkettete String-Literale umbrechen.
pre-commit `check-added-large-files` blockiert Dateien > 500 KB → Bilder vorher verkleinern
(`magick in.jpg -auto-orient -resize '1200x1200>' -strip -quality 82 out.jpg`).

## Content-System (wichtig)

- Alle editierbaren Texte/Bilder sind Content-Blöcke, gerendert über das Macro `editable(key, …)` aus
  `templates/components/editable_block.html`. Standardtexte stehen **nur** in
  `infrastructure/database/seed/content_defaults.py` (`DEFAULT_CONTENT_BLOCKS`; Jinja-Globals
  `content_default`, `count_numbered_keys`) – das Macro holt den Fallback selbst. Versionierung: ADR-0002.
- Nummerierte Listen (Zitate, „Für wen“, Ausbildungen) zählen ihre Keys über `count_numbered_keys()` –
  neuer Eintrag = neuer Default-Key, keine Template-Änderung.
- Alle Text-Blöcke dürfen leer gespeichert werden (Bild-Blöcke nicht, siehe `ContentService.save_block_content`).
  Leere Blöcke rendert `editable()` öffentlich nicht; im Admin-Modus erscheinen sie als gestrichelter
  Platzhalter. Umgebende Deko ggf. im Template mit `is_admin`/Inhalt prüfen (Beispiel: `hero.text`).
- Seeding (`ContentService.seed_defaults`, Entrypoint `atem.cli seed-content`) fügt nur **fehlende** Keys ein.
  Wird ein bestehender Default-Text geändert, braucht es eine **Alembic-Datenmigration** mit
  `migrations/_helpers.py:replace_default_texts` (ersetzt nur exakt unveränderte Blöcke, schreibt neue Version).
  Siehe TDR-0003.
- Content-Saves sind abgesichert: Key-Muster + nur existierende Keys, Bildpfad-Muster, max. 10 000 Zeichen,
  Tag-Allowlist; Werte in Alpine-Attributen immer mit `|tojson` bzw. `data-*`.
- UI-Bausteine: `components/ui_macros.html` (`section_header`, `check_item`).
- Angebote & Tarife: `Offering`-Modul (Admin `/admin/services`). Keine Fakten (Preise, Adressen,
  Anerkennungen) erfinden – das pflegt die Praxisinhaberin im Admin.
- Das DB-Schema gehört **ausschliesslich Alembic** (Baseline `0000_initial_schema`). Schema-Änderungen immer
  als neue Revision; `alembic check` muss „No new upgrade operations“ melden. `create_all` nur in Tests.
- `.env*`-Dateien sind für Claude gesperrt – Vorlagen liegen in `config/*.example`.

## Sicherheitsregeln (Admin & Formulare)

- Neue Admin-Routen gehören in einen Controller mit `guards = [require_admin]`
  (`presentation/security/admin_auth.py`) und in `ADMIN_CONTROLLERS` – nie eigene Session-Prüfungen schreiben.
  `tests/test_route_guards.py` erkennt ungeschützte `/admin`-Routen automatisch.
- Jeder POST braucht CSRF: HTMX/`fetch` senden `x-csrftoken` automatisch (`hx-headers` am `<body>`,
  `csrfHeaders()` in `app.js`), klassische Formulare ein `<input type="hidden" name="_csrf_token" value="{{ csrf_token() }}">`.
- Logout ist ein POST. Sessions werden über `User.session_version` widerrufen.
- 2FA (TOTP + Recovery-Codes) ist in production/staging Pflicht (`ADMIN_REQUIRE_2FA`).
  Notfall: `python -m atem.cli reset-2fa --username …`.
- Uploads nur über `MediaService` (Pillow-Re-Encoding, kein SVG); Theme-Werte nur Hex/Font-Allowlist.
- Keine Personendaten ins Log (keine E-Mails/Namen); Event `login_failed` mit IP ist die fail2ban-Schnittstelle.
- Gesamtbild: ADR-0004.

## Frontend & Content-Security-Policy

- Strikte CSP (`presentation/security/security_headers.py`): **kein Inline-JS, kein `eval`, keine `<style>`-Elemente,
  keine externen Hosts**. Erlaubt sind nur `style="…"`-Attribute.
- Tailwind wird kompiliert: `scripts/build-css.sh` (`--watch` beim Entwickeln). `static/css/app.css` ist generiert
  (gitignored, im Docker-Build erzeugt). Neue Klassen in Templates/JS werden automatisch erfasst.
- Alpine läuft als **CSP-Build** (`static/vendor/alpinejs-csp`): in Templates keine Template-Literals, Pfeilfunktionen,
  Statements oder Globals (`window`, `document`, `Math`) – Logik in `Alpine.data`-Komponenten unter
  `static/js/components/`; Werte über `data-*`-Attribute übergeben.
- Theme-Variablen kommen aus `GET /theme.css`; Schriften sind lokal (`static/fonts`, `static/css/fonts.css`).
- Browser-Tests: `uv run pytest tests_e2e --no-cov` (Playwright; prüft CSP-Verletzungen und JS-Fehler).

## Dokumentation & Governance

- Architekturentscheide: `docs/adr/` (MADR, `template.md`); kleinere technische Entscheide: `docs/tdr/`.
- Diagramme nur in Mermaid (`docs/architecture/`); Betrieb/Notfälle: `docs/ops/runbook.md`.
- `docs/reviews/` enthält **lokale, nicht versionierte** Analysen (per `.gitignore` ausgeschlossen, da sie
  offene Schwachstellen beschreiben) – nie committen oder verlinken.
- Umsetzungspläne: `docs/plans/` (z. B. `2026-10-04-pusterum-rebranding.md`).
- Drittbibliotheken im Browser liegen unter `static/vendor/` (README mit Version + SHA-256).
- Commits: Conventional Commits (`feat(scope): …`, `fix(…)`, `chore: …`).

## Deployment

Domain: **www.pusterum.be** (`.be` = Bern, nicht Belgien); `pusterum.be` leitet per Caddy auf `www` um.
Kontakt-Mail: `kontakt@pusterum.be`. Hosting, `docker compose -f docker-compose.prod.yml up -d --build` (Caddy mit Auto-TLS, `.env` aus
`config/env.production.example`). Der Container-Entrypoint (`docker/entrypoint.sh`) führt `alembic upgrade head`
und `python -m atem.cli seed-content` aus; den ersten Admin legt `python -m atem.cli create-admin` an.
Secrets in `.env`, `db.env`, `backup.env` (Vorlagen in `config/`); Backups per restic auf die Storage Box.
Ablauf, Restore und Notfälle: [`docs/ops/runbook.md`](docs/ops/runbook.md).
