# Plan: Benachrichtigung bei Ausfall und fehlgeschlagenem Deployment

> Status: **geplant, noch nicht umgesetzt** (2026-10-14). Herkunft: Tech-Debt «Später» in
> [`2026-10-13-techdebt-mobile-ux-und-deployment.md`](2026-10-13-techdebt-mobile-ux-und-deployment.md).

## Kontext

Fällt die Website aus oder scheitert ein automatisches Deployment (ADR-0005), merkt das heute
niemand. Fehler stehen nur im Server-Journal. Ziel ist eine Benachrichtigung per Mail, optional
per Push, ohne zusätzliche Software auf dem Server.

**Ansatz: Healthcheck-Dienst nach dem Totmann-Prinzip.** Der Backup-Container unterstützt das
bereits über `HEALTHCHECK_PING_URL`. Der Dienst alarmiert in zwei Fällen:

- ein Ping meldet `/fail`;
- ein erwarteter Ping bleibt aus.

Das Deploy-Skript läuft ohnehin alle 5 Minuten. Künftig prüft es bei jedem Lauf die Live-Website und
pingt das Ergebnis. Alarm gibt es damit bei:

- fehlgeschlagenem Deployment;
- nicht erreichbarer Website;
- ausgefallenem Server oder Netz, weil die Pings dann ausbleiben;
- gestopptem Timer.

Die Backups kommen als zweiter Check dazu. Auf dem Server reicht dafür das vorhandene `curl`.

**HEAD → 405 wird nicht umgesetzt.** Kein Monitor fragt per HEAD an, die Live-Prüfung läuft per GET.
Litestar 2.24 beantwortet HEAD nicht von selbst. Eine Lösung bräuchte einen Eingriff in interne Teile
des ASGI-Handlers.

## Änderungen

1. **`ops/deploy/pusterum-deploy.sh`**: Die Pings laufen zentral über einen `EXIT`-Trap.
   - **Ping-URL:** `DEPLOY_PING_URL` kommt aus `$REPO_DIR/deploy.env`. Das Skript liest nur diese
     Zeile per `sed` und führt die Datei nicht als Shell-Code aus. Eine gesetzte Umgebungsvariable hat
     Vorrang. Ist die URL leer, wird nicht gepingt und alles läuft wie heute.
   - **Melden:** `log()` ersetzt `echo` und merkt sich die letzte Meldung. Der Trap pingt bei Exit 0
     auf `$URL`, sonst auf `$URL/fail`, mit
     `curl -fsS -m 10 --retry 3 --data-raw "<Meldung>"`. So steht die Meldung in der Alarm-Mail. Ein
     fehlgeschlagener Ping wird ignoriert.
   - **Leerlauf:** Ohne neuen Commit, und auch bei einem bereits gemeldeten fehlgeschlagenen Commit,
     prüft ein einzelner `curl` die Live-URL. Ist sie gesund, gibt es einen Erfolgs-Ping. Sonst meldet
     das Skript `FEHLER: Website antwortet nicht (…)` und endet mit `return 1`.
   - **Bekannter fehlgeschlagener Commit:**
     - Er pingt weiterhin `/fail` mit «wartet auf neuen Commit».
     - Der Exit-Code bleibt 0 wie heute, damit `systemctl --failed` nicht alle 5 Minuten anschlägt.
     - Der Check bleibt rot, bis ein neuer Commit gesund läuft. Die Mail kommt nur einmal, beim Wechsel
       des Status.
   - **Ausnahmen:** Kein Ping bei `--dry-run` und wenn ein anderer Lauf die Sperre hält.
   - **Unerwartete Fehler** unter `set -e`, z. B. bei `git fetch`, landen über den Trap ebenfalls auf
     `/fail`.
   - **Server:** Die systemd-Units bleiben unverändert. Das Skript aktualisiert sich mit dem nächsten
     Deployment selbst.
2. **`config/deploy.env.production.example`** (neu): `DEPLOY_PING_URL=` mit Kommentar.
   **`.gitignore`**: `/deploy.env`, wie bei `db.env` und `backup.env`.
3. **`tests/test_deploy_script.py`** (neu): Das Skript läuft per `subprocess` in einem temporären
   Git-Repo mit Bare-Remote, das den Branch `production` simuliert.
   - **Aufbau:** `docker` und `curl` sind Fake-Skripte im `PATH`. Der Fake-`curl` protokolliert seine
     Aufrufe, und ein Steuerfile legt fest, ob die Health-URL gesund ist. `HEALTH_RETRIES=1`,
     `HEALTH_DELAY=0`.
   - **Fälle:**
     - Leerlauf gesund → Erfolgs-Ping.
     - Leerlauf krank → `/fail` und Exit 1.
     - Neuer Commit gesund → Erfolgs-Ping.
     - Neuer Commit krank → Rollback, `/fail`, Marker wird geschrieben.
     - Bekannter fehlgeschlagener Commit → `/fail` und Exit 0.
     - Ohne URL → kein Ping.
     - `--dry-run` → kein Ping.
4. **Doku**
   - **Runbook** (verschlüsselt, dort mit Dienst-Namen):
     - **1.13, neuer Schritt «Benachrichtigung»:** zwei Checks anlegen.
       - «Website & Deployment»: Periode 5 min, Karenz 20 min. Die Karenz deckt lange Deploys und den
         Neustart um 05:30 ab.
       - «Backup»: Periode 1 Tag, Karenz 3 h.
       - Die URLs kommen in `deploy.env` und `backup.env`. Danach das Backup neu starten
         (`up -d backup`) und für jeden Check einen Testalarm auslösen.
     - **Abschnitte 2, 3.1 und 5:** aktualisieren (was bei einem Alarm zu tun ist).
   - **Wartungsplan** (`docs/ops/private/wartung.md`):
     - eine Zeile «Alarmierung» in der Liste der automatischen Abläufe;
     - monatlich das Dashboard ansehen;
     - halbjährlich einen Testalarm auslösen.
   - **ADR-0005:** Nachtrag «Benachrichtigung». Der Nachteil «nur Journal» fällt damit weg.
   - **Tech-Debt-Liste:**
     - Benachrichtigung als erledigt markieren.
     - HEAD → 405 als bewusst nicht umgesetzt eintragen, mit Begründung.

## Verifikation

- `uv run pytest tests/test_deploy_script.py -v`, danach die volle Suite, ShellCheck und die
  Quality-Gates.
- Runbook und `wartung.md` sind verschlüsselt committet: `git cat-file -p HEAD:… | head -c 9`
  ergibt `GITCRYPT`.
- **Nach dem Deployment auf dem Server:**
  1. `deploy.env` anlegen. Innerhalb von 5 Minuten muss der Check auf «up» stehen.
  2. Testalarm auslösen:
     `HEALTH_URL=https://www.pusterum.be/gibtsnicht ops/deploy/pusterum-deploy.sh`.
     Es muss eine Mail kommen.
  3. Der nächste Lauf des Timers muss wieder «up» melden.
