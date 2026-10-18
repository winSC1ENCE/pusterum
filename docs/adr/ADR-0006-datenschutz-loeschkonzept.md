# ADR-0006: Datenschutz und Löschkonzept (DSG/DSV)

* **Status:** accepted (umgesetzt 2026-10-18 ohne juristische Prüfung, Grundlage EDÖB-Empfehlungen)
* **Deciders:** Betreiber (Technik), Praxisinhaberin
* **Date:** 2026-10-16
* **Technical Story:** Tech-Debt [2026-10-16](../plans/2026-10-16-techdebt-datenschutz-und-kontaktanfragen.md)

> Keine Rechtsberatung. Die Rechtsgrundlagen sind nach bestem Wissen zitiert; Punkte mit dem Vermerk
> «nicht verifiziert» und das Gesamtkonzept sollten vor der Umsetzung juristisch geprüft werden
> (z. B. Merkblätter des EDÖB).

## Context and Problem Statement

Über das Kontaktformular erhebt die Website Personendaten (Name, E-Mail, optional Telefon, Betreff,
Freitext, IP). Im Freitext beschreiben Menschen oft ihre Beschwerden; das sind **Gesundheitsdaten** und
damit besonders schützenswerte Personendaten. Heute gilt eine einzige Frist (Löschung 365 Tage nach
Eingang). Es fehlen:

* das Löschen auf Anfrage einer Person über alle Ablageorte (Datenbank, Backups, Postfach, Logs);
* ein Auskunftsweg;
* konkrete Fristen für Logs;
* eine vollständige Information in der Datenschutzerklärung.

Die Benachrichtigungsmail an die Praxis enthält den vollen Anfragetext; damit liegt eine Kopie
ausserhalb jeder Frist im Postfach.

### Rechtsrahmen (Schweiz)

Bundesgesetz über den Datenschutz (DSG, SR 235.1) und Datenschutzverordnung (DSV, SR 235.11),
beide in Kraft seit 1. September 2023.

| Bestimmung | Bedeutung für PUSTERUM |
| :--- | :--- |
| Art. 5 lit. c Ziff. 2 DSG | Daten über die Gesundheit sind besonders schützenswert |
| Art. 6 Abs. 3 DSG | Zweckbindung: nur zur Beantwortung der Anfrage |
| Art. 6 Abs. 4 DSG | Vernichten oder anonymisieren, sobald für den Zweck nicht mehr nötig |
| Art. 8 DSG | Angemessene Datensicherheit (technisch und organisatorisch) |
| Art. 9 DSG | Bearbeitung durch Auftragsbearbeiter (Hosting, Mail, Backup-Speicher) |
| Art. 16 DSG, Anhang 1 DSV | Bekanntgabe ins Ausland; Deutschland gilt als angemessen |
| Art. 19 DSG | Informationspflicht bei der Beschaffung (Datenschutzerklärung) |
| Art. 24 DSG | Meldung von Verletzungen der Datensicherheit an den EDÖB bei hohem Risiko |
| Art. 25 DSG, Art. 18 DSV | Auskunftsrecht; Antwort in der Regel innert 30 Tagen |
| Art. 30-32 DSG | Persönlichkeitsschutz; Art. 32 Abs. 2 lit. c: Löschung oder Vernichtung verlangen |
| Art. 12 DSG, Art. 24 DSV | Verzeichnis der Bearbeitungstätigkeiten; Ausnahme für Unternehmen unter 250 Mitarbeitenden, ausser bei umfangreicher Bearbeitung besonders schützenswerter Daten |

Zu **Backups** enthält das DSG keine ausdrückliche Regel. Das unten gewählte Vorgehen entspricht der
verbreiteten Praxis (nicht verifiziert, juristisch bestätigen lassen).

## Decision Drivers

* Rechtskonformität nach DSG/DSV, insbesondere Art. 6 Abs. 4 und die Betroffenenrechte
* Gesundheitsdaten im Freitext: so kurz wie möglich aufbewahren, so wenig Kopien wie möglich
* Ein Begehren muss in wenigen Minuten vollständig erledigt werden können (CLI + Admin)
* Wiederherstellung aus Backups darf gelöschte Daten nicht wieder sichtbar machen
* Kein zusätzlicher Dienst, kein Mehraufwand im Alltag der Praxis

## Considered Options

* **A: Status quo** - eine Frist (365 Tage), manuelles Löschen einzelner Nachrichten
* **B: Löschkonzept mit Datenkatalog** - Fristen je Datenart, Löschen pro Person, Löschprotokoll,
  erneutes Anwenden nach Restore, Backups laufen in ihrer Rotation aus
