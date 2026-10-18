"""Guards for privacy-relevant operations config (ADR-0006, tech-debt #7)."""

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


def test_proxy_access_log_masks_client_ips() -> None:
    log_block = re.search(r"\tlog \{.*?\n\t\}", (ROOT / "Caddyfile").read_text(), re.S)
    assert log_block, "Caddyfile has no log block"
    for field in ("request>remote_ip", "request>client_ip"):
        assert re.search(rf"{re.escape(field)} ip_mask \{{", log_block.group(0)), field


def test_server_keeps_journald_logs_30_days() -> None:
    config = yaml.safe_load((ROOT / "ops/server/cloud-init.yaml").read_text())
    files = {f["path"]: f["content"] for f in config["write_files"]}
    assert "MaxRetentionSec=30day" in files["/etc/systemd/journald.conf.d/50-retention.conf"]
    assert "systemctl restart systemd-journald" in config["runcmd"]
