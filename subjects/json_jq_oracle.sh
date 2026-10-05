#!/bin/bash
out=$(jq -c . "$1" 2>/dev/null) || exit 1
n=$(printf '%s' "$out" | grep -c .)
[ "$n" -eq 1 ] && exit 0 || exit 1
