#!/bin/sh
# Valid = mxml builds a tree, diagnostics allowed (harness exit 0 or 3).
"$(dirname "$0")/harness" "$1" >/dev/null 2>&1
rc=$?
[ $rc -eq 0 ] || [ $rc -eq 3 ]