* **C: Wie B, zusätzlich gezieltes Löschen in Backups** - Snapshots neu schreiben (`restic rewrite`)

## Decision Outcome

Chosen option: **B**, weil sie die Pflichten mit vertretbarem Aufwand erfüllt. Option C verändert
signierte Backup-Stände, ist fehleranfällig und schwächt die Wiederherstellbarkeit. Eine verkürzte
Rotation bleibt als Stellschraube.

### Datenkatalog und Fristen (Vorschlag)

| Daten | Ort | Zweck | Frist / Löschung |
| :--- | :--- | :--- | :--- |
| Kontaktanfrage (alle Felder) | DB `contact_messages` | Anfrage beantworten | 6 Monate nach Status «Erledigt», spätestens 12 Monate nach Eingang; «Spam» nach 7 Tagen; auf Anfrage sofort |
| IP-Adresse der Anfrage | DB `contact_messages.ip_address` | Missbrauchsschutz (Limits pro Stunde/Tag) | nach 7 Tagen anonymisieren (`NULL`) |
| E-Mail-Hash (HMAC) | DB `contact_messages.email_hash` | max. 1 Bestätigung pro Tag | mit der Anfrage |
| Login-Versuche (IP, Gerät) | DB `login_attempts` | Schutz vor Rateangriffen | 30 Tage (umgesetzt) |
| Captcha-Challenges | DB `used_captcha_challenges` | Replay-Schutz | nach Ablauf, 20 min (umgesetzt) |
| Admin-Konten | DB `users`, `recovery_codes` | Zugang zum Admin | bis zur Deaktivierung; Löschung nach Ausscheiden |
| Autorname von Inhaltsversionen | DB `content_block_versions.author_name` | Nachvollziehbarkeit | bleibt (berechtigtes Interesse); keine weiteren Daten |
| Löschprotokoll | DB `deletion_log` (neu) | Nachweis, erneutes Löschen nach Restore | Message-IDs, E-Mail-HMAC, Zeitpunkt, Admin; Frist = längste Backup-Aufbewahrung + 1 Monat |
| Benachrichtigungsmail | Postfach der Praxis | Hinweis auf neue Anfrage | **ohne Anfragetext** (siehe unten); sonst manuell mitlöschen |
| App-Log (IP bei Login-Ereignissen) | journald auf dem Server | Sicherheit, fail2ban | 30 Tage (`MaxRetentionSec`) |
| Reverse-Proxy-Zugriffslog | Container-Log | Fehler- und Missbrauchsanalyse | IP gekürzt (`ip_mask`) oder kein Zugriffslog; Rotation nach Grösse |
| Datenbank-Backups | Backup-Speicher (verschlüsselt) | Wiederherstellung | Rotation 7 täglich / 4 wöchentlich / 6 monatlich, also max. etwa 6 Monate |
| Server-Backups des Hosters | Hoster | Wiederherstellung des ganzen Servers | Rotation des Hosters (Tage) |

### Prozesse

1. **Löschen auf Anfrage** (Art. 32 Abs. 2 lit. c DSG, Art. 6 Abs. 4 DSG): Identität prüfen
   (Antwort an die bekannte Adresse genügt in der Regel), dann:
   * Admin-Button «Alle Anfragen dieser Person löschen» oder CLI `forget-person --email`;
   * löscht alle Anfragen mit dieser E-Mail-Adresse (über den HMAC-Hash, auch bei abweichender
     Schreibweise);
   * schreibt einen Eintrag ins `deletion_log`, ohne Klartextdaten;
   * Postfach: zugehörige Mails löschen (entfällt, sobald die Benachrichtigung ohne Text kommt);
   * Bestätigung an die Person mit dem Hinweis auf die Backup-Rotation (max. etwa 6 Monate).
2. **Auskunft** (Art. 25 DSG): CLI/Admin-Export `export-person --email` als JSON (alle gespeicherten
   Felder), Antwort innert 30 Tagen.
3. **Wiederherstellung aus Backup**: Direkt nach jedem Restore läuft `reapply-deletions`. Es löscht
   alle im `deletion_log` verzeichneten Anfragen erneut. Das wird Pflichtschritt im Runbook (3.3) und
   in `restore.sh`.
   Umgesetzt 2026-10-18 (TDR-0013): Die App führt es bei jedem Start aus, `restore.sh` bewahrt das
   aktuelle Protokoll über den Restore.
4. **Fristen automatisch**: Der bestehende tägliche Retention-Lauf wird um die Fristen je Status, die
   IP-Anonymisierung und das Löschprotokoll erweitert. Er soll nur einmal pro Tag laufen (Advisory-Lock
   statt pro Worker).
