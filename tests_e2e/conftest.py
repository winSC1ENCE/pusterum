"""E2E fixtures: migrate a dedicated database and run the real app with granian.

Requires PostgreSQL. Set E2E_DATABASE_URL (default: local docker compose database
``atem_e2e`` – created automatically if the ``atem_postgres`` container is running).
"""

import os
import socket
import subprocess
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from playwright.sync_api import Page

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_URL = "postgresql+asyncpg://atem_user:atem_secure_password@localhost:5432/atem_e2e"
ADMIN_EMAIL = "entwicklung@pusterum.be"  # dev admin seeded by the app (login = e-mail)
ADMIN_PASSWORD = "admin-secure-init-pass-change-me"

CSP_PROBE = """
window.__cspViolations = [];
document.addEventListener('securitypolicyviolation', (e) => {
  window.__cspViolations.push(
    `${e.violatedDirective}: ${e.blockedURI} ${e.sourceFile}:${e.lineNumber}`);
});
"""


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _ensure_local_database(url: str) -> None:
    if url != DEFAULT_DB_URL:
        return
    for statement in ("DROP DATABASE IF EXISTS atem_e2e", "CREATE DATABASE atem_e2e"):
        subprocess.run(
            [
                "docker",
                "exec",
                "atem_postgres",
                "psql",
                "-U",
                "atem_user",
                "-d",
                "atem_db",
                "-c",
                statement,
            ],
            check=False,
            capture_output=True,
        )


@pytest.fixture(scope="session")
def server_url() -> Iterator[str]:
    db_url = os.environ.get("E2E_DATABASE_URL", DEFAULT_DB_URL)
    _ensure_local_database(db_url)
    port = _free_port()
    env = {
        **os.environ,
        "ENVIRONMENT": "development",
        "DEBUG": "false",
        "SECRET_KEY": "e2e-secret-key-at-least-32-characters-long",
        "DATABASE_URL": db_url,
        "ALLOWED_HOSTS": '["127.0.0.1", "localhost"]',
        "ADMIN_EMAIL": ADMIN_EMAIL,
        "ADMIN_INITIAL_PASSWORD": ADMIN_PASSWORD,
        "CONTACT_FORM_MIN_SECONDS": "0",
        "ALTCHA_MAX_NUMBER": "5000",
        "MAIL_ENABLED": "false",
    }
    subprocess.run(["uv", "run", "alembic", "upgrade", "head"], cwd=ROOT, env=env, check=True)
    proc = subprocess.Popen(
        [
            "uv",
            "run",
            "granian",
            "--interface",
            "asgi",
            "--factory",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "atem.presentation.app:create_app",
        ],
        cwd=ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    url = f"http://127.0.0.1:{port}"
    for _ in range(80):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                break
        except OSError:
            time.sleep(0.25)
    time.sleep(0.5)
    yield url
    proc.terminate()
    proc.wait(timeout=10)


@pytest.fixture
def page(page: Page) -> Page:
    """Playwright page that records CSP violations and console errors."""
    page.add_init_script(CSP_PROBE)
    errors: list[str] = []
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    page.console_errors = errors  # type: ignore[attr-defined]
    return page


def assert_clean(page: Page) -> None:
    """No CSP violations and no JavaScript errors on the current page."""
    violations: list[Any] = page.evaluate("window.__cspViolations || []")
    assert violations == [], f"CSP violations: {violations}"
    errors = [e for e in page.console_errors if "favicon" not in e]  # type: ignore[attr-defined]
    assert errors == [], f"Console errors: {errors}"
