#!/bin/bash
# Same verdict as parse_json; also logs "rc<TAB>base64(input)" per call.
PJ="$(dirname "$0")/../artifacts/xvada/experiments/json/parse_json"
"$PJ" "$1" >/dev/null 2>&1; rc=$?
: "${PJLOG:?Set PJLOG to the output log path}"
printf '%d\t%s\n' "$rc" "$(base64 -w0 "$1")" >> "$PJLOG"
exit $rc
