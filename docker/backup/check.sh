#!/bin/sh
# Weekly integrity check: verifies repository structure and reads 5 % of the data.
set -eu
echo "[backup] $(date -Iseconds) restic check ..."
restic check --read-data-subset=5%
