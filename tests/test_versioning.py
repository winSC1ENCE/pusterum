"""Versioning (TDR-0009): pyproject.toml, uv.lock and CHANGELOG.md agree on one SemVer version."""

import re
import subprocess
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
# Separator: ASCII hyphen (since 1.2.0, METAS dash rule) or the en dash of older releases.
RELEASE_HEADING = re.compile(
    r"^## \[(?P<version>[^\]]+)\] [-\u2013] (?P<date>\d{4}-\d{2}-\d{2})$", re.M
)


def project_version() -> str:
    with (ROOT / "pyproject.toml").open("rb") as file:
        version: str = tomllib.load(file)["project"]["version"]
    return version


def test_project_version_is_semver() -> None:
    assert SEMVER.match(project_version()), project_version()


def test_lockfile_has_the_project_version() -> None:
    lock = tomllib.loads((ROOT / "uv.lock").read_text())
    atem = next(package for package in lock["package"] if package["name"] == "atem")
    assert atem["version"] == project_version(), "run `uv lock` after changing the version"


def test_newest_changelog_release_is_the_project_version() -> None:
    changelog = (ROOT / "CHANGELOG.md").read_text()
    assert "## [Unreleased]" in changelog
    releases = [match["version"] for match in RELEASE_HEADING.finditer(changelog)]
    assert releases, "CHANGELOG.md has no «## [x.y.z] - YYYY-MM-DD» section"
    assert releases[0] == project_version(), (
        "CHANGELOG.md and pyproject.toml disagree – a release moves «Unreleased» to the new "
        "version and bumps [project].version (TDR-0009)"
    )
    assert all(SEMVER.match(version) for version in releases), releases


def test_release_notes_script_prints_only_the_section_of_the_version() -> None:
    script = ROOT / "scripts/release-notes.sh"
    version = subprocess.run(
        [script, "--version"], check=True, capture_output=True, text=True
    ).stdout.strip()
    notes = subprocess.run([script], check=True, capture_output=True, text=True).stdout

    assert version == project_version()
    assert notes.strip()
    assert "## [" not in notes  # neither its own heading nor the next release

    missing = subprocess.run([script, "0.0.0"], capture_output=True, text=True, check=False)
    assert missing.returncode == 1