5. **Datenpanne** (Art. 24 DSG): Runbook-Abschnitt mit Einschätzung «hohes Risiko?», Meldung an den
   EDÖB, Information der Betroffenen, Protokoll.

### Postfach: Benachrichtigung ohne Anfragetext

Die Mail an die Praxis enthält künftig nur «Neue Anfrage von <Vorname>, Betreff …» und den Link ins
Admin, ohne Freitext, Telefon und E-Mail-Adresse. Geantwortet wird über «Antworten» im Admin
(`mailto:` mit vorbereitetem Betreff, siehe TDR-0010). Damit entsteht keine unbefristete Kopie von
Gesundheitsdaten im Postfach. **Entschieden** von der Praxisinhaberin am 2026-10-18: ohne Text
(umgesetzt).

### Information und Organisation

* **Datenschutzerklärung** aktualisieren (Datenmigration nach TDR-0003):
  * konkrete Fristen aus der Tabelle oben;
  * Backups mit maximaler Dauer;
  * Benachrichtigung der Praxis per E-Mail;
  * Hosting in Deutschland (heute steht «Deutschland oder Finnland»);
  * Gesundheitsdaten: Bitte nur das Nötigste schreiben;
  * Vorgehen und Frist für Auskunft und Löschung.
* **Kontaktformular**: Hinweis «Bitte keine ausführlichen Gesundheitsangaben» und ein echter Link auf
  die Datenschutzerklärung.
* Umgesetzt 2026-10-18 (Migration `0020_privacy_statement`) nach den Empfehlungen des EDÖB:
  Kurzfassung zuoberst, danach 9 Abschnitte. Ändert sich eine Bearbeitung (Anbieter, Frist,
  Cookie), wird der Text im selben Release angepasst.
* **Auftragsbearbeitung** (Art. 9 DSG): Verträge (AVV/DPA) mit Hoster, Mail-Provider und
  Backup-Speicher prüfen und im verschlüsselten Betriebsordner vermerken.
* **Verzeichnis** (Art. 12 DSG): voraussichtlich nicht Pflicht (kleines Unternehmen, keine
  umfangreiche Bearbeitung). Ein kurzes freiwilliges Verzeichnis im verschlüsselten Ordner
  `docs/ops/private/` dient trotzdem als Übersicht.
* Umgesetzt 2026-10-18: Verzeichnis und Verträge in `docs/ops/private/auftragsbearbeitung.md`.

### Positive Consequences

* Begehren auf Auskunft und Löschung sind in Minuten erledigt und nachweisbar
* Gesundheitsdaten liegen kürzer und an weniger Orten
* Ein Restore macht gelöschte Daten nicht wieder sichtbar
* Die Datenschutzerklärung entspricht der tatsächlichen Bearbeitung

### Negative Consequences

* Gelöschte Daten bleiben bis zum Auslaufen der Backup-Rotation (max. etwa 6 Monate) in
  verschlüsselten Backups; das muss offengelegt werden
* Das Löschprotokoll ist ein pseudonymes Datum (HMAC, IDs) und braucht selbst eine Frist
* Ohne Anfragetext in der Mail ist zum Lesen eine Anmeldung im Admin nötig

## Pros and Cons of the Options

### A: Status quo

* Good, because kein Aufwand
* Bad, because kein vollständiges Löschen auf Anfrage, Kopie im Postfach, Restore stellt gelöschte
  Daten wieder her, Datenschutzerklärung unvollständig

### B: Löschkonzept mit Datenkatalog

* Good, because erfüllt die Pflichten mit bestehenden Mitteln (Retention-Lauf, CLI, Runbook)
* Bad, because Backups enthalten gelöschte Daten bis zum Auslaufen der Rotation

### C: Wie B, zusätzlich Löschen in Backups

* Good, because Daten verschwinden sofort auch aus Backups
* Bad, because Backups neu schreiben ist riskant, aufwendig und bei Server-Backups des Hosters nicht
  möglich

## Links

* Umsetzung: [Tech-Debt 2026-10-16](../plans/2026-10-16-techdebt-datenschutz-und-kontaktanfragen.md)
* [TDR-0010: Kontaktanfragen-Workflow](../tdr/TDR-0010-kontaktanfragen-workflow.md)
* [TDR-0006: Backups mit restic](../tdr/TDR-0006-restic-backups.md)
* [ADR-0004: Security-Architektur](ADR-0004-security-architecture.md)
* [TDR-0003: Datenmigrationen für Standardtexte](../tdr/TDR-0003-quote-rotator-and-content-migrations.md)
* Betrieb: `docs/ops/runbook.md` (verschlüsselt)
