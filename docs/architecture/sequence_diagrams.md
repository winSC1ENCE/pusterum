# Sequenzdiagramme: Atemtherapie Webapplikation

> **Übersicht:** Detaillierte Sequenzabläufe für alle Kernprozesse der Webapplikation (Klienten-Interaktion, HTMX-Events, E-Mail-Dispatching, Authentifizierung und Inhaltsverwaltung).

---

## 1. HTMX Kontaktformular & Benachrichtigungs-Workflow

Visualisiert das Absenden einer Terminanfrage über das HTMX-Frontend mit Anti-Spam-Prüfung, Datenbankpersistierung und asynchronem Mail-Versand.

```mermaid
sequenceDiagram
    autonumber
    actor Klient as Klient (Browser)
    participant Caddy as Caddy Proxy (HTTPS / TLS)
    participant Controller as PublicController (Litestar)
    participant ContactSvc as ContactService (Application)
    participant Repo as SqlAlchemyContactRepository
    participant DB as PostgreSQL 16 (asyncpg)
    participant Mailer as IEmailService (SMTP / Mock)
    actor Therapeutin as Therapeutin (E-Mail)

    Klient->>Caddy: POST /contact (Form Data: Name, Mail, Msg, Honeypot)
    Caddy->>Controller: Reverse Proxy Request

    activate Controller
    Controller->>ContactSvc: submit_contact_form(CreateContactMessageDTO, client_ip)
    activate ContactSvc

    Note over ContactSvc: 1. Anti-Spam Honeypot Prüfung
    alt Honeypot Feld ist ausgefüllt (Spam-Bot)
        ContactSvc-->>Controller: raise ValidationException("Spam detected")
        Controller-->>Klient: HTMX Swap: Fehlermeldung im Formular
    else Gültige Anfrage
        Note over ContactSvc: 2. Domain-Entity erzeugen & speichern
        ContactSvc->>Repo: create_message(ContactMessage)
        activate Repo
        Repo->>DB: INSERT INTO contact_messages (...)
        DB-->>Repo: Stored Row (UUID, Timestamps)
        Repo-->>ContactSvc: ContactMessage Entity
        deactivate Repo

        Note over ContactSvc: 3. E-Mail Benachrichtigungen
        par Benachrichtigung an Therapeutin
            ContactSvc->>Mailer: send_contact_notification(ContactMessage)
            activate Mailer
            Mailer->>Therapeutin: E-Mail: Neue Anfrage von Klient
            Mailer-->>ContactSvc: Delivery OK
            deactivate Mailer
        and Empfangsbestätigung an Klient
            ContactSvc->>Mailer: send_contact_confirmation(ContactMessage)
            activate Mailer
            Mailer->>Klient: E-Mail: Bestätigung des Eingangs
            Mailer-->>ContactSvc: Delivery OK
            deactivate Mailer
        end

        ContactSvc-->>Controller: ContactMessageResponseDTO
        deactivate ContactSvc

        Controller-->>Caddy: 200 OK (contact_success.html Template)
        deactivate Controller
        Caddy-->>Klient: HTMX outerHTML Swap (Erfolgsanzeige)
    end
```

---

## 2. Public Page Rendering & Dependency Injection Flow

Visualisiert das Laden der Landing-Page (`GET /`) mit Dependency Injection der Repositories und Services.

