# Tech-Debt: Datenschutz, Kontaktanfragen und Admin-Konten

> Stand 2026-10-16, Grundlage: Analyse des Codes (v1.1.0). Entscheide: [ADR-0006](../adr/ADR-0006-datenschutz-loeschkonzept.md)
> (Löschkonzept nach DSG/DSV) und [TDR-0010](../tdr/TDR-0010-kontaktanfragen-workflow.md)
> (Verwaltung der Kontaktanfragen). Vorgänger: [2026-10-13](2026-10-13-techdebt-mobile-ux-und-deployment.md).

Prio: **P1** rechtlich oder betrieblich nötig, **P2** Arbeitsalltag der Praxis, **P3** Verbesserung.
Aufwand: **S** bis halber Tag, **M** 1-2 Tage, **L** mehr.

## Übersicht

| # | Thema | Prio | Aufwand | Abhängig von | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | CLI `reset-password` | P1 | S | - | offen |
| 2 | Admin-Konto deaktivieren / löschen | P1 | S | - | offen |
| 3 | Zähler im Dashboard falsch ab 51 Anfragen | P1 | S | - | offen |
| 4 | Löschen auf Anfrage + Löschprotokoll + `reapply-deletions` | P1 | M | ADR-0006 | offen |
| 5 | Fristen je Status, IP-Anonymisierung, Retention-Lauf einmal pro Tag | P1 | M | 4, TDR-0010 (Status) | offen |
| 6 | Datenschutzerklärung + Hinweis im Kontaktformular | P1 | S | Entscheide 4/5/8 | offen |
| 7 | Log-Fristen: journald 30 Tage, Proxy-Log mit gekürzter IP | P1 | S | - | offen |
| 8 | Benachrichtigungsmail ohne Anfragetext | P1 | S | Entscheid Praxis | offen |
| 9 | Runbook: Auskunfts-/Löschbegehren, Datenpanne, Restore + `reapply-deletions` | P1 | S | 4 | offen |
| 10 | Auftragsbearbeitung prüfen, Kurzverzeichnis (verschlüsselt) | P1 | S | - | offen |
| 11 | Statusmodell + Verlauf (Migration) | P2 | M | TDR-0010 | offen |
| 12 | Liste: Filter, Suche, Sortierung, Paging | P2 | M | 11 | offen |
| 13 | Detailansicht: Notizen, Verlauf, «Antworten», Wiedervorlage | P2 | M | 11 | offen |
| 14 | Auskunfts-Export pro Person (JSON) | P2 | S | 4 | offen |
| 15 | Anfragetext verschlüsselt in der Datenbank | P3 | M | - | offen |
| 16 | Seite «Admin-Konten» (letzter Login, 2FA, aktiv) | P3 | S | 2 | offen |
| 17 | Gedankenstriche im Repo vs. METAS-Regel | P3 | S | Entscheid | offen |

## Details

### 1 · CLI `reset-password` (P1)

Heute gibt es keinen Weg, ein vergessenes Passwort zurückzusetzen. Der Umweg «neues Konto anlegen»
scheitert an der eindeutigen E-Mail-Adresse. Umsetzung:

* `python -m atem.cli reset-password --email …`: fragt das neue Passwort zweimal ab (oder liest
  `ATEM_ADMIN_PASSWORD`), prüft es mit den bestehenden Regeln (`_validate_new_password`, mindestens
  12 Zeichen).
* Setzt den Hash, erhöht `session_version` (alle Sitzungen beendet), hebt eine Sperre auf
  (`failed_login_count`, `locked_until`). Die 2FA bleibt; bei verlorenem Gerät zusätzlich `reset-2fa`.
* Schickt der Kontoinhaberin eine Sicherheitsmail «Passwort wurde zurückgesetzt» (bestehender
  Mailversand, analog zur Sperr-Mail).
* Tests wie bei `unlock`/`reset-2fa`; Runbook 4.1 ersetzt den Umweg.

### 2 · Admin-Konto deaktivieren / löschen (P1)

`users.is_active` existiert und wird beim Login und bei jeder Sitzung geprüft, aber nichts setzt es.

* `deactivate-admin --email` setzt `is_active = false` und erhöht `session_version`. Rückgängig mit
  `activate-admin`.
* `delete-admin --email` löscht das Konto; `recovery_codes` folgen per `CASCADE`. Inhaltsversionen
  behalten `author_name` (kein Fremdschlüssel).
* Schutz: Das letzte aktive Admin-Konto lässt sich weder deaktivieren noch löschen.
* Runbook 1.10: Der SQL-Befehl zum Deaktivieren wird durch den CLI-Befehl ersetzt.

### 3 · Zähler im Dashboard (P1, Fehler)

«Gesamt» und «Neu» zählen nur die 50 angezeigten Zeilen. Kurzfristig mit `COUNT`-Abfragen beheben
(Repository-Methode `count_by_status`); dauerhaft mit den Status-Reitern aus #12.

### 4 · Löschen auf Anfrage (P1, ADR-0006)

* Admin-Button «Alle Anfragen dieser Person löschen» und CLI `forget-person --email`.
* Findet Anfragen über den HMAC-Hash der normalisierten Adresse.
* Neue Tabelle `deletion_log` (IDs, E-Mail-HMAC, Zeitpunkt, Admin; keine Klartextdaten) mit eigener
  Frist.
* CLI `reapply-deletions` löscht nach einem Restore erneut alles aus dem Protokoll; `restore.sh` ruft
  es automatisch auf.

### 5 · Fristen und IP-Anonymisierung (P1, ADR-0006)

