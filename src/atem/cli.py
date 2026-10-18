"""Command line interface for operational tasks.

Usage (inside the container or locally with `uv run`)::

    python -m atem.cli create-admin --email vorname.name@example.ch
    python -m atem.cli reset-2fa --email vorname.name@example.ch
    python -m atem.cli unlock --email vorname.name@example.ch
    python -m atem.cli reset-password --email vorname.name@example.ch [--require-change]
    python -m atem.cli deactivate-admin --email vorname.name@example.ch
    python -m atem.cli activate-admin --email vorname.name@example.ch
    python -m atem.cli delete-admin --email vorname.name@example.ch [--yes]
    python -m atem.cli seed-content
    python -m atem.cli purge-messages
    python -m atem.cli export-person --email person@example.ch > auskunft.json
    python -m atem.cli forget-person --email person@example.ch [--yes]
    python -m atem.cli reapply-deletions
"""

import argparse
import asyncio
import getpass
import json
import os
import sys
from collections.abc import Callable, Coroutine
from typing import Any, TextIO, cast

from atem.domain.exceptions import EntityNotFoundException, ValidationException
from atem.infrastructure.config.settings import get_settings
from atem.infrastructure.database.session import create_engine, create_session_factory
from atem.infrastructure.email.mock_email_service import MockEmailService
from atem.infrastructure.logging.logger import setup_logging
from atem.presentation.bootstrap import (
    build_auth_service,
    build_contact_repository,
    build_contact_service,
    purge_expired_data,
    seed_content,
)

PASSWORD_ENV_VAR = "ATEM_ADMIN_PASSWORD"  # nosec B105 - env var name, not a secret


def _read_password() -> str:
    """Read the new admin password from the environment or interactively."""
    from_env = os.environ.get(PASSWORD_ENV_VAR)
    if from_env:
        return from_env
    first = getpass.getpass("Neues Admin-Passwort: ")
    second = getpass.getpass("Passwort wiederholen: ")
    if first != second:
        raise ValidationException("Die Passwörter stimmen nicht überein.")
    return first


async def _create_admin(email: str) -> None:
    password = _read_password()
    engine = create_engine()
    try:
        async with create_session_factory(engine)() as session:
            user = await build_auth_service(session).create_admin(email, password)
            await session.commit()
        print(f"Admin «{user.email}» angelegt.")
    finally:
        await engine.dispose()


async def _reset_2fa(email: str) -> None:
    engine = create_engine()
    try:
        async with create_session_factory(engine)() as session:
            await build_auth_service(session).reset_totp(email)
            await session.commit()
        print(f"Zwei-Faktor-Anmeldung für «{email}» zurückgesetzt – bitte neu einrichten.")
    finally:
        await engine.dispose()


async def _unlock(email: str) -> None:
    engine = create_engine()
    try:
        async with create_session_factory(engine)() as session:
            await build_auth_service(session).unlock(email)
            await session.commit()
        print(f"Sperre für «{email}» aufgehoben.")
    finally:
        await engine.dispose()


async def _reset_password(email: str, *, require_change: bool) -> None:
    password = _read_password()
    engine = create_engine()
    try:
        async with create_session_factory(engine)() as session:
            await build_auth_service(session).reset_password(
                email, password, require_change=require_change
            )
            await session.commit()
        hint = " Beim nächsten Login muss es geändert werden." if require_change else ""
        print(f"Passwort für «{email}» zurückgesetzt, alle Sitzungen beendet.{hint}")
    finally:
        await engine.dispose()


async def _set_active(email: str, *, active: bool) -> None:
    engine = create_engine()
    try:
        async with create_session_factory(engine)() as session:
            await build_auth_service(session).set_active(email, active=active)
            await session.commit()
        state = "aktiviert" if active else "deaktiviert (alle Sitzungen beendet)"
        print(f"Konto «{email}» {state}.")
    finally:
        await engine.dispose()


async def _delete_admin(email: str) -> None:
    engine = create_engine()
    try:
        async with create_session_factory(engine)() as session:
            await build_auth_service(session).delete_admin(email)
            await session.commit()
        print(f"Konto «{email}» gelöscht.")
    finally:
        await engine.dispose()


def _confirm_delete(email: str) -> bool:
    answer = input(f"Konto «{email}» endgültig löschen? Tippen Sie «ja»: ")
    return answer.strip().lower() == "ja"


async def _purge() -> None:
    settings = get_settings()
    engine = create_engine()
    try:
        deleted = await purge_expired_data(create_session_factory(engine), settings)
        print(f"{deleted} Kontaktnachrichten nach Ablauf der Frist gelöscht.")
    finally:
        await engine.dispose()


async def _export_person(email: str) -> None:
    settings = get_settings()
    engine = create_engine()
    try:
        async with create_session_factory(engine)() as session:
            service = build_contact_service(
                build_contact_repository(session, settings), MockEmailService(), settings
            )
            data = await service.export_person(email)
        print(json.dumps(data, ensure_ascii=False, indent=2))
        print(f"{len(data)} Anfragen exportiert.", file=sys.stderr)
    finally:
        await engine.dispose()


async def _forget_person(email: str) -> None:
    settings = get_settings()
    engine = create_engine()
    try:
        async with create_session_factory(engine)() as session:
            service = build_contact_service(
                build_contact_repository(session, settings), MockEmailService(), settings
            )
            deleted = await service.forget_person(email)
            await session.commit()
        print(f"{deleted} Anfragen gelöscht und im Löschprotokoll vermerkt.")
    finally:
        await engine.dispose()


