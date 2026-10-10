# Plan: Rebranding «Hā Ola» → PUSTERUM fertigstellen + CLAUDE.md

## Context
Die Praxis heisst neu **PUSTERUM** (dän. „Raum zum Atmen“). Eine abgebrochene Session hat bereits
`DEFAULT_CONTENT_BLOCKS` (`sqlalchemy_content_repository.py`) und die Profil-Defaults
(`sqlalchemy_profile_repository.py`) auf die Texte aus `.tmp/Texte Webseite Endversion.md` umgestellt
und das neue Portrait als `static/images/stephanie_portrait.jpg` kopiert (identisch mit `.tmp/Foto Webseite Physio.JPG`).
Offen: Templates (Fallbacks + Darstellung der neuen Keys), restliche «Hā Ola»-Stellen, Zitate,
bestehende DBs, Tests, Doku und eine neue `CLAUDE.md`.

Entscheide (User): Alembic-Datenmigration · rotierendes Zitat-Band · Brücken-Text + 8er-Liste.

## 0. Plan im Repo ablegen
Diesen Plan als `docs/plans/2026-10-04-pusterum-rebranding.md` ablegen (neuer Ordner `docs/plans/`) und in `CLAUDE.md` darauf verweisen.

## 1. CLAUDE.md (neu, Repo-Root, deutsch)
Kompakt, verweist auf GEMINI.md statt es zu duplizieren:
- Projekt/Branding: PUSTERUM, Therapeutin Stephanie, Atem- und Körpertherapie (IKP), Gemeinschaftspraxis Physio.
- Architektur-Schichten (domain/application/infrastructure/presentation), Litestar-Factory `atem.presentation.app:create_app` (`--factory`!).
- Befehle: `uv sync`, `docker compose up -d db`, Granian-Dev-Server, alle Quality-Gates aus GEMINI.md §3, `uv run pytest` (Coverage ≥ 85 %).
- Content-System: Texte = `DEFAULT_CONTENT_BLOCKS` + `editable()`-Macro (`components/editable_block.html`) mit Template-Fallback; Seed fügt **nur fehlende Keys** ein → Textänderungen an Defaults brauchen eine Datenmigration; Versionierung (ADR-0002).
- Schema via `Base.metadata.create_all` im Lifespan (`app.py:172`); Alembic unter `migrations/`.
- Konventionen: ruff line-length 100, mypy strict, ADR/TDR-Pflicht (`docs/adr`, `docs/tdr`, Mermaid), Conventional Commits, Sprache UI/Doku Deutsch (CH-Schreibweise „ss“).
- Ports-Konflikt-Hinweis (atem_app auf 8000).

## 2. Restliche Namens-Stellen (Templates/Code)
Muster: «Atemtherapie Hā Ola» → «PUSTERUM» bzw. «PUSTERUM – Atem- und Körpertherapie»; Template-Fallbacks in `editable(...)` an die neuen Defaults angleichen.
- `layouts/base.html` (title, meta description/keywords/author – EMR/ASCA/OdA-KT-Claims entfernen)
- `components/hero.html`, `about.html` (Fallbacks, alt-Texte, Portrait-Fallback → `stephanie_portrait.jpg`, „Über mich & Hā Ola“ → „Über mich & PUSTERUM“), `navbar.html`, `footer.html`, `practice.html`, `dandelion_ambient.html:348`
- `pages/impressum.html`, `pages/datenschutz.html` (Titel, E-Mail → `kontakt@pusterum.ch`)
- `sqlalchemy_profile_repository.py:284/291` PracticeInfo-Fallback (Name, E-Mail)
- `pyproject.toml` description (+ ruff-Kommentar „Hawaiian okina“ neutralisieren)