* Fristen: «Erledigt» + 6 Monate, Spam 7 Tage, sonst spätestens 12 Monate nach Eingang.
* `ip_address` nach 7 Tagen auf `NULL` (die Limits brauchen höchstens 24 h).
* Der Retention-Lauf läuft heute in jedem Worker. Künftig nur einmal mit PostgreSQL-Advisory-Lock.

### 6 · Datenschutzerklärung und Formular (P1)

* Texte per Datenmigration aktualisieren (TDR-0003, `replace_default_texts`):
  * Fristen;
  * Backups mit maximaler Dauer;
  * Benachrichtigung per Mail;
  * Hosting in Deutschland statt «Deutschland oder Finnland»;
  * Gesundheitsdaten;
  * Auskunft und Löschung mit 30 Tagen.
* Kontaktformular: Hinweis «Bitte keine ausführlichen Gesundheitsangaben» und ein klickbarer Link
  auf die Datenschutzerklärung (heute nur Text).
* Die Texte bleiben im Admin bearbeitbar; die Praxisinhaberin prüft sie vor dem Release.

### 7 · Log-Fristen (P1)

* journald auf dem Server: `MaxRetentionSec=30day` (Cloud config + Runbook 6), weil die App bei
  Login-Ereignissen IPs loggt (fail2ban-Schnittstelle).
* Reverse-Proxy-Zugriffslog: IP mit `ip_mask` kürzen oder das Zugriffslog abschalten; heute rotiert es
  nur nach Grösse.

### 8 · Benachrichtigungsmail ohne Anfragetext (P1, Entscheid offen)

Vorschlag nach ADR-0006: nur Vorname, Betreff und Link ins Admin. Entscheid der Praxisinhaberin:
Komfort «Antworten aus dem Mailprogramm» gegen keine Kopie von Gesundheitsdaten im Postfach.

### 9 · Runbook-Prozesse (P1)

Auskunfts- und Löschbegehren (Identität, 30 Tage, Vorlage, Protokoll), Datenpanne nach Art. 24 DSG,
Restore mit `reapply-deletions` als Pflichtschritt (3.3).

### 10 · Auftragsbearbeitung und Verzeichnis (P1)

AVV/DPA mit Hoster, Mail-Provider und Backup-Speicher prüfen und den Ablageort im verschlüsselten
Betriebsordner vermerken. Ein kurzes freiwilliges Verzeichnis der Bearbeitungstätigkeiten unter
`docs/ops/private/` anlegen.

### 11-13 · Verwaltung der Kontaktanfragen (P2, TDR-0010)

* Status Neu, In Bearbeitung, Beantwortet, Erledigt, Spam mit Verlauf.
* Liste mit Reitern, Suche, Zeitraum, Sortierung, Paging und Hinweisen («überfällig», «Wiedervorlage»,
  «wird gelöscht am»).
* Detailansicht mit Notizen, Verlauf, «Antworten» (`mailto:`), Wiedervorlage und Zuweisung.

### 14 · Auskunfts-Export (P2)

`export-person --email` (CLI und Admin) liefert alle gespeicherten Daten einer Person als JSON.

### 15 · Anfragetext verschlüsselt speichern (P3)

Freitext und Telefonnummer mit dem bestehenden `ISecretCipher` (Fernet) verschlüsseln. Schützt
Gesundheitsdaten zusätzlich, falls Datenbank oder Dump abfliessen. Die Suche (#12) bleibt dann auf
Name, E-Mail und Betreff beschränkt.

### 16 · Seite «Admin-Konten» (P3)

Nur lesend: E-Mail, aktiv, 2FA eingerichtet, letzter Login. Hilft bei der halbjährlichen Kontrolle im
Wartungsplan.

### 17 · Gedankenstriche (P3, Entscheid offen)

Die METAS-Richtlinie verbietet Gedankenstriche (U+2013, U+2014) in Dateien. Das Repo nutzt sie in
Texten, und das Changelog-Format (Überschrift `## [x.y.z]`, Gedankenstrich, Datum) ist in `tests/test_versioning.py` und
`scripts/release-notes.sh` fest verankert. Entscheid: nur neue Inhalte ohne Gedankenstrich, oder Format,
Test und bestehende Texte umstellen. Seitentexte für Besucher sind davon getrennt zu betrachten.

## Offene Entscheide

| Frage | Vorschlag | Wer |
| :--- | :--- | :--- |
| Fristen für Anfragen | Erledigt + 6 Monate, Spam 7 Tage, max. 12 Monate | Praxisinhaberin |
| Benachrichtigungsmail mit oder ohne Text | ohne Text | Praxisinhaberin |
| Namen der Status | Neu, In Bearbeitung, Beantwortet, Erledigt, Spam | Praxisinhaberin |
| Freiwilliges Verzeichnis | ja, kurz | Betreiber |
| Gedankenstriche | nur neue Inhalte | Betreiber |
| Juristische Prüfung des Löschkonzepts | ja, vor Umsetzung von #4-#8 | Betreiber |

## Weitere Befunde (klein, ohne eigene Nummer)

* Branch-Präfixe künftig nach Richtlinie: `feature/`, `fix/`, `hotfix/`, `chore/`, `docs/`.
* Die E2E-Tests teilen den Datenbankzustand (z. B. Kinder-Modus, Farbpreset); Tests deshalb ohne feste
  Annahmen über Theme-Farben schreiben oder den Zustand pro Test zurücksetzen.
* Zurückgestellt aus 2026-10-15: Dependabot Auto-Merge für grüne Minor/Patch-PRs und monatliches
  Intervall.
