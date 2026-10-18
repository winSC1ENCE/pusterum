# TDR-0011: Zeilenumbrüche in Inhaltsblöcken

* **Status:** accepted (umgesetzt 2026-10-18)
* **Date:** 2026-10-18
* **Author:** Betreiber (Technik)
* **Scope:** Macro `editable()` (`templates/components/editable_block.html`), Jinja-Filter
  (`presentation/templating.py`), Live-Editor (`static/js/admin/live-editor.js`),
  `admin/editable_block_single.html`, `controllers/admin/content.py`

## Problem / Scope

Die Praxisinhaberin möchte in jedem Text einen Zeilenumbruch setzen können, auch in Titeln, und
dieser soll auf der Website als echter Umbruch erscheinen. Heute:

* einzeilige Blöcke (`text`) werden in einem `<input>` bearbeitet; Enter speichert;
* mehrzeilige Blöcke (`textarea`) speichern `\n`, die Ausgabe `{{ val }}` zeigt den Umbruch aber nicht
  an, ausser an drei Stellen mit CSS `whitespace-pre-line`;
* `rich_text` (`presentation/rich_text.py`) wandelt Umbrüche bereits in `<br>` um;
* nach dem Speichern rendert `admin/editable_block_single.html` den Block mit dem Typ aus der Datenbank
  statt aus dem Template, wodurch sich bei einigen Blöcken der Editor ändert.

## Technical Decision

* **Speicherung:** Inhalte bleiben reiner Text; ein Umbruch ist `\n`. Kein HTML in der Datenbank.
* **Ausgabe:** neuer Jinja-Filter `nl2br`. Er **escaped zuerst** den ganzen Text und ersetzt danach
  `\r\n`/`\n` durch `<br>`; Rückgabe als `markupsafe.Markup`. Das Macro `editable()` nutzt ihn für
  `text` und `textarea` (öffentlich und im Admin-Modus). `rich_text` bleibt unverändert.
* **Editor:** `text` wird ein mitwachsendes `textarea` (Startgrösse 1 Zeile). Enter fügt einen Umbruch
  ein, Speichern mit Alt+S oder dem Knopf. `phone` und `email` bleiben einzeilige `<input>`.
* **CSS:** `whitespace-pre-line` an den bisherigen drei Stellen entfernen, damit Umbrüche nicht doppelt
  erscheinen.
* **Re-Render:** Der Editor-Typ aus dem Template wird als Render-Hinweis mitgeschickt und gegen eine
  Allowlist geprüft (wie `tag`, `css_class`, `rows`). Das Template für den einzelnen Block nutzt diesen
  Hinweis statt `block.block_type`.

## Rationale & Trade-offs

* **Why this approach:**
  * Escape-then-replace ist sicher: Benutzereingaben können kein HTML einschleusen, die strikte CSP
    und die bestehenden Tests zu Render-Hinweisen bleiben gültig.
  * Eine Regel für alle Textblöcke statt CSS-Sonderfälle pro Template.
  * Kein Sanitizer und keine neue Abhängigkeit.
* **Alternatives evaluated:**
  * `<br>` im Inhalt erlauben (Allowlist): verlangt einen HTML-Sanitizer, öffnet XSS-Risiken und
    macht Inhalte schwerer migrierbar.
  * `whitespace-pre-line` überall: zeigt auch Einrückungen und Leerzeichen am Rand, wirkt je nach
    Template unterschiedlich und hilft einzeiligen Feldern nicht.
  * Umbruch nur mit Shift+Enter im `<input>`: ein `<input>` kann keinen Umbruch enthalten.
* **Impact on existing code:**
  * Blöcke, die heute schon `\n` enthalten, zeigen nach dem Deploy Umbrüche, wo bisher keine waren.
    Vor dem Release liefert eine DB-Abfrage die betroffenen Blöcke; die Praxisinhaberin prüft sie.
  * Titel mit Umbruch: Die Layouts (Hero, Abschnittstitel) werden mit einem Umbruch per Screenshot
    geprüft.
  * Tests: Escaping trotz Umbruch, Umbruch in einem Titel, Editor-Typ nach dem Speichern, E2E.
