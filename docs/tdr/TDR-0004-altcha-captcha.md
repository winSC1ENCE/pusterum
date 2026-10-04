# TDR-0004: ALTCHA (self-hosted Proof-of-Work) als CAPTCHA

* **Status:** accepted
* **Date:** 2026-10-04
* **Author:** Nicolas Mischler
* **Scope:** Kontaktformular (`/contact`, `/altcha/challenge`), `infrastructure/captcha/`

## Problem / Scope

Das Kontaktformular war nur durch ein Honeypot-Feld geschützt und hätte als Spam-Relay missbraucht
werden können. Benötigt wird ein Bot-Schutz ohne Datenübermittlung an Dritte, ohne Cookies und kompatibel
mit einer strikten Content-Security-Policy.

## Technical Decision

* **ALTCHA v1** (Python-Bibliothek `altcha`, Widget `altcha@1.5.1` im *external*-Build, lokal gehostet unter
  `static/vendor/altcha/` mit SHA-256 im README).
* Der Server signiert Challenges per HMAC (Schlüssel per HKDF aus `SECRET_KEY`), Ablauf 20 min,
  Schwierigkeit `ALTCHA_MAX_NUMBER` (Default 100 000 ≈ 0,1–0,5 s auf einem Smartphone).
* Verifikation serverseitig (`AltchaCaptcha.verify`); jede gelöste Challenge wird in
  `used_captcha_challenges` gesperrt (Replay-Schutz) und nach Ablauf gelöscht.
* Ergänzend: signiertes Zeit-Token, Honeypot, IP-Limits (3/h, 10/Tag), Caddy-Rate-Limit.

## Rationale & Trade-offs

* **Why this approach:** keine Drittanbieter (DSG/DSGVO), kein Konto, keine Kosten, CSP-tauglich (separates
  CSS und Web-Worker), für Menschen fast unsichtbar.
* **Alternatives evaluated:** Friendly Captcha (EU, aber Konto/kostenpflichtig kommerziell), Cloudflare
  Turnstile (Datenübermittlung USA), hCaptcha (Bild-Puzzles, schlechte UX).
* **Impact on existing code:** neue Tabelle (Migration 0006), Widget nur auf der Startseite geladen,
  E2E-Test löst die Challenge im echten Browser.
