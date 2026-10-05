#!/usr/bin/env bash
# Usage: scripts/run_xvada.sh NAME ORACLE TRAIN TEST [search options]
set -euo pipefail
exec bash "$(dirname "$0")/run_inference.sh" xvada "$@"