async def _reapply_deletions() -> None:
    settings = get_settings()
    engine = create_engine()
    try:
        async with create_session_factory(engine)() as session:
            service = build_contact_service(
                build_contact_repository(session, settings), MockEmailService(), settings
            )
            deleted = await service.reapply_deletions()
            await session.commit()
        print(f"{deleted} Anfragen aus dem Löschprotokoll erneut gelöscht.")
    finally:
        await engine.dispose()


def _confirm_forget(email: str) -> bool:
    answer = input(f"Alle Anfragen von «{email}» endgültig löschen? Tippen Sie «ja»: ")
    return answer.strip().lower() == "ja"


async def _seed_content() -> None:
    engine = create_engine()
    try:
        inserted = await seed_content(create_session_factory(engine))
        print(f"{inserted} Standard-Inhalte ergänzt.")
    finally:
        await engine.dispose()


def build_parser() -> argparse.ArgumentParser:
    """Create the argument parser with all sub-commands."""
    parser = argparse.ArgumentParser(prog="atem.cli", description="PUSTERUM Betriebsbefehle")
    sub = parser.add_subparsers(dest="command", required=True)

    admin = sub.add_parser("create-admin", help="Administrator-Konto anlegen")
    admin.add_argument("--email", required=True, help="persönliche E-Mail-Adresse = Login")

    reset = sub.add_parser("reset-2fa", help="2FA eines Kontos zurücksetzen (Gerät verloren)")
    reset.add_argument("--email", required=True)

    unlock = sub.add_parser("unlock", help="Kontosperre nach Fehlversuchen sofort aufheben")
    unlock.add_argument("--email", required=True)

    reset_pw = sub.add_parser(
        "reset-password", help="Passwort zurücksetzen (vergessen); 2FA bleibt bestehen"
    )
    reset_pw.add_argument("--email", required=True)
    reset_pw.add_argument(
        "--require-change",
        action="store_true",
        help="vorläufiges Passwort: beim nächsten Login muss ein neues gewählt werden",
    )

    deactivate = sub.add_parser("deactivate-admin", help="Konto sperren (Person scheidet aus)")
    deactivate.add_argument("--email", required=True)
    activate = sub.add_parser("activate-admin", help="Deaktiviertes Konto wieder freigeben")
    activate.add_argument("--email", required=True)

    delete = sub.add_parser("delete-admin", help="Konto endgültig löschen")
    delete.add_argument("--email", required=True)
    delete.add_argument("--yes", action="store_true", help="ohne Rückfrage löschen")

    sub.add_parser("seed-content", help="Fehlende Standard-Inhalte ergänzen (idempotent)")
    sub.add_parser("purge-messages", help="Aufbewahrungsfrist durchsetzen (alte Daten löschen)")
    export = sub.add_parser(
        "export-person", help="Alle Anfragen einer Person als JSON (Auskunftsbegehren)"
    )
    export.add_argument("--email", required=True)
    forget = sub.add_parser(
        "forget-person", help="Alle Anfragen einer Person löschen (Löschbegehren, protokolliert)"
    )
    forget.add_argument("--email", required=True)
    forget.add_argument("--yes", action="store_true", help="ohne Rückfrage löschen")
    sub.add_parser(
        "reapply-deletions", help="Protokollierte Löschungen wiederholen (nach jedem Restore)"
    )
    return parser


class _Stderr:
    """Logs go to stderr, stdout carries data (export-person > auskunft.json).

    ``sys.stderr`` is looked up on every write, so a replaced stream (tests) is respected.
    """

    def write(self, text: str) -> int:
        return sys.stderr.write(text)

    def flush(self) -> None:
        sys.stderr.flush()


def _coroutine(args: argparse.Namespace) -> Coroutine[Any, Any, None]:
    """The async task behind a sub-command."""
    commands: dict[str, Callable[[], Coroutine[Any, Any, None]]] = {
        "create-admin": lambda: _create_admin(args.email),
        "reset-2fa": lambda: _reset_2fa(args.email),
        "unlock": lambda: _unlock(args.email),
        "reset-password": lambda: _reset_password(args.email, require_change=args.require_change),
        "deactivate-admin": lambda: _set_active(args.email, active=False),
        "activate-admin": lambda: _set_active(args.email, active=True),
        "delete-admin": lambda: _delete_admin(args.email),
        "purge-messages": _purge,
        "export-person": lambda: _export_person(args.email),
        "forget-person": lambda: _forget_person(args.email),
        "reapply-deletions": _reapply_deletions,
        "seed-content": _seed_content,
    }
    return commands[args.command]()


# Destructive commands ask first unless --yes is given.
CONFIRMATIONS: dict[str, Callable[[str], bool]] = {
    "delete-admin": _confirm_delete,
    "forget-person": _confirm_forget,
}


def main(argv: list[str] | None = None) -> int:
    """CLI entry point; returns the process exit code."""
    args = build_parser().parse_args(argv)
    settings = get_settings()  # fail fast on insecure configuration
    setup_logging(is_dev=settings.is_dev, stream=cast("TextIO", _Stderr()))
    confirm = CONFIRMATIONS.get(args.command)
    if confirm and not args.yes and not confirm(args.email):
        print("Abgebrochen, nichts gelöscht.")
        return 1
    try:
        asyncio.run(_coroutine(args))
    except (ValidationException, EntityNotFoundException) as exc:
        print(f"Fehler: {exc.message}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
