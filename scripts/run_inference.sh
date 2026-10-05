#!/usr/bin/env bash
# Usage: run_inference.sh TOOL NAME ORACLE TRAIN TEST [search options]
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
[[ $# -ge 5 ]] || { echo 'Expected TOOL NAME ORACLE TRAIN TEST [search options]' >&2; exit 2; }
tool=$1; name=$2
[[ "$tool" == xvada || "$tool" == treevada ]] || exit 2
[[ "$name" != */* && "$name" != . && "$name" != .. && -n "$name" ]] || exit 2
oracle=$(realpath -e "$3"); train=$(realpath -e "$4"); test_dir=$(realpath -e "$5")
shift 5
out="$ROOT/runs/$name"
mkdir -p "$ROOT/runs"
mkdir "$out"
export PYTHONPATH="$ROOT/stubs${PYTHONPATH:+:$PYTHONPATH}"
cd "$ROOT/artifacts/$tool"
prefix=(); eval_options=()
if [[ "$tool" == treevada ]]; then prefix=(external); else eval_options=(--no-antlr4); fi
{
    echo "tool $tool"
    echo "commit $(git rev-parse HEAD)"
    echo "oracle $(realpath --relative-to="$ROOT" "$oracle")"
    echo "train $(realpath --relative-to="$ROOT" "$train")"
    echo "test $(realpath --relative-to="$ROOT" "$test_dir")"
} > "$out/meta.txt"
start=$SECONDS
"$ROOT/.venv/bin/python" search.py "${prefix[@]}" "$@" "$oracle" "$train" "$out/search.log" > "$out/search.out" 2>&1
learned=$SECONDS
"$ROOT/.venv-pypy/bin/python" eval.py "${prefix[@]}" "${eval_options[@]}" "$oracle" "$test_dir" "$out/search.log" > "$out/eval.out" 2>&1
echo "search_s $((learned-start)) eval_s $((SECONDS-learned))" >> "$out/meta.txt"
tr '\r' '\n' < "$out/eval.out" | grep '^Recall:' | tail -1 >> "$out/meta.txt"
echo "Results: $out"
