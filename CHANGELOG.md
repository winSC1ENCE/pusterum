# Changelog

Alle nennenswerten Änderungen an PUSTERUM. Format nach [Keep a Changelog](https://keepachangelog.com/de/1.1.0/),
Versionen nach [Semantic Versioning](https://semver.org/lang/de/) (TDR-0009).

- **MAJOR:** inkompatible Änderung, z. B. Daten- oder Betriebsumstellung mit Handarbeit
- **MINOR:** neue Funktion
- **PATCH:** Fehlerbehebung, Updates von Abhängigkeiten

Neue Einträge kommen unter «Unreleased». Der Release-PR `develop` → `main` macht daraus die neue
Version. Nach grüner CI auf `main` entstehen automatisch Tag `vX.Y.Z` und GitHub-Release.

## [Unreleased]

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