## 3. Kompetenz-Sektion (`components/competencies.html`)
- Header: badge/title/subtitle mit neuen Fallbacks.
- Block «Was ist …»: `competencies.bridge_title`, `bridge_p1–p4` (bereits in Defaults).
- Block «Für wen …»: `for_whom_title`, `for_whom_subtitle` + neue Keys `competencies.for_whom_1..8` (wortgetreu aus der Vorlage) als editierbare Liste mit Häkchen-Icon (2-spaltig ab md).
- Karten-Loop über `profile.competencies` entfällt; alte Keys `competencies.1-3.*` aus Defaults entfernen.
- Die von der Vorsession erfundenen Fallback-Listen in `get_competencies`/`get_services` (inkl. erfundener Preise 140/170 CHF) **zurückbauen** – nicht aus der Vorlage; Services bleiben DB-/Admin-gepflegt.

## 4. Zitat-Band (neu `components/quotes.html`)
- In `pages/index.html` nach `about.html` einbinden.
- Keys `quotes.1..6.text` / `quotes.1..6.author` (Nestor, Wim Hof, Tolle, Sivananda, Orr, Cousins; Anführungszeichen vereinheitlichen «…») in `DEFAULT_CONTENT_BLOCKS`, section `quotes`.
- Alpine.js-Rotation (z. B. 7 s, Fade, Pause bei Hover, Punkte-Navigation, `prefers-reduced-motion` → keine Auto-Rotation); im Edit-Modus alle Zitate sichtbar/editierbar. Styling mit bestehenden `theme-*`-Klassen.
- Kurzes TDR `docs/tdr/TDR-0003-quote-rotator.md` (Template `docs/tdr/template.md`).

## 5. Datenmigration für bestehende DBs
`migrations/versions/` existiert noch nicht (Schema läuft über `create_all`). Erste Revision als **reine Datenmigration**:
- Guard: nur ausführen, wenn Tabellen `content_block`/`content_block_version` existieren (Inspector).
- Mapping `OLD_DEFAULTS = {key: alter Default-Text}` (aus `git show HEAD:…/sqlalchemy_content_repository.py`) → für jeden Key, dessen `current_content` **exakt** dem alten Default entspricht: neue Version (`version_number+1`, author „System Migration“, summary „Rebranding PUSTERUM“) + `current_content` aktualisieren. Manuell geänderte Blöcke bleiben unberührt.
- Analog Profil-/PracticeInfo-Zeile, falls Felder exakt alte Defaults enthalten (Name/E-Mail/Portrait-URL).
- Neue Keys (bridge, for_whom, quotes) kommen automatisch über `_ensure_seed_data`.
- `downgrade`: no-op (Historie erlaubt Restore über Admin).
- Tabellen-/Spaltennamen vorab in `infrastructure/database/models/` verifizieren.

## 6. Portrait
`stephanie_portrait.jpg` (2038×2014, 895 KB, iPhone-EXIF): Orientierung prüfen (`identify -format '%[orientation]'`), falls ImageMagick vorhanden auf ~1200 px / Qualität 82 verkleinern + EXIF strippen (auto-orient). `ste_aquarel.png` bleibt als Datei liegen.

## 7. Tests & Doku
- `tests/test_content.py`: „Hā Ola.“ → „PUSTERUM.“ (Zeilen 22, 36, 45, 61, 86, 92, 158).
- Ggf. Test für neue Keys (`competencies.for_whom_1`, `quotes.1.text`) und Render-Test der Startseite (Zitat-Band + Liste vorhanden).
- `README.md` Titel/Beschreibung, `DEV_START.md:3`, `TDR-0002` Markenbezug, GEMINI.md Projektziel → PUSTERUM.

## Verifikation
1. `git grep -n -i "hā ola\|ha-ola"` → keine Treffer ausser Migration (OLD_DEFAULTS).
2. `uv run ruff check src tests && uv run ruff format --check src tests && uv run mypy src && uv run bandit -c pyproject.toml -r src && uv run vulture src && uv run deptry .`
3. `uv run pytest` (≥ 85 % Coverage).
4. `docker compose up -d db && uv run alembic upgrade head` gegen bestehende Dev-DB → alte Texte ersetzt, Versionshistorie vorhanden.
5. Granian-Dev-Server starten, http://127.0.0.1:8000 prüfen: Hero/Über-mich/Portrait, Kompetenz-Sektion mit 8er-Liste, Zitat-Rotation, Footer/Impressum; Admin-Inline-Edit eines Zitats testen.
