# Tech-Debt: Mobile-UX, CI und Deployment (Stand 2026-10-13)

Arbeitsliste in der vereinbarten Reihenfolge. Betriebsschritte auf dem Server stehen im Runbook
([`docs/ops/runbook.md`](../ops/runbook.md), Checkliste 1.5, 1.12, 1.13).

| # | Punkt | Status |
| --- | ------- | -------- |
| 0 | Runbook bereinigen (Status nur noch in der Checkliste) | erledigt |
| 1 | CI grün: `multidict` wegen CVE-2026-104874 aktualisieren (pip-audit) | erledigt |
| 2 | Mobile: Hamburger-Menü ausserhalb des Bildschirms | erledigt |
| 3 | Menü-Sprung landet zu weit unten / unter dem Header | erledigt |
| 4 | Footer: «PUSTERUM» auf dunklem Grund kaum lesbar | erledigt |
| 4b | Kinder-Sektion trotz deaktivierter «Atmende Blume» sichtbar | erledigt |
| 4c | Kontaktformular: Ausweg per E-Mail, wenn ALTCHA blockiert wird | erledigt |
| 5 | `develop` → `main`, Server auf `main` (Runbook 1.12) | erledigt |
| 6 | Automatisches Deployment bei Push auf `main` (ADR-0005, Runbook 1.13) | offen |
| 7 | Schrift: Mindestgrössen anheben + Regler «Schrift A− A A+» | offen |

## Details

### 2 · Hamburger-Menü auf Mobile

Der Logo-Block (`components/navbar.html`) war `flex-shrink-0` mit einem nicht umbrechenden
Untertitel und damit breiter als ein 375-px-Bildschirm. Der Menü-Knopf lag ausserhalb, die Seite
wurde breiter und das Handy zoomte heraus. Lösung: Logo-Block darf schrumpfen, Untertitel erst ab
`sm` sichtbar. E2E-Test prüft «kein horizontaler Overflow» und «Menü-Knopf im Viewport».

### 3 · Menü-Sprung

Das Mobile-Dropdown lag im Seitenfluss des `sticky` Headers: Der Browser berechnete das Sprungziel
mit offenem Menü, danach klappte es zu und der Inhalt rutschte um die Menühöhe nach oben. Lösung:
Dropdown als Overlay (`absolute`), `scroll-padding-top` = Header-Höhe → Kapitel beginnt direkt
unter dem halbtransparenten Header.

### 4 · Footer-Kontrast

`styles.css` setzt für `h1…h6, .font-heading` eine Textfarbe und überschrieb so Tailwind-Klassen wie
`text-white`. Lösung: Selektor mit `:where(…)` (Spezifität 0).

### 4b · Kinder-Sektion

Der Effekt-Schalter «Atmende Blume (Kinder)» im Corporate Design steuerte nur das schwebende Widget;
Sektion «Atmen mit Kindern», Menü-/Footer-Links und die Druckkarte wurden immer ausgeliefert.
Lösung: alles hängt am selben Schalter. Admins sehen die ausgeblendete Sektion weiterhin (mit
Hinweis), damit die Texte pflegbar bleiben.

### 4c · ALTCHA-Fallback

Befund: In einem Firmennetz (Edge) antwortet ein Web-Proxy auf `/altcha/challenge` mit 403 und
liefert für CSS eine HTML-Sperrseite (neu registrierte, unkategorisierte Domain). Server und App
liefern korrekt (geprüft: 200 / `application/json`, CSS `text/css`; unser Stack kennt dort kein 403).
Das Widget zeigt nur «Prüfung fehlgeschlagen – bitte erneut versuchen.» – die Anfrage geht verloren.

Umsetzung:
- `components/contact_form_card.html`: unter `<altcha-widget>` ein verstecktes
  `<p id="altcha-fallback" role="alert" hidden>` – «Die Sicherheitsprüfung konnte nicht geladen
  werden (z. B. wegen eines Firmen-Netzwerkfilters). Schreiben Sie uns direkt an
  <a href="mailto:…">…</a>.» Adresse aus dem bestehenden Content-Block (wie `practice_email` in
  `components/contact_form.html`), keine neue Konfiguration.
- `static/js/app.js`: auf das `statechange`-Event des Widgets hören (`detail.state === "error"` →
  Hinweis zeigen, `"verified"` → wieder verbergen). Bindung nach HTMX-Swaps erneuern
  (`htmx:load`), da das Formular nach dem Absenden ersetzt wird. CSP-konform, kein Inline-JS.
- E2E (`tests_e2e/test_smoke.py`): `page.route("**/altcha/challenge", …)` liefert 403 →
  Checkbox anklicken → Hinweis mit `mailto:` sichtbar, keine CSP-Fehler.
- Firmenseitig unabhängig davon: IT bitten, `pusterum.be` zu kategorisieren bzw. freizugeben.

### 6 · Automatisches Deployment

Pull-Prinzip: CI setzt nach grünem Lauf auf `main` den Branch `production`; ein systemd-Timer auf
dem Server holt neue Stände, baut neu, prüft `/health/ready` und rollt bei Fehlern zurück.
Entscheid und Begründung: ADR-0005.

### 7 · Schriftgrösse

Feste Kleinstgrössen (`text-[10px]`, `text-[11px]`) in öffentlichen Templates auf mindestens
`text-xs` anheben. Dazu ein dezenter Regler im Mobile-Menü und im Footer (100 / 112.5 / 125 %),
gespeichert nur lokal im Browser (`localStorage`, kein Cookie).

## Später (erfasst, nicht eingeplant)

- CI zusätzlich wöchentlich per `schedule:` laufen lassen, damit neue CVEs auffallen, bevor ein
  normaler Push rot wird.
- Dependabot (oder Renovate) für `uv` und GitHub-Actions.
- GitHub-Actions-Pins auf Versionen mit Node 24 anheben (Warnung «Node.js 20 is deprecated»).
- Litestar-Deprecations (~20 000 Warnungen in `pytest`): Pfadparameter mit `FromPath[…]` bzw.
  `Annotated[…, PathParameter()]` und Dependencies mit `NamedDependency[…]` deklarieren – sonst
  Bruch mit Litestar 3.0.
