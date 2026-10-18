# TDR-0013: Löschprotokoll und erneutes Löschen nach einem Restore

* **Status:** accepted (umgesetzt 2026-10-18)
* **Date:** 2026-10-18
* **Author:** Betreiber (Technik)
* **Scope:** `ContactService.delete_message`/`forget_person`/`reapply_deletions`, Tabelle
  `deletion_log` (Migration `0021_deletion_log`), CLI `forget-person` und `reapply-deletions`,
  `docker/entrypoint.sh`, `docker/backup/restore.sh`

## Problem / Scope

Eine Person kann verlangen, dass ihre Anfragen gelöscht werden (ADR-0006). Die Backups enthalten sie
bis zu 6 Monate weiter. Nach einem Restore wären gelöschte Anfragen wieder da. Bisher musste der
Betreiber dafür IDs von Hand aus dem Protokoll löschen (Runbook 7.3), was leicht vergessen geht.

## Technical Decision

* **Protokoll:** Jede Löschung von Hand (einzelne Anfrage oder alle einer Adresse) schreibt pro
  Anfrage einen Eintrag in `deletion_log`: Nachrichten-ID, Grund, gepfefferter Hash der Adresse,
  Admin, Zeitpunkt. Kein Klartext. Die automatische Frist-Löschung schreibt nichts, weil der nächste
  Lauf zurückgeholte abgelaufene Anfragen ohnehin wieder löscht.
* **Erneut löschen nur nach ID**, nicht nach Hash: Sonst würden neue Anfragen derselben Person, die
  nach dem Löschen eingegangen sind, mitgelöscht.
* **Automatisch beim Start:** Der Entrypoint führt nach den Migrationen `reapply-deletions` aus.
  Normalerweise löscht das nichts; nach einem Restore löscht es die protokollierten Anfragen, bevor
  die App Anfragen anzeigt.
* **Protokoll übersteht den Restore:** Der Snapshot enthält eine ältere Fassung von `deletion_log`.
  `restore.sh` sichert deshalb die aktuellen Einträge vor `pg_restore` und führt sie danach wieder
  ein (`ON CONFLICT DO NOTHING`; unbekannte Admins werden zu `NULL`).
* **Frist:** Einträge werden nach 213 Tagen gelöscht (Retention-Lauf). Die ältesten Backups sind
  6 Monate alt (restic `--keep-monthly 6`).

## Rationale & Trade-offs

* **Why this approach:**
  * kein Handgriff mehr im Normalfall; der Pflichtschritt aus dem Runbook kann nicht vergessen
    werden;
  * keine Personendaten im Protokoll; der Hash belegt bei Bedarf, wessen Begehren es war.
* **Grenzen:** Beim Restore des ganzen Servers (Hetzner-Backup) ist auch das Protokoll alt. Dafür
  bleiben die IDs im verschlüsselten Datenschutz-Protokoll die Reserve (Runbook 7.3).
* **Alternatives evaluated:**
  * Protokoll als Datei ausserhalb der Datenbank: geht beim Verlust des Servers ebenso verloren und
    braucht eigenes Backup.
  * Erneut löschen nach Adress-Hash: löscht auch neue, berechtigte Anfragen derselben Person.
  * Backups beim Löschen umschreiben: mit restic nicht praktikabel, die Snapshots sind unveränderlich.
* **Impact on existing code:**
  * `delete_message` protokolliert jetzt; neue Admin-Route `POST /admin/messages/{id}/forget`.
  * Runbook 3.3, 7.2, 7.3 und das Datenschutz-Protokoll beschreiben den neuen Ablauf.
