"""Command line interface for operational tasks.

Usage (inside the container or locally with `uv run`)::

    python -m atem.cli create-admin --email vorname.name@example.ch
    python -m atem.cli reset-2fa --email vorname.name@example.ch
    python -m atem.cli unlock --email vorname.name@example.ch
    python -m atem.cli seed-content
    python -m atem.cli purge-messages
"""

import argparse
import asyncio
import getpass
import os
import sys

from atem.domain.exceptions import EntityNotFoundException, ValidationException
from atem.infrastructure.config.settings import get_settings
from atem.infrastructure.database.session import create_engine, create_session_factory
from atem.presentation.bootstrap import build_auth_service, purge_expired_data, seed_content

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


async def _purge() -> None:
    settings = get_settings()
    engine = create_engine()
    try:
        deleted = await purge_expired_data(create_session_factory(engine), settings)
        days = settings.MESSAGE_RETENTION_DAYS
        print(f"{deleted} Kontaktnachrichten älter als {days} Tage gelöscht.")
    finally:
        await engine.dispose()


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

    sub.add_parser("seed-content", help="Fehlende Standard-Inhalte ergänzen (idempotent)")
    sub.add_parser("purge-messages", help="Aufbewahrungsfrist durchsetzen (alte Daten löschen)")
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point; returns the process exit code."""
    args = build_parser().parse_args(argv)
    get_settings()  # fail fast on insecure configuration
    try:
        if args.command == "create-admin":
            asyncio.run(_create_admin(args.email))
        elif args.command == "reset-2fa":
            asyncio.run(_reset_2fa(args.email))
        elif args.command == "unlock":
            asyncio.run(_unlock(args.email))
        elif args.command == "purge-messages":
            asyncio.run(_purge())
        elif args.command == "seed-content":
            asyncio.run(_seed_content())
    except (ValidationException, EntityNotFoundException) as exc:
        print(f"Fehler: {exc.message}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
