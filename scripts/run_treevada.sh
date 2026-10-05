#!/usr/bin/env bash
# Usage: scripts/run_treevada.sh NAME ORACLE TRAIN TEST
set -euo pipefail
exec bash "$(dirname "$0")/run_inference.sh" treevada "$@"
