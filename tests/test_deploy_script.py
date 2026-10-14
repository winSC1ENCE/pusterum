"""ops/deploy/pusterum-deploy.sh: deploy, rollback and healthcheck pings (ADR-0005).

Runs the real script against a temporary git remote; ``docker`` and ``curl`` are fakes on PATH.
"""

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "ops/deploy/pusterum-deploy.sh"
HEALTH_URL = "https://site.test/health/ready"
PING_URL = "https://ping.test/abc"

pytestmark = pytest.mark.skipif(
    not all(shutil.which(tool) for tool in ("bash", "git", "flock")),
    reason="needs bash, git and flock",
)

FAKE_CURL = """#!/usr/bin/env bash
# Health URL: ok while $FAKE_DIR/healthy exists. Any other URL: a ping, logged with its body.
url="${@: -1}" data=""
while [ $# -gt 0 ]; do [ "$1" = --data-raw ] && data="$2"; shift; done
if [ "$url" = "$HEALTH_URL" ]; then [ -e "$FAKE_DIR/healthy" ]; exit; fi
printf '%s %s\\n' "$url" "$data" >>"$FAKE_DIR/pings"
"""
FAKE_DOCKER = """#!/usr/bin/env bash
echo "$*" >>"$FAKE_DIR/docker"
"""


@dataclass
class Deploy:
    """A server checkout of ``production`` plus fakes; ``run`` executes the deploy script."""

    tmp: Path
    remote: Path
    work: Path
    checkout: Path
    env: dict[str, str]

    def git(self, cwd: Path, *args: str) -> str:
        return subprocess.run(
            ["git", *args], cwd=cwd, env=self.env, check=True, capture_output=True, text=True
        ).stdout.strip()

    def push_commit(self, name: str) -> str:
        """Commit in the developer clone and move ``production`` (what CI ``promote`` does)."""
        (self.work / name).write_text(name)
        self.git(self.work, "add", name)
        self.git(self.work, "commit", "-qm", name)
        self.git(self.work, "push", "-q", "origin", "HEAD:production")
        return self.git(self.work, "rev-parse", "HEAD")

    def healthy(self, state: bool) -> None:
        flag = self.tmp / "healthy"
        if state:
            flag.touch()
        else:
            flag.unlink(missing_ok=True)

    def run(self, *args: str, **env: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", str(SCRIPT), *args],
            env={**self.env, **env},
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
        )

    def pings(self) -> list[str]:
        path = self.tmp / "pings"
        return path.read_text().splitlines() if path.exists() else []

    @property
    def head(self) -> str:
        return self.git(self.checkout, "rev-parse", "HEAD")


@pytest.fixture
def deploy(tmp_path: Path) -> Deploy:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name, body in (("curl", FAKE_CURL), ("docker", FAKE_DOCKER)):
        (bin_dir / name).write_text(body)
        (bin_dir / name).chmod(0o755)
    env = {
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
        "HOME": str(tmp_path),
        "TMPDIR": str(tmp_path),
        "FAKE_DIR": str(tmp_path),
        "HEALTH_URL": HEALTH_URL,
        "HEALTH_RETRIES": "1",
        "HEALTH_DELAY": "0",
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@example.org",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@example.org",
        "GIT_CONFIG_GLOBAL": os.devnull,
    }
    remote, work, checkout = tmp_path / "remote.git", tmp_path / "work", tmp_path / "srv"
    setup = Deploy(tmp_path, remote, work, checkout, {**env, "REPO_DIR": str(checkout)})
    setup.git(tmp_path, "init", "-q", "--bare", str(remote))
    setup.git(tmp_path, "clone", "-q", str(remote), str(work))
    setup.push_commit("first")
    setup.git(tmp_path, "clone", "-q", "-b", "production", str(remote), str(checkout))
    (checkout / "deploy.env").write_text(f"# test\nDEPLOY_PING_URL={PING_URL}\n")
    (checkout / ".git/info/exclude").write_text("deploy.env\n")
    setup.healthy(True)
    return setup


def test_idle_run_with_healthy_site_pings_success(deploy: Deploy) -> None:
    result = deploy.run()

    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout == ""  # quiet in the journal
    assert deploy.pings() == [f"{PING_URL} ok"]


