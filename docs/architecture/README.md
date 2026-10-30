# Architektur-Dokumentation – PUSTERUM

Alle Diagramme werden ausschliesslich mit **Mermaid** direkt in Markdown gepflegt (keine separaten
`.puml`/`.mmd`-Kopien mehr, die auseinanderlaufen).

| Dokument | Inhalt |
| :--- | :--- |
| [`uml_class_diagram.md`](uml_class_diagram.md) | Schichten, Entitäten, Ports, Adapter, Controller |
| [`sequence_diagrams.md`](sequence_diagrams.md) | Seitenaufruf (CSP), Kontaktformular (ALTCHA), Admin-Login (2FA), Inline-Editing, Start & Backups, Release & Deployment mit Alarmierung |
| [`../ops/runbook.md`](../ops/runbook.md) | Betrieb: Erstinstallation, Deployment, Backups/Restore, Notfälle (verschlüsselt) |
| [`../ops/private/systemuebersicht.md`](../ops/private/systemuebersicht.md) | Gesamtsystem mit Anbietern und Abhängigkeiten, ArchiMate-artig (verschlüsselt) |
| [`../ops/private/wartung.md`](../ops/private/wartung.md) | Wiederkehrende Wartung mit Protokoll (verschlüsselt) |
| [`../../CHANGELOG.md`](../../CHANGELOG.md) | Versionen und Änderungen (TDR-0009) |

## Entscheidungen

* [ADR-0001: Tech-Stack & Architecture Blueprint](../adr/ADR-0001-tech-stack-and-architecture-blueprint.md)
* [ADR-0002: Live In-Context Inline-Editing & Versionierung](../adr/ADR-0002-live-inline-content-editing-and-versioning-system.md)
* [ADR-0003: Persistente Medien & Produktions-Persistenz](../adr/ADR-0003-persistent-media-storage-and-production-persistence.md)
* [ADR-0004: Security-Architektur](../adr/ADR-0004-security-architecture.md)
* [ADR-0005: Automatisches Deployment per Pull-Prinzip](../adr/ADR-0005-continuous-deployment.md)
* [ADR-0006: Datenschutz und Löschkonzept (DSG/DSV)](../adr/ADR-0006-datenschutz-loeschkonzept.md) (proposed)
* [TDR-0001: Theme & organische Formen](../tdr/TDR-0001-dynamic-theme-and-organic-shapes-engine.md)
* [TDR-0002: Pusteblumen-Effekte](../tdr/TDR-0002-dandelion-ambient-effects-engine.md)
* [TDR-0003: Zitat-Band & Datenmigrationen](../tdr/TDR-0003-quote-rotator-and-content-migrations.md)
* [TDR-0004: ALTCHA statt Drittanbieter-CAPTCHA](../tdr/TDR-0004-altcha-captcha.md)
* [TDR-0005: Tailwind-Build, Alpine-CSP & strikte CSP](../tdr/TDR-0005-tailwind-build-and-strict-csp.md)
* [TDR-0006: Backups mit restic](../tdr/TDR-0006-restic-backups.md)
* [TDR-0007: SSH-Zugang über WireGuard](../tdr/TDR-0007-ssh-via-wireguard.md)
* [TDR-0008: Updates mit Dependabot](../tdr/TDR-0008-dependency-updates-dependabot.md)
* [TDR-0009: Versionierung und Releases](../tdr/TDR-0009-versioning-and-releases.md)
* [TDR-0010: Verwaltung der Kontaktanfragen](../tdr/TDR-0010-kontaktanfragen-workflow.md) (proposed)
* [TDR-0011: Zeilenumbrüche in Inhaltsblöcken](../tdr/TDR-0011-zeilenumbrueche-inhaltsbloecke.md)
* [TDR-0012: Kontaktanfragen verschlüsselt speichern](../tdr/TDR-0012-kontaktanfragen-verschluesselt.md)
* [TDR-0013: Löschprotokoll und erneutes Löschen nach einem Restore](../tdr/TDR-0013-loeschprotokoll-und-restore.md)
* [TDR-0014: Reihenfolge der Abschnitte im Design-Studio](../tdr/TDR-0014-reihenfolge-der-abschnitte.md)
* [TDR-0015: Links in formatierten Texten](../tdr/TDR-0015-links-im-rich-text.md)
* Vorlagen: [ADR](../adr/template.md) · [TDR](../tdr/template.md)
