# TDR-0015: Links in formatierten Texten

* **Status:** accepted (umgesetzt 2026-10-30)
* **Date:** 2026-10-30
* **Author:** Betreiber (Technik)
* **Scope:** `presentation/rich_text.py`, Rich-Text-Toolbar (`components/editable_block.html`,
  `static/js/admin/live-editor.js`), `check_item` (`components/ui_macros.html`),
  Migration `0025_links_about`, Helper `migrations/_helpers.py:add_links`/`link_phrases`

## Problem / Scope

Die Praxisinhaberin möchte bei den Ausbildungen auf die Ausbildungsstätten (IKP, AFS, Sivananda,
Klubschule Migros) und im Praxistext auf die Gemeinschaftspraxis verlinken. Inhaltsblöcke konnten
bisher keine Links enthalten; HTML ist in Inhalten bewusst nicht erlaubt.

## Technical Decision

* Rich-Text kennt neu `[Text](https://…)`. Der Renderer erkennt Links auf dem Rohtext, escaped
  Text und URL und erzeugt `<a href="…" target="_blank" rel="noopener noreferrer">`.
  Erlaubt sind nur `https://`-Adressen ohne Leerzeichen, Anführungszeichen, `<>`, `()`, `[]` und
  Backslash; alles andere bleibt sichtbarer Text. Fett/kursiv/unterstrichen wirken im Linktext,
  nicht in der URL.
* Die Toolbar hat einen Knopf «Link»: Er setzt `[Auswahl](https://)` und den Cursor hinter
  `https://` (kein `prompt`, CSP-konform).
* `about.credential_*` und `practice.description` sind neu `rich_text`.
* Migration `0025_links_about` verlinkt die Namen in den **aktuellen** Texten (auch bearbeiteten),
  wenn die URL dort noch nicht vorkommt. Der Wortlaut bleibt gleich; jede Änderung ist eine neue
  Version und im Admin wiederherstellbar.

## Rationale & Trade-offs

* **Why this approach:** Markdown-Linksyntax ist kurz, lesbar und passt zur bestehenden
  Rich-Text-Syntax. Escapen vor dem Erzeugen von Markup hält die Inhalte XSS-sicher.
* **Alternatives evaluated:** separates URL-Feld pro Eintrag (geht nicht für Links im Fliesstext);
  HTML-Allowlist mit Sanitizer (mehr Angriffsfläche, neue Abhängigkeit).
* **Impact on existing code:** Bestehende Rich-Text-Inhalte ändern sich nicht. In den umgestellten
  Blöcken wirken `*`, `__` und Zeilen mit `- ` neu als Formatierung.