def test_idle_run_with_site_down_pings_fail(deploy: Deploy) -> None:
    deploy.healthy(False)

    result = deploy.run()

    assert result.returncode == 1
    assert "FEHLER: Website antwortet nicht" in result.stdout
    assert deploy.pings() == [f"{PING_URL}/fail FEHLER: Website antwortet nicht ({HEALTH_URL})."]


def test_new_commit_deploys_and_pings_success(deploy: Deploy) -> None:
    target = deploy.push_commit("second")

    result = deploy.run()

    assert result.returncode == 0, result.stdout + result.stderr
    assert deploy.head == target
    assert deploy.pings() == [f"{PING_URL} Deployment {target[:7]} erfolgreich."]


def test_unhealthy_commit_rolls_back_and_keeps_alarm_until_next_commit(deploy: Deploy) -> None:
    previous = deploy.head
    bad = deploy.push_commit("broken")
    deploy.healthy(False)

    result = deploy.run()

    assert result.returncode == 1
    assert deploy.head == previous
    assert (deploy.tmp / ".local/state/pusterum/failed").read_text().strip() == bad
    assert deploy.pings()[-1].startswith(f"{PING_URL}/fail KRITISCH")

    # Old version healthy again: no retry of the bad commit, but the check stays red
    deploy.healthy(True)
    result = deploy.run()

    assert result.returncode == 0
    assert deploy.head == previous
    assert deploy.pings()[-1] == (
        f"{PING_URL}/fail Deployment {bad[:7]} fehlgeschlagen, {previous[:7]} läuft – "
        "wartet auf einen neuen Commit."
    )

    fixed = deploy.push_commit("fixed")
    assert deploy.run().returncode == 0
    assert deploy.head == fixed
    assert deploy.pings()[-1] == f"{PING_URL} Deployment {fixed[:7]} erfolgreich."


def test_successful_rollback_reports_the_failed_deployment(deploy: Deploy) -> None:
    previous = deploy.head
    bad = deploy.push_commit("broken")
    # Healthy again as soon as the rollback rebuilds: fake docker restores the flag
    (deploy.tmp / "bin/docker").write_text(
        '#!/usr/bin/env bash\ngrep -q "^broken$" broken 2>/dev/null && rm -f "$FAKE_DIR/healthy"'
        ' || touch "$FAKE_DIR/healthy"\n'
    )

    result = deploy.run()

    assert result.returncode == 1
    assert "FEHLER: Health-Check fehlgeschlagen" in result.stdout
    assert deploy.head == previous
    assert deploy.pings() == [
        f"{PING_URL}/fail Deployment {bad[:7]} fehlgeschlagen, Rollback auf {previous[:7]} "
        f"erfolgreich. {bad[:7]} wird erst mit einem neuen Commit erneut versucht."
    ]


def test_unexpected_error_pings_fail(deploy: Deploy) -> None:
    deploy.git(deploy.checkout, "remote", "set-url", "origin", str(deploy.tmp / "missing.git"))

    result = deploy.run()

    assert result.returncode != 0
    assert deploy.pings()[0].startswith(f"{PING_URL}/fail Unerwarteter Fehler")


def test_local_changes_abort_with_fail_ping(deploy: Deploy) -> None:
    deploy.push_commit("second")
    (deploy.checkout / "first").write_text("edited on the server")

    result = deploy.run()

    assert result.returncode == 1
    assert deploy.pings()[0].startswith(f"{PING_URL}/fail ABBRUCH: lokale Änderungen")


def test_without_ping_url_nothing_is_sent(deploy: Deploy) -> None:
    (deploy.checkout / "deploy.env").unlink()
    deploy.healthy(False)

    assert deploy.run().returncode == 1
    assert deploy.pings() == []


def test_environment_variable_overrides_deploy_env(deploy: Deploy) -> None:
    deploy.run(DEPLOY_PING_URL="https://other.test/x")

    assert deploy.pings() == ["https://other.test/x ok"]


def test_dry_run_sends_no_ping(deploy: Deploy) -> None:
    deploy.push_commit("second")

    result = deploy.run("--dry-run")

    assert result.returncode == 0
    assert "Trockenlauf" in result.stdout
    assert deploy.pings() == []
