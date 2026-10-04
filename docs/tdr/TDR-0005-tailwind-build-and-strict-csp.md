# TDR-0005: Tailwind-Build, Alpine-CSP-Build & strikte Content-Security-Policy

* **Status:** accepted
* **Date:** 2026-10-04
* **Author:** Nicolas Mischler
* **Scope:** Templates, `static/`, `presentation/security/security_headers.py`, Dockerfile

## Problem / Scope

Tailwind wurde zur Laufzeit im Browser kompiliert (407 KB, Inline-Konfiguration), Alpine nutzte
`new Function`, Theme-Variablen standen in einem Inline-`<style>`, Schriften kamen von Google. Damit war
keine wirksame CSP möglich – gespeicherte XSS hätte ungehindert Skripte ausführen können.

## Technical Decision

* **Tailwind 3.4.17 Standalone-CLI** (gepinnt + SHA256, ohne Node.js): `scripts/build-css.sh`,
  Konfiguration in `tailwind.config.js`, Ausgabe `static/css/app.css` (≈ 41 KB, generiert, gitignored,
  im Docker-Build erzeugt).
* **Alpine `@alpinejs/csp@3.17.4`** (vendored): Logik in `static/js/components/*.js` als `Alpine.data`;
  Templates enthalten nur einfache Ausdrücke, Werte kommen über `data-*`-Attribute.
* **Theme** als `GET /theme.css?v=<hash>` (immutable cache), **Fonts** lokal (`static/fonts`, woff2).
* **CSP:** `default-src 'self'; script-src 'self'; style-src 'self'; style-src-attr 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; worker-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'; object-src 'none'` (+ `upgrade-insecure-requests` in Produktion).
* htmx ohne injizierte Indikator-Styles und ohne `eval` (`htmx-config`-Meta).

## Rationale & Trade-offs

* **Why this approach:** einzige Variante, die Skript-Injection auf Browserebene vollständig blockiert;
  zusätzlich deutlich schnellere Seite.
* **Alternatives evaluated:** CSP mit `unsafe-inline`/`unsafe-eval` (wirkungslos gegen XSS), Nonces
  (Alpine-Standardbuild bräuchte trotzdem `unsafe-eval`).
* **Impact on existing code:** einzig `style`-Attribute bleiben erlaubt (datengetriebene Grössen; keine
  Skriptausführung möglich). Playwright-E2E schlägt bei jeder CSP-Verletzung fehl.
