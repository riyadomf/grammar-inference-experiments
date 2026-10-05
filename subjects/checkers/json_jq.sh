#!/bin/bash
command -v jq >/dev/null || exit 127
error_log=$(mktemp)
trap 'rm -f "$error_log"' EXIT
i=0
while IFS= read -r p; do
  [ -r "$p" ] || exit 2
  out=$(jq -c . "$p" 2>"$error_log"); rc=$?
  if [ "$rc" -ne 0 ]; then
    if { [ "$rc" -ne 4 ] && [ "$rc" -ne 5 ]; } || ! grep -q 'parse error:' "$error_log"; then
      cat "$error_log" >&2
      exit "$rc"
    fi
  fi
  n=$(printf '%s' "$out" | grep -c .)
  if [ $rc -eq 0 ] && [ "$n" -eq 1 ]; then echo "$i 0"; else echo "$i 1"; fi
  i=$((i+1))
done < "$1"
