# Sequenzdiagramme – PUSTERUM

> Stand 2026-10-04 (nach Go-Live-Härtung). Mermaid ist die einzige Quelle.

---

## 1. Seitenaufruf (strikte CSP, Theme als Stylesheet)

```mermaid
sequenceDiagram
    autonumber
    actor B as Besucher (Browser)
    participant C as Caddy (TLS, HSTS, Rate-Limit)
    participant M as Middleware-Kette
    participant P as PublicController
    participant S as Content/Offering/ThemeService
    participant DB as PostgreSQL

    B->>C: GET https://www.pusterum.be/
    C->>M: reverse_proxy app:8000
    Note over M: SecurityHeaders → HostValidation → ProxyHeaders<br/>→ RateLimit → Session → CSRF-Cookie
    M->>P: index()
    P->>S: Inhalte, Angebote, Theme laden
    S->>DB: SELECT …
    P-->>B: HTML (keine Inline-Skripte/-Styles) + CSP-Header
    B->>C: GET /static/css/app.css?v=… , /theme.css?v=…, /static/js/…
    C-->>B: kompiliertes CSS, Theme-Variablen, Alpine (CSP-Build), htmx
```

---

## 2. Kontaktformular (ALTCHA, Limits, sichere Mails)

```mermaid
sequenceDiagram
    autonumber
    actor B as Besucher
    participant P as PublicController
    participant CS as ContactService
    participant CAP as AltchaCaptcha
    participant R as ContactRepository
    participant MAIL as SmtpEmailService
    actor T as Praxis (E-Mail)

    B->>P: GET /altcha/challenge
    P->>CAP: create_challenge() (HMAC-signiert, Ablauf 20 min)
    P-->>B: Challenge → Web-Worker löst Proof-of-Work
    B->>P: POST /contact (HTMX, CSRF-Header, form_token, altcha)
    P->>P: Zeit-Token prüfen (≥ 3 s, ≤ 2 h)
    P->>CS: submit_contact_form(dto, ip, payload)
    CS->>CS: Honeypot leer?
    CS->>CAP: verify(payload)
    CS->>R: register_captcha_challenge(id) – Replay-Schutz
    CS->>R: count_messages_from_ip(1 h / 24 h)
    alt Limit überschritten
        CS-->>P: RateLimitedException
        P-->>B: Formular-Karte mit Hinweis
    else ok
        CS->>R: create_message(…, email_hash)
        CS->>MAIL: send_contact_notification (Reply-To = Besucher)
        MAIL-->>T: Neue Anfrage
        CS->>R: confirmation_sent_since(email_hash, 24 h)?
        CS->>MAIL: send_contact_confirmation(Adresse) – fester Text, max. 1×/Tag
        P-->>B: Erfolgs-Karte (nur dieses Partial wird getauscht)
    end
```

---

## 3. Admin-Login mit Zwei-Faktor-Anmeldung

```mermaid
sequenceDiagram
    autonumber
    actor A as Admin
    participant AC as AdminAuthController
    participant AS as AuthService
    participant UR as UserRepository

    A->>AC: POST /admin/login (Benutzer, Passwort, CSRF, Cookie atem_device?)
    AC->>AS: authenticate(dto, ip, device_claim)
    AS->>UR: count_failed_attempts(ip, 15 min) – IP-Limit
    AS->>UR: get_by_username()
    Note over AS: unbekannt → Dummy-Hash (keine Enumeration)
    alt vertrautes Gerät (signiertes Cookie dieses Benutzers)
        AS->>UR: count_failed_device_attempts(device, 15 min) – Limit pro Gerät
    else unbekanntes Gerät
        Note over AS: Kontosperre (exp. Back-off) → generischer Fehler<br/>Beginn einer Sperre → Mail an Kontoinhaberin
    end
    AS->>AS: Argon2id verify
    alt 2FA aktiv
        AS-->>AC: requires_totp
        AC-->>A: Session «pending_2fa» (5 min) → /admin/login/verify
        A->>AC: POST /admin/login/verify (TOTP oder Recovery-Code)
        AC->>AS: verify_second_factor()
        Note over AS: TOTP mit Replay-Schutz (letzter Zeitschritt)<br/>Recovery-Code einmalig (Argon2-Hash)
    end
    AS->>UR: Zähler zurücksetzen, Login protokollieren
    AC-->>A: Neue Session {id, sv=session_version} (Secure, HttpOnly, SameSite=Strict, 12 h)<br/>+ Cookie atem_device (180 Tage, Path=/admin)
    Note over A,AC: Jede Admin-Anfrage: Guard prüft Benutzer + session_version in der DB.<br/>Logout / Passwort- / 2FA-Änderung erhöht session_version → alle Cookies ungültig.
```

---

## 4. Inline-Bearbeitung & Versionierung (ADR-0002)

```mermaid
sequenceDiagram
    autonumber
    actor A as Admin (Live-Editor)
    participant CC as AdminContentController
    participant G as require_admin
    participant CS as ContentService
    participant R as ContentRepository

    A->>CC: POST /admin/content/{key}/save (HTMX, x-csrftoken)
    CC->>G: Session gültig?
    CC->>CS: save_block_content(key, dto, author)
    CS->>CS: Key-Muster & nur existierende Keys<br/>Bildpfad-Muster, max. 10 000 Zeichen
    CS->>R: save_version() → neue unveränderliche Version
    CC-->>A: Block neu gerendert (Render-Hinweise per Allowlist)
    A->>CC: POST …/restore/{n}
    CC->>CS: restore_block_version()
    CC-->>A: HX-Refresh (Seite lädt mit Originalformatierung)
```

---

## 5. Produktionsstart & Backups

```mermaid
sequenceDiagram
    autonumber
    participant D as docker compose
    participant E as entrypoint.sh
    participant AL as Alembic
    participant CLI as atem.cli
    participant G as granian (2 Worker)
    participant BK as backup (cron)
    participant SB as Storage Box

    D->>E: Container start
    E->>AL: alembic upgrade head (Advisory-Lock)
    E->>CLI: seed-content (fehlende Standardtexte)
    E->>G: exec granian
    Note over G: Settings-Validierung: Start verweigert bei Dev-Secret,<br/>DEBUG, Platzhaltern, Mail ohne TLS
    loop täglich 02:30
        BK->>BK: pg_dump + /media
        BK->>SB: restic backup (verschlüsselt) + forget 7/4/6
    end
    loop sonntags
        BK->>SB: restic check --read-data-subset=5%
    end
```
