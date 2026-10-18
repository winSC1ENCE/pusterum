# TDR-0012: Kontaktanfragen verschlüsselt speichern

* **Status:** accepted (umgesetzt 2026-10-18)
* **Date:** 2026-10-18
* **Author:** Betreiber (Technik)
* **Scope:** `SqlAlchemyContactRepository`, `repositories/base.py` (Hooks `_encode`/`_decode`),
  `presentation/bootstrap.py` (`build_contact_cipher`, `build_contact_repository`), Migration
  `0018_encrypt_contact_text`, CLI `export-person`

## Problem / Scope

Im Freitext einer Anfrage beschreiben Menschen oft ihre Beschwerden, also Gesundheitsdaten
(ADR-0006). Diese liegen bisher im Klartext in der Datenbank und damit auch in jedem `pg_dump`.
Fliessen Datenbank oder Dump ab, sind sie direkt lesbar.

## Technical Decision

* **Felder:** `message`, `sender_phone` und `notes` werden mit Fernet (AES-128-CBC + HMAC-SHA256)
  verschlüsselt. Name, E-Mail und Betreff bleiben lesbar, weil Suche (#12) und Löschen pro Person
  (#4) sie brauchen.
* **Schlüssel:** per HKDF aus `SECRET_KEY` abgeleitet, Zweck `atem-contact-cipher`, also getrennt
  vom Schlüssel der TOTP-Geheimnisse. Kein zusätzliches Secret.
* **Ort:** Das Repository ver- und entschlüsselt (Hooks `_encode`/`_decode` der Basisklasse). Domain,
  Services, Templates und E-Mails sehen weiterhin Klartext.
* **Nicht lesbare Werte** (anderer `SECRET_KEY`): Anzeige als «[nicht lesbar: Schlüssel geändert]»,
  Log `contact_field_unreadable` ohne Inhalt. Beim Speichern bleibt der ursprüngliche Geheimtext
  erhalten, er wird nie durch den Platzhalter überschrieben.
* **Bestand:** Migration `0018` verschlüsselt alle vorhandenen Anfragen und ändert `sender_phone`
  auf `Text` (der Geheimtext ist länger als 50 Zeichen). Downgrade entschlüsselt wieder.
* **Auskunft:** Weil `psql` nur noch Geheimtext zeigt, exportiert `python -m atem.cli export-person
  --email …` alle Anfragen einer Person als JSON auf stdout. CLI-Logs gehen deshalb nach stderr.

## Rationale & Trade-offs

* **Why this approach:**
  * schützt Dumps, Backups und einen direkten Datenbankzugriff ohne App-Secrets;
  * nutzt das vorhandene `ISecretCipher` und `cryptography`, keine neue Abhängigkeit;
  * die Verschlüsselung ist an einer Stelle gekapselt und für den Rest der App unsichtbar.
* **Grenzen:** Wer den Server mit `.env` kompromittiert, kann entschlüsseln. Die Massnahme ergänzt
  den Schutz der Backups (restic, verschlüsselt) und ersetzt keine Härtung des Servers.
* **Alternatives evaluated:**
  * PostgreSQL `pgcrypto`: Schlüssel müsste in jeder Abfrage mitgeschickt werden und erscheint
    womöglich in Logs; bindet die Lösung an PostgreSQL (Tests laufen auch auf SQLite).
  * Eigenes Secret `CONTACT_ENCRYPTION_KEY`: unabhängig von `SECRET_KEY`, aber ein weiteres Secret
    für Betrieb und Wiederherstellung. Später möglich, mit einer Migration zum Umschlüsseln.
  * `MultiFernet` mit altem und neuem Schlüssel: würde Schlüsselwechsel ohne Datenverlust erlauben.
    Vorerst nicht nötig, siehe Folgen.
* **Impact on existing code:**
  * **`SECRET_KEY` wechseln macht gespeicherte Anfragen unlesbar** (wie schon die 2FA-Geheimnisse).
    Vor einem Wechsel offene Anfragen beantworten oder exportieren (Runbook 4.1, 7.4).
  * Wiederherstellung auf einem neuen Server braucht denselben `SECRET_KEY` (in Proton Pass).
  * Die Auskunft im Runbook (7.1) nutzt `export-person` statt `psql`.
  * Die Migration braucht beim Deploy den produktiven `SECRET_KEY`; der Container-Entrypoint hat
    ihn bereits.
  * Tests: Geheimtext in der Datenbank, Klartext beim Lesen, falscher Schlüssel, Export und CLI.
