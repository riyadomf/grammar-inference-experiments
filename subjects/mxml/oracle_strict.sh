#!/bin/sh
# Valid = mxml builds a tree AND reports no diagnostics (harness exit 0).
exec "$(dirname "$0")/harness" "$1" >/dev/null 2>&1
