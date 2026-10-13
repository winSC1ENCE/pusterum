# Architektur-Dokumentation – PUSTERUM

Alle Diagramme werden ausschliesslich mit **Mermaid** direkt in Markdown gepflegt (keine separaten
`.puml`/`.mmd`-Kopien mehr, die auseinanderlaufen).

| Dokument | Inhalt |
| :--- | :--- |
| [`uml_class_diagram.md`](uml_class_diagram.md) | Schichten, Entitäten, Ports, Adapter, Controller |
| [`sequence_diagrams.md`](sequence_diagrams.md) | Seitenaufruf (CSP), Kontaktformular (ALTCHA), Admin-Login (2FA), Inline-Editing, Start & Backups |
| [`../ops/runbook.md`](../ops/runbook.md) | Betrieb: Erstinstallation, Deployment, Backups/Restore, Notfälle |

## Entscheidungen

* [ADR-0001: Tech-Stack & Architecture Blueprint](../adr/ADR-0001-tech-stack-and-architecture-blueprint.md)
* [ADR-0002: Live In-Context Inline-Editing & Versionierung](../adr/ADR-0002-live-inline-content-editing-and-versioning-system.md)
* [ADR-0003: Persistente Medien & Produktions-Persistenz](../adr/ADR-0003-persistent-media-storage-and-production-persistence.md)
* [ADR-0004: Security-Architektur](../adr/ADR-0004-security-architecture.md)
* [ADR-0005: Automatisches Deployment per Pull-Prinzip](../adr/ADR-0005-continuous-deployment.md)
* [TDR-0001: Theme & organische Formen](../tdr/TDR-0001-dynamic-theme-and-organic-shapes-engine.md)
* [TDR-0002: Pusteblumen-Effekte](../tdr/TDR-0002-dandelion-ambient-effects-engine.md)
* [TDR-0003: Zitat-Band & Datenmigrationen](../tdr/TDR-0003-quote-rotator-and-content-migrations.md)
* [TDR-0004: ALTCHA statt Drittanbieter-CAPTCHA](../tdr/TDR-0004-altcha-captcha.md)
* [TDR-0005: Tailwind-Build, Alpine-CSP & strikte CSP](../tdr/TDR-0005-tailwind-build-and-strict-csp.md)
* [TDR-0006: Backups mit restic](../tdr/TDR-0006-restic-backups.md)
* [TDR-0007: SSH-Zugang über WireGuard](../tdr/TDR-0007-ssh-via-wireguard.md)
* Vorlagen: [ADR](../adr/template.md) · [TDR](../tdr/template.md)