```mermaid
sequenceDiagram
    autonumber
    actor Besucher as Besucher (Browser)
    participant Litestar as Litestar ASGI App
    participant DI as DI Container (Lifespan & State)
    participant Ctrl as PublicController
    participant ProfSvc as ProfileService
    participant ProfRepo as SqlAlchemyProfileRepository
    participant DB as PostgreSQL 16
    participant Jinja as JinjaTemplateEngine

    Besucher->>Litestar: GET /
    activate Litestar

    Litestar->>DI: Resolve Dependencies for PublicController.index()
    activate DI
    DI->>DI: Provide AsyncSession (from session_factory)
    DI->>DI: Provide SqlAlchemyProfileRepository(session)
    DI->>DI: Provide ProfileService(profile_repository)
    DI-->>Litestar: ProfileService Instance
    deactivate DI

    Litestar->>Ctrl: index(profile_service)
    activate Ctrl
    Ctrl->>ProfSvc: get_public_profile()
    activate ProfSvc

    par Daten abrufen
        ProfSvc->>ProfRepo: get_profile()
        ProfRepo->>DB: SELECT * FROM therapist_profiles LIMIT 1
        DB-->>ProfRepo: TherapistProfileModel
        ProfRepo-->>ProfSvc: TherapistProfile
    and Kompetenzen abrufen
        ProfSvc->>ProfRepo: get_competencies(active_only=True)
        ProfRepo->>DB: SELECT * FROM competencies WHERE is_active = True
        DB-->>ProfRepo: list[CompetencyModel]
        ProfRepo-->>ProfSvc: list[Competency]
    and Angebote abrufen
        ProfSvc->>ProfRepo: get_services(active_only=True)
        ProfRepo->>DB: SELECT * FROM service_offerings WHERE is_active = True
        DB-->>ProfRepo: list[ServiceOfferingModel]
        ProfRepo-->>ProfSvc: list[ServiceOffering]
    and Praxisinfo abrufen
        ProfSvc->>ProfRepo: get_practice_info()
        ProfRepo->>DB: SELECT * FROM practice_info LIMIT 1
        DB-->>ProfRepo: PracticeInfoModel
        ProfRepo-->>ProfSvc: PracticeInfo
    end

    ProfSvc-->>Ctrl: TherapistProfileDTO
    deactivate ProfSvc

    Ctrl->>Jinja: render("pages/index.html", context={profile})
    activate Jinja
    Jinja-->>Ctrl: HTML5 Response String
    deactivate Jinja

    Ctrl-->>Litestar: Template Response
    deactivate Ctrl

    Litestar-->>Besucher: 200 OK (HTML5 + Tailwind CSS + Alpine.js + HTMX)
    deactivate Litestar
```

---

## 3. Administrator-Authentifizierung & Session Flow

Visualisiert die Anmeldung im Admin-Bereich mit Argon2id Passwort-Prüfung und verschlüsselten Cookies.

```mermaid
sequenceDiagram
    autonumber
    actor Admin as Therapeutin / Admin
    participant Ctrl as AdminController
    participant AuthSvc as AuthService
    participant UserRepo as SqlAlchemyUserRepository
    participant DB as PostgreSQL 16
    participant Hasher as Argon2PasswordHasher
    participant Session as CookieBackend (Litestar)

    Admin->>Ctrl: POST /admin/login (username, password)
    activate Ctrl
    Ctrl->>AuthSvc: authenticate(LoginRequestDTO)
    activate AuthSvc

    AuthSvc->>UserRepo: get_by_username(username)
    activate UserRepo
    UserRepo->>DB: SELECT * FROM users WHERE username = :username
    DB-->>UserRepo: UserModel (mit password_hash)
    UserRepo-->>AuthSvc: User Entity
    deactivate UserRepo

    alt Benutzer nicht gefunden oder inaktiv
        AuthSvc-->>Ctrl: raise AuthenticationException("Ungültige Anmeldedaten")
        Ctrl-->>Admin: Render login.html mit Fehlermeldung
    else Benutzer gefunden
        AuthSvc->>Hasher: verify_password(plain_password, password_hash)
        activate Hasher
        Hasher-->>AuthSvc: True / False (Argon2id Verification)
        deactivate Hasher

        alt Passwort ungültig
            AuthSvc-->>Ctrl: raise AuthenticationException("Ungültige Anmeldedaten")
            Ctrl-->>Admin: Render login.html mit Fehlermeldung
        else Passwort gültig
            AuthSvc-->>Ctrl: UserResponseDTO(id, username, role)
            deactivate AuthSvc

            Ctrl->>Session: Set request.session["user"] = {id, username, role}
            activate Session
            Session-->>Ctrl: Encrypted AES Cookie
            deactivate Session

            Ctrl-->>Admin: 302 Redirect to /admin (Set-Cookie: atem_session=...)
        end
    end
    deactivate Ctrl
```

---

## 4. Inhaltsverwaltung & Angebots-CRUD (Admin)

Visualisiert die Verwaltung von Behandlungsangeboten und Profilinhalten.

```mermaid
sequenceDiagram
    autonumber
    actor Admin as Therapeutin / Admin
    participant Ctrl as AdminController
    participant ProfSvc as ProfileService
    participant Repo as SqlAlchemyProfileRepository
    participant DB as PostgreSQL 16

    Admin->>Ctrl: GET /admin (mit Session Cookie)
    activate Ctrl
    Note over Ctrl: Session-Validierung: User eingeloggt?

    Ctrl->>ProfSvc: get_public_profile()
    activate ProfSvc
    ProfSvc->>Repo: get_profile(), get_services()
    Repo->>DB: SELECT ...
    DB-->>Repo: ORM Records
    Repo-->>ProfSvc: Entities
    ProfSvc-->>Ctrl: TherapistProfileDTO
    deactivate ProfSvc

    Ctrl-->>Admin: 200 OK (Render admin/dashboard.html mit Statistiken & Anfragen)
    deactivate Ctrl
```
