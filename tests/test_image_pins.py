"""Container image pins: Dependabot can update them only where it can read them (TDR-0008)."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIGEST_PIN = re.compile(r"^[\w./-]+:[\w.-]+@sha256:[0-9a-f]{64}$")
POSTGRES_PIN = re.compile(r"postgres:[\w.-]+@sha256:[0-9a-f]{64}")
DOCKERFILES = ("Dockerfile", "docker/caddy/Dockerfile", "docker/backup/Dockerfile")


def test_dockerfiles_pin_base_images_directly_in_from() -> None:
    """``FROM ${VAR}`` is invisible to Dependabot – every base image is a pinned literal."""
    for name in DOCKERFILES:
        for line in (ROOT / name).read_text().splitlines():
            if line.startswith("FROM "):
                image = line.split()[1]
                assert DIGEST_PIN.match(image), f"{name}: {line}"


def test_postgres_pins_match_the_backup_image() -> None:
    """Production DB, backup pg_dump and CI test databases run the same PostgreSQL build.

    Dependabot updates docker/backup/Dockerfile; on a mismatch run scripts/sync-image-pins.sh.
    """
    source = POSTGRES_PIN.findall((ROOT / "docker/backup/Dockerfile").read_text())
    assert len(source) == 1
    for name, expected_count in (("docker-compose.prod.yml", 1), (".github/workflows/ci.yml", 4)):
        pins = POSTGRES_PIN.findall((ROOT / name).read_text())
        assert len(pins) == expected_count, name
        assert set(pins) == set(source), (
            f"{name} uses {sorted(set(pins))}, backup image is {source[0]} – "
            "run scripts/sync-image-pins.sh"
        )


def test_dependabot_config_has_no_yaml_aliases() -> None:
    """Valid YAML and schema, yet Dependabot rejects the file: «YAML aliases are not supported»."""
    anchor_or_alias = re.compile(r"(:|^\s*-)\s*[&*][\w-]+")
    lines = (ROOT / ".github/dependabot.yml").read_text().splitlines()
    offending = [line for line in lines if anchor_or_alias.search(line.split("#")[0])]
    assert not offending, f"Dependabot cannot parse YAML anchors/aliases: {offending}"
