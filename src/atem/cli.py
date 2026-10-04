"""Command line interface for operational tasks.

Usage (inside the container or locally with `uv run`)::

    python -m atem.cli create-admin --username stephanie --email kontakt@pusterum.be
    python -m atem.cli seed-content
"""

import argparse
import asyncio
import getpass
import os
import sys

from atem.domain.exceptions import ValidationException
from atem.infrastructure.config.settings import get_settings
from atem.infrastructure.database.session import create_engine, create_session_factory
from atem.presentation.bootstrap import build_auth_service, seed_content

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


async def _create_admin(username: str, email: str) -> None:
    password = _read_password()
    engine = create_engine()
    try:
        async with create_session_factory(engine)() as session:
            user = await build_auth_service(session).create_admin(username, email, password)
            await session.commit()
        print(f"Admin «{user.username}» angelegt.")
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
    admin.add_argument("--username", required=True)
    admin.add_argument("--email", required=True)

    sub.add_parser("seed-content", help="Fehlende Standard-Inhalte ergänzen (idempotent)")
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point; returns the process exit code."""
    args = build_parser().parse_args(argv)
    get_settings()  # fail fast on insecure configuration
    try:
        if args.command == "create-admin":
            asyncio.run(_create_admin(args.username, args.email))
        elif args.command == "seed-content":
            asyncio.run(_seed_content())
    except ValidationException as exc:
        print(f"Fehler: {exc.message}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
