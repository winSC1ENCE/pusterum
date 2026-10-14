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
| 6 | Automatisches Deployment bei Push auf `main` (ADR-0005, Runbook 1.13) | erledigt |
| 7 | Schrift: Mindestgrössen anheben + Regler «Schrift A− A+» | erledigt |
| 8 | Updates der Container-Images: wöchentlicher CI-Lauf + Dependabot (TDR-0008), Actions auf Node 24 | erledigt |
| 9 | Backup-Container: Zombie-Prozesse würden `pids_limit` füllen → Backups fallen aus | erledigt |

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
  Hinweis zeigen, `"verified"` → wieder verbergen). Das Event bubbelt nicht → Listener in der
  Capture-Phase am `document`; wirkt so auch nach HTMX-Swaps. CSP-konform, kein Inline-JS.
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

### 8 · Updates der Container-Images

**Erledigt 2026-10-14** (TDR-0008): Dependabot statt Renovate (keine Dritt-App), Dockerfiles mit
direkten `FROM`-Pins, PostgreSQL-Pins per Test + `scripts/sync-image-pins.sh`, Actions auf Node 24.
Ursprünglicher Plan: Basis-Images (Python, PostgreSQL, Caddy, Backup) sind per Digest gepinnt – `apt`
auf dem Server aktualisiert sie nicht (Runbook 6). Umsetzung:
- `ci.yml`: zusätzlicher Trigger `schedule:` (wöchentlich) – der Trivy-Scan meldet dann neue,
  behebbare CVEs der Images, auch ohne Push.
- Renovate (oder Dependabot) für Docker-Digests, `uv` und GitHub-Actions; vorher prüfen, ob das
  Werkzeug die `ARG`-basierten `FROM`-Zeilen in den Dockerfiles erkennt.
- Update-PRs laufen wie Code: CI → Merge nach `main` → automatisches Deployment.

### 9 · Zombie-Prozesse im Backup-Container

Befund 2026-10-14 (Login-Meldung «7 zombie processes»): alles `ssh`-Prozesse von restic (SFTP),
Elternprozess `crond` = PID 1 im Container `atem_backup`. `crond` räumt beendete Enkelprozesse
nicht ab; pro Backup bleiben ~2 Zombies. Sie zählen zu `pids_limit: 128` → nach rund zwei
Monaten hätte der Container keine Prozesse mehr starten können, Backups wären still ausgefallen.
Fix: `init: true` für `backup` und `restore` (Docker-Init räumt ab; lokal nachgewiesen: ohne Init
1 Zombie, mit Init 0). Nach dem Deploy prüfen: `ps -eo stat | grep -c '^Z'` → 0.

## Später (erfasst, nicht eingeplant)

- ~~**Server: Zeitzone prüfen und Update-Zeit vor den Neustart legen.**~~ **Erledigt 2026-10-14**
  (Cloud config + Runbook 6.1; Updates 04:30, Neustart 05:30). Meldung 2026-10-14 06:30 CEST:
  «The system will reboot at Thu 2026-10-15 05:30 CEST». **Geprüft 2026-10-14:** Zeitzone stimmt
  (`timedatectl` → `Europe/Zurich (CEST, +0200)`); `apt-daily-upgrade.timer` lief 06:03, nächster
  Lauf 06:57 – also immer *nach* dem Neustart-Fenster 05:30 → jeder Neustart wartet bis ~23 h.
  Lösung: Override `/etc/systemd/system/apt-daily-upgrade.timer.d/override.conf` mit
  `OnCalendar=` (leeren) + `OnCalendar=*-*-* 04:30` und `RandomizedDelaySec=20m` → Neustart in
  derselben Nacht; in Cloud-Config und Runbook 6.1 aufnehmen (Sonntag: `restic check` 04:15 ist
  kein Konflikt, da nur der Neustart stört).
- HEAD-Anfragen auf Seiten (z. B. `curl -I https://www.pusterum.be/`) liefern 405 statt 200.
  Für Besucher irrelevant, aber Uptime-Monitore prüfen teils per HEAD → Fehlalarm. GET-Routen
  auch für HEAD freigeben (Litestar) oder Monitor auf GET stellen.

- Benachrichtigung bei fehlgeschlagenem Deployment (heute nur im Server-Journal), z. B. Ping an
  einen Uptime-/Healthcheck-Dienst aus `pusterum-deploy.sh`.
- Litestar-Deprecations (~20 000 Warnungen in `pytest`): Pfadparameter mit `FromPath[…]` bzw.
  `Annotated[…, PathParameter()]` und Dependencies mit `NamedDependency[…]` deklarieren – sonst
  Bruch mit Litestar 3.0.
