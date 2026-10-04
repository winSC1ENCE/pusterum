# Quickstart: Lokale Entwicklungsumgebung (DEV START)

Kurzanleitung zum schnellen und sauberen Starten der lokalen Entwicklungsumgebung für **PUSTERUM – Praxis für Atem- und Körpertherapie**.

---

## 1. Voraussetzungen

Folgende Tools müssen auf dem System installiert sein:

* **Python 3.12+**
* **Astral `uv`** (Paketmanager):
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```
* **Docker & Docker Compose** (für die lokale PostgreSQL-Datenbank)

---

## 2. DEV-Umgebung in 4 Schritten starten

### Schritt 1: Abhängigkeiten installieren & `.env` anlegen
```bash
uv sync
uv run pre-commit install
cp config/env.development.example .env   # ENVIRONMENT=development ist Pflicht (Default = production)
```

### Schritt 2: PostgreSQL Datenbank starten
```bash
docker compose up -d db
```

### Schritt 3: Datenbank-Migrationen anwenden
```bash
uv run alembic upgrade head
```

### Schritt 4: Entwicklungs-Server starten
```bash
uv run granian --interface asgi --host 127.0.0.1 --port 8000 --reload --factory atem.presentation.app:create_app
```

> **Tipp (Offline / SBB Free WLAN):**
> Befinden Sie sich in einem Zug-WLAN oder offline, hängen Sie `--no-sync` an, um externe PyPI-Checks zu überspringen:
> ```bash
> uv run --no-sync granian --interface asgi --host 127.0.0.1 --port 8000 --reload --factory atem.presentation.app:create_app
> ```

> **Hinweis bei Port-Konflikten (Port 8000 belegt):**
> Wurde zuvor der App-Container gestartet, stoppen Sie ihn einfach (während `db` weiterläuft):
> ```bash
> docker compose stop app   # oder: docker stop atem_app
> docker compose up -d db   # DB läuft weiterhin
> ```

---

## 3. URLs & Standard-Zugangsdaten

| Bereich | URL | Zugangsdaten |
| :--- | :--- | :--- |
| **Website (Live)** | [http://127.0.0.1:8000](http://127.0.0.1:8000) | Öffentlich zugänglich |
| **Admin-Login** | [http://127.0.0.1:8000/admin/login](http://127.0.0.1:8000/admin/login) | **User:** `admin`<br/>**Passwort:** `admin-secure-init-pass-change-me` |
| **Corporate Design Studio** | [http://127.0.0.1:8000/admin/design](http://127.0.0.1:8000/admin/design) | Nach Login im Admin-Panel |
| **Health Check** | [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health) | Status & System-Check |

---

## 4. Tests & Code-Qualität

Vor Commits können alle automatisierten Prüfungen lokal ausgeführt werden:

```bash
# Tests & Coverage ausführen (Mindestens 85%)
uv run pytest

# Alle Linters, Type-Checks & Sicherheits-Gates prüfen
uv run pre-commit run --all-files
```
