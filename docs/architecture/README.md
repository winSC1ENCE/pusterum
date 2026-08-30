# Architektur-Dokumentation & Diagramme: Atemtherapie Webapplikation

Willkommen im zentralen Architektur-Verzeichnis des Projekts. Hier finden sich alle Architekturdiagramme sowohl als **PlantUML (`.puml`)**, als **Mermaid (`.mmd`)** sowie eingebettet in Markdown-Dokumenten mit ausführlicher technischer Erläuterung.

---

## 1. UML-Klassendiagramme (Klassen & Interfaces)

* **PlantUML-Datei:** [`class_diagram.puml`](class_diagram.puml)
* **Mermaid-Datei:** [`class_diagram.mmd`](class_diagram.mmd)
* **Dokumentation mit Erläuterungen:** [`uml_class_diagram.md`](uml_class_diagram.md)

### Abgedeckte Schichten:
- **Domain Layer:** `BaseEntity`, `TherapistProfile`, `Competency`, `ServiceOffering`, `PracticeInfo`, `ContactMessage`, `User`, `ContentBlock`, `ContentBlockVersion`, `ThemeConfig`
- **Domain Ports (ABCs):** `IProfileRepository`, `IContactRepository`, `IUserRepository`, `IContentRepository`, `IThemeRepository`, `IEmailService`, `IPasswordHasher`
- **Infrastructure Adapters:** `SqlAlchemyProfileRepository`, `SqlAlchemyContactRepository`, `SqlAlchemyUserRepository`, `SqlAlchemyContentRepository`, `SqlAlchemyThemeRepository`, `SmtpEmailService`, `MockEmailService`, `Argon2PasswordHasher`
- **Application Layer:** `ProfileService`, `ContactService`, `AuthService`, `ContentService`, `ThemeService`
- **Presentation Layer:** `PublicController`, `AdminController`, `HealthController`

---

## 2. Sequenzdiagramme (Interaktions-Workflows)

* **Gesamtdokumentation aller Abläufe:** [`sequence_diagrams.md`](sequence_diagrams.md)

### Einzeldateien nach Prozess:

| Workflow / Anwendungsfall | PlantUML (`.puml`) | Mermaid (`.mmd`) |
| :--- | :--- | :--- |
| **1. HTMX Kontaktformular & Benachrichtigung** | [`contact_flow_sequence.puml`](contact_flow_sequence.puml) | [`contact_flow_sequence.mmd`](contact_flow_sequence.mmd) |
| **2. Public Page Rendering & DI Lifecycle** | [`page_render_sequence.puml`](page_render_sequence.puml) | [`page_render_sequence.mmd`](page_render_sequence.mmd) |
| **3. Admin Authentifizierung & Session Flow** | [`admin_auth_sequence.puml`](admin_auth_sequence.puml) | [`admin_auth_sequence.mmd`](admin_auth_sequence.mmd) |
| **4. Live In-Context Inline-Editing & Versioning** | [`inline_edit_versioning_sequence.puml`](inline_edit_versioning_sequence.puml) | [`inline_edit_versioning_sequence.mmd`](inline_edit_versioning_sequence.mmd) |

---

## 3. Architecture Decision Records (ADRs)

* [**ADR-0001: Tech-Stack & Architecture Blueprint**](../adr/ADR-0001-tech-stack-and-architecture-blueprint.md)
* [**ADR-0002: Live In-Context Inline-Editing & Versionierungssystem**](../adr/ADR-0002-live-inline-content-editing-and-versioning-system.md)
* [**ADR-Vorlage (MADR Standard)**](../adr/template.md)
* [**TDR-Vorlage (Micro-ADR / Technische Entscheidungen)**](../tdr/template.md)
