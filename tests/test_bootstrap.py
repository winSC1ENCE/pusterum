"""Tests for secure configuration, bootstrap helpers and the operations CLI."""

import pytest
from pydantic import ValidationError

from atem.application.services.auth_service import AuthService
from atem.cli import build_parser
from atem.domain.exceptions import ValidationException
from atem.infrastructure.config.settings import DEV_SECRET_KEY, Settings

SECURE_PROD = {
    "ENVIRONMENT": "production",
    "SECRET_KEY": "a" * 64,
    "ALLOWED_HOSTS": ["www.pusterum.be"],
    "DATABASE_URL": "postgresql+asyncpg://atem_user:Str0ng-Secret@db:5432/atem_db",
}


def _settings(**overrides: object) -> Settings:
    return Settings(_env_file=None, **{**SECURE_PROD, **overrides})  # type: ignore[arg-type]


def test_production_accepts_secure_configuration() -> None:
    settings = _settings()
    assert settings.is_production_like
    assert len(settings.session_secret) == 32


def test_default_environment_is_production() -> None:
    assert Settings.model_fields["ENVIRONMENT"].default == "production"


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({"SECRET_KEY": DEV_SECRET_KEY}, "SECRET_KEY"),
        ({"DEBUG": True}, "DEBUG"),
        ({"ALLOWED_HOSTS": ["localhost", "127.0.0.1"]}, "ALLOWED_HOSTS"),
        (
            {"DATABASE_URL": "postgresql+asyncpg://u:atem_secure_password@db/x"},
            "Standard-Datenbankpasswort",
        ),
        ({"MAIL_ENABLED": True}, "SMTP_USE_TLS"),
        ({"ENVIRONMENT": "staging", "DEBUG": True}, "DEBUG"),
        ({"DATABASE_URL": "postgresql+asyncpg://u:CHANGE_ME@db/x"}, "CHANGE_ME"),
    ],
)
def test_production_rejects_insecure_configuration(
    overrides: dict[str, object], expected: str
) -> None:
    with pytest.raises(ValidationError, match=expected):
        _settings(**overrides)


def test_development_allows_dev_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SECRET_KEY", raising=False)
    settings = Settings(_env_file=None, ENVIRONMENT="development", DEBUG=True)  # type: ignore[call-arg]
    assert settings.SECRET_KEY == DEV_SECRET_KEY
    assert not settings.is_production_like


def test_derived_keys_are_purpose_bound() -> None:
    settings = _settings()
    assert settings.derive_key(b"a") != settings.derive_key(b"b")


async def test_create_admin_enforces_policy(auth_service: AuthService) -> None:
    with pytest.raises(ValidationException, match="mindestens 12"):
        await auth_service.create_admin("stephanie", "kontakt@pusterum.be", "kurz")

    user = await auth_service.create_admin(
        "stephanie", "kontakt@pusterum.be", "ein-langes-passwort"
    )
    assert user.username == "stephanie"

    with pytest.raises(ValidationException, match="existiert bereits"):
        await auth_service.create_admin("stephanie", "kontakt@pusterum.be", "ein-langes-passwort")


def test_cli_parser_commands() -> None:
    parser = build_parser()
    args = parser.parse_args(["create-admin", "--username", "s", "--email", "s@pusterum.be"])
    assert args.command == "create-admin"
    assert parser.parse_args(["seed-content"]).command == "seed-content"
    assert parser.parse_args(["reset-2fa", "--username", "s"]).command == "reset-2fa"
