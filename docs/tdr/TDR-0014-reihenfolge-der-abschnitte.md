# TDR-0014: Reihenfolge der Abschnitte im Design-Studio

* **Status:** accepted (umgesetzt 2026-10-21)
* **Date:** 2026-10-21
* **Author:** Betreiber (Technik)
* **Scope:** `PageSection` (`domain/models/theme.py`), Spalte `theme_configs.section_order`
  (Migration `0023_section_order`), `ThemeService.move_section`, Route `POST /admin/design/sections`,
  Jinja-Globals `page_sections`/`nav_sections`, `pages/index.html`, Navbar und Footer

## Problem / Scope

Die Praxisinhaberin möchte die Reihenfolge der Abschnitte auf der Startseite selbst bestimmen.
Bisher war sie in `index.html` fest verdrahtet, und Navbar (Desktop, Mobil) und Footer führten
je eine eigene Linkliste, die von Hand gleich gehalten werden musste.

## Technical Decision

* **Verschiebbar** sind Kompetenzen, Angebote, Kinder, Über mich, Zitate und Praxis
  (`PageSection`). Der Startbereich bleibt oben, «Kontakt» unten.
* **Default** ist die Reihenfolge der Enum-Deklaration: Kompetenzen, Angebote, Kinder,
  Über mich, Zitate, Praxis.
* **Speicherung** als kommagetrennter Text im aktiven Theme (gleiches Muster wie `dandelion_mode`).
  `PageSection.parse_order` liefert immer eine vollständige Liste: unbekannte Werte und Duplikate
  fallen weg, fehlende Abschnitte werden in Default-Reihenfolge angehängt. Ein künftiger neuer
  Abschnitt braucht so keine Datenmigration.
* **Bedienung:** Karte «5. Reihenfolge der Abschnitte» im Design-Studio mit ↑/↓ pro Abschnitt.
  Jeder Knopf ist ein Formular mit `hx-post`: HTMX tauscht nur die Karte aus
  (`admin/section_order_card.html`). Die Seite lädt nicht neu und springt nicht, der Fokus bleibt
  auf dem Knopf des verschobenen Abschnitts. Ohne JavaScript funktioniert das Formular weiter
  (Redirect zurück zur Karte). Es gibt kein neues JavaScript und keine Drag-and-drop-Bibliothek.
* **Eine Quelle für Seite und Navigation:** `page_sections(theme)` steuert die Includes in
  `index.html`, `nav_sections(theme)` die Links in Navbar und Footer. Die Zitate haben keinen Link,
  der Kinder-Link erscheint nur bei aktivem Angebot.

## Rationale & Trade-offs

* **Why this approach:**
  * kleine Änderung im bestehenden Theme, keine neue Tabelle;
  * Navigation kann nicht mehr von der Seitenreihenfolge abweichen;
  * CSP-sicher ohne zusätzlichen Code im Browser.
* **Grenzen:** Verschieben geht nur schrittweise. Bei sechs Einträgen ist das vertretbar.
* **Alternatives evaluated:**
  * Drag-and-drop (z. B. SortableJS): bequemer, aber neue Vendor-Bibliothek und Alpine-Komponente
    für wenige Einsätze.
  * Eine Positionszahl pro Abschnitt: fehleranfällig (doppelte oder fehlende Zahlen).
* **Impact on existing code:**
  * `index.html`, `navbar.html` und `footer.html` lesen die Reihenfolge statt fester Listen.
  * Presets, Formen und Farbanpassungen lassen die Reihenfolge unverändert.
