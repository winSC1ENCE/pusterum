# Changelog

Alle nennenswerten Änderungen an PUSTERUM. Format nach [Keep a Changelog](https://keepachangelog.com/de/1.1.0/),
Versionen nach [Semantic Versioning](https://semver.org/lang/de/) (TDR-0009).

- **MAJOR:** inkompatible Änderung, z. B. Daten- oder Betriebsumstellung mit Handarbeit
- **MINOR:** neue Funktion
- **PATCH:** Fehlerbehebung, Updates von Abhängigkeiten

Neue Einträge kommen unter «Unreleased». Der Release-PR `develop` → `main` macht daraus die neue
Version. Nach grüner CI auf `main` entstehen automatisch Tag `vX.Y.Z` und GitHub-Release.

## [Unreleased]

## [1.3.0] - 2026-10-18

### Hinzugefügt

- Neue Seite «Kontaktanfragen» im Admin: Reiter nach Status, Suche nach Name, E-Mail und Betreff,
  Zeitraum, Sortierung und Seiten. Lange unbeantwortete Anfragen sind als «überfällig» markiert.
- Detailansicht jeder Anfrage mit internen Notizen, Verlauf (wer hat wann was geändert), «Antworten»
  per Mailprogramm und Export aller Anfragen einer Adresse für Auskunftsbegehren.
- Die aktuelle Version der Webseite steht unten im Footer.
- Das Kontaktformular verlinkt auf die Datenschutzerklärung und bittet, keine ausführlichen
  Gesundheitsangaben zu schreiben.
- Löschbegehren: In der Detailansicht lassen sich alle Anfragen einer Adresse auf einmal löschen
  (auf dem Server: `forget-person`). Jede Löschung wird ohne Personendaten protokolliert.

### Geändert

- Neue Datenschutzerklärung nach den Empfehlungen des EDÖB: Kurzfassung zuoberst, Fristen je
  Status, Empfänger und Länder, Gesundheitsangaben, Rechte mit Antwort innert 30 Tagen. Bereits
  bearbeitete Abschnitte bleiben unverändert und sollten von Hand geprüft werden.
- Neue Status: Neu, In Bearbeitung, Beantwortet, Erledigt, Spam. «Gelesen» wird zu «In Bearbeitung»,
  «Archiviert» zu «Erledigt». Beim ersten Öffnen wechselt eine neue Anfrage auf «In Bearbeitung».
- Das Dashboard zeigt nur noch die neuesten offenen Anfragen und verlinkt auf die volle Liste.
- Anfragen werden je nach Status gelöscht: «Erledigt» nach 6 Monaten, «Spam» nach 7 Tagen, alle
  anderen spätestens nach 12 Monaten. Liste und Detail zeigen das Löschdatum.

### Sicherheit

- Gelöschte Anfragen bleiben gelöscht, auch nach einer Wiederherstellung aus dem Backup: Die App
  löscht sie beim Start automatisch erneut.
- Die Benachrichtigungsmail enthält nur noch Vorname, Betreff und einen Link ins Admin, weder
  Nachricht noch Telefonnummer noch E-Mail-Adresse. So liegen keine Gesundheitsangaben im Postfach.

## [1.2.0] - 2026-10-18

### Hinzugefügt

- Zitate lassen sich auf dem Handy durch Wischen wechseln, am Computer mit den Pfeiltasten. Nach einem
  manuellen Wechsel bleibt das Zitat die vollen 7 Sekunden stehen.
- Das Menü auf dem Handy schliesst sich auch durch Tippen ausserhalb (abgedunkelter Bereich) und mit
  Escape. Für Screenreader ist erkennbar, ob es offen ist.
- Zeilenumbrüche in allen Texten: Im Live-Editor macht Enter eine neue Zeile, auch in Titeln und kurzen
  Texten (gespeichert wird mit Alt+S oder «Speichern»). Auf der Website erscheint der Umbruch genau so.
- Design-Studio: Schalter «Kontakt: Telefonnummer anzeigen». Ausgeschaltet verschwindet die Nummer im
  Kontaktbereich und im Impressum, bleibt aber gespeichert und im Live-Editor bearbeitbar.
- Betrieb: Befehle zum Zurücksetzen eines vergessenen Passworts (mit Sicherheitsmail an die Person) sowie
  zum Deaktivieren, Reaktivieren und Löschen von Admin-Konten. Das letzte aktive Konto ist geschützt.
- Admin: Seite «Admin-Konten» zeigt alle Konten mit Status, 2FA, Wiederherstellungscodes, letzter
  Anmeldung und letzter Passwortänderung (nur Ansicht).

### Sicherheit

- Datenschutz: Das Zugriffslog speichert IP-Adressen nur noch gekürzt, Server-Logs werden nach 30 Tagen
  gelöscht.
- Datenschutz: Die IP-Adresse einer Kontaktanfrage wird nach 7 Tagen entfernt (sie dient nur dem Schutz vor
  Massenanfragen).
- Datenschutz: Nachrichtentext, Telefonnummer und Notizen von Kontaktanfragen werden verschlüsselt
  gespeichert, auch bestehende. Für Auskunftsbegehren gibt es den Befehl `export-person`.

### Behoben

- Live-Editor: Nach dem Speichern wechselte bei einigen Feldern (z. B. Adresse) die Eingabeart.
- Dashboard: «Eingegangene» und «Neue Anfragen» zählen jetzt alle Anfragen, nicht nur die 50 angezeigten.
- Dashboard: Der Eingang einer Anfrage wird in Schweizer Zeit angezeigt (bisher UTC).

## [1.1.0] – 2026-10-15

Die Gestaltung wirkt jetzt vollständig wie vorgesehen, und die Kopfzeile lässt sich im Design-Studio
einstellen. Beim Deployment läuft eine Datenbank-Migration automatisch (neue Einstellung, Startwert 60 %).

### Hinzugefügt

- Design-Studio: Deckkraft der Kopfzeile einstellbar (Regler «Kopfzeile: Deckkraft», 0 % = Glas-Effekt,
  100 % = deckend; Standard 60 %). Der Seiteninhalt schimmert beim Scrollen wieder verwischt durch.

### Geändert

- Architektur-Dokumentation auf den aktuellen Stand gebracht (Klassen- und Sequenzdiagramme, neu:
  Ablauf von Release, Deployment und Alarmierung).
- Technische Vorbereitung auf Litestar 3: Abhängigkeiten und Pfadparameter sind ausdrücklich
  deklariert, die Tests laufen ohne Veraltet-Warnungen (vorher rund 20 000). Für Besucher ändert sich
  nichts.

### Behoben

- Farbabstufungen der Gestaltung wirken jetzt wie vorgesehen: zarte Hintergründe hinter Logo, Symbolen und
  Häkchen, Hover im Menü. Auf der druckbaren Kinderkarte erscheinen Rahmen
  und Kartenfarben korrekt.

## [1.0.1] – 2026-10-15

Wartungs-Release: aktualisierte Abhängigkeiten und robustere Pipeline. Für Besucher ändert sich nichts.

### Geändert

- Abhängigkeiten aktualisiert (erste Dependabot-Runde):
  - Python-Pakete, u. a. SQLAlchemy 2.1, asyncpg, alembic, pydantic, cryptography und granian;
  - Basis-Images für Python und Debian;
  - Reverse-Proxy Caddy 2.10 → 2.11 (Laufzeit- und Build-Image).
- Dependabot-Updates von Caddy ziehen auch das Build-Image nach (Test und
  `scripts/sync-image-pins.sh`).
- Nach `main` lassen sich nur noch `develop` (Release) und `hotfix/*` mergen. Die CI blockiert
  andere Branches.
- Entwicklung: ruff läuft im pre-commit-Hook in derselben Version wie in der CI.

### Behoben

- CI: Das Caddy-Image wird mit Cache gebaut, Downloads werden bei Netzwerkfehlern wiederholt.
  Daran war der erste Lauf von Release v1.0.0 gescheitert.

## [1.0.0] – 2026-10-14

Erste versionierte Ausgabe. Die Website ist seit dem 2026-10-13 unter `www.pusterum.be` live.

### Hinzugefügt

- Single-Page-Website der Praxis mit Pusteblume-Motiv. Alle Texte und Bilder kann die
  Praxisinhaberin direkt auf der Seite bearbeiten, mit Versionierung der Inhalte.
- Verwaltung im Admin:
  - Angebote und Tarife;
  - Praxisadresse und Anfahrt mit einfacher Formatierung;
  - Design-Studio für Farben und Schriften.
- Kinderbereich mit geführter Atemübung. Er lässt sich über den Schalter «Atmende Blume» ein- und
  ausblenden.
- Kontaktformular:
  - Spamschutz durch ALTCHA;
  - Betreff je Angebot;
  - Ausweichen auf eine E-Mail, wenn die Prüfung nicht laden kann (z. B. hinter Firmen-Proxys).
- Schriftgrösse in drei Stufen, im Mobile-Menü und in der Fusszeile. Die Wahl bleibt nur im Browser
  gespeichert.
- Automatisches Deployment nach grüner CI auf `main`: Branch `production`, Health-Check und
  Rollback (ADR-0005).
- Benachrichtigung bei fehlgeschlagenem Deployment, nicht erreichbarer Website oder fehlendem Backup
  über einen Healthcheck-Dienst.
- Verschlüsselte Backups von Datenbank und Medien auf einen externen Backup-Speicher, mit getestetem
  Restore.
- Wöchentliche Update-PRs (Dependabot) und ein wöchentlicher Sicherheitslauf der CI (TDR-0008).
- Versionierung mit Changelog und automatischen Release-Tags (TDR-0009).

### Sicherheit

- Admin:
  - Anmeldung nur mit persönlicher E-Mail-Adresse;
  - Argon2id und 2FA mit Wiederherstellungscodes;
  - Kontosperre nur für unbekannte Geräte;
  - CSRF-Schutz bei jedem POST.
- Strikte Content-Security-Policy: kein Inline-JS, Alpine als CSP-Build, Tailwind kompiliert.
- Gehärteter Produktions-Stack:
  - Reverse-Proxy mit Rate-Limits, fail2ban über das Journal;
  - SSH nur über VPN (TDR-0007);
  - automatische Sicherheitsupdates mit Neustart in der Nacht.

### Behoben

- Mobile:
  - Das Menü ist auf schmalen Geräten erreichbar.
  - Sprünge zu Ankern landen unter der fixierten Kopfzeile.
  - Die Fusszeile hat genug Kontrast.
- Ein ausgeschalteter Kinderbereich blendet jetzt auch Links und Karte aus.
- Backup-Container: verwaiste Prozesse füllen das Prozesslimit nicht mehr.
- `multidict` 7.1.0 (CVE-2026-104874).
