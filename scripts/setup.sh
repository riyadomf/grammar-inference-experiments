#!/usr/bin/env bash
# Install the pinned artifacts and local Python environments.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
mode=${1:---core}
[[ "$mode" == --core || "$mode" == --all ]] || { echo 'Usage: scripts/setup.sh [--core|--all]' >&2; exit 2; }
[[ $(uname -s) == Linux && $(uname -m) == x86_64 ]] || { echo 'The supplied benchmark parsers require Linux x86_64.' >&2; exit 2; }
command -v uv >/dev/null || { echo 'Install uv before running setup.' >&2; exit 2; }
mkdir -p "$ROOT/artifacts"

fetch() {
    local name=$1 url=$2 revision=$3 target="$ROOT/artifacts/$1"
    if [[ ! -d "$target" ]]; then
        git clone --no-hardlinks "$url" "$target"
        git -C "$target" switch --detach "$revision"
    fi
    [[ $(git -C "$target" rev-parse HEAD) == "$revision" ]] || { echo "Unexpected revision: $target" >&2; exit 2; }
}

fetch xvada https://github.com/rifatarefin/xvada.git af167eb842ae79dacbe415bb32fcb62d9f4aa619
fetch treevada https://github.com/rifatarefin/treevada.git 44fb606bdc97e9145f7f730ca951ba24a15052f8
patch="$ROOT/patches/0001-Run-without-an-API-key-and-on-Python-3.12.patch"
if git -C "$ROOT/artifacts/xvada" apply --check "$patch" 2>/dev/null; then
    git -C "$ROOT/artifacts/xvada" apply "$patch"
else
    git -C "$ROOT/artifacts/xvada" apply --reverse --check "$patch"
fi
if [[ ! -x "$ROOT/.venv/bin/python" ]]; then uv venv --python 3.10.20 "$ROOT/.venv"; fi
if [[ ! -x "$ROOT/.venv-pypy/bin/python" ]]; then uv venv --python pypy@3.10.16 "$ROOT/.venv-pypy"; fi
uv pip install --python "$ROOT/.venv/bin/python" -r "$ROOT/requirements.txt"
uv pip install --python "$ROOT/.venv-pypy/bin/python" -r "$ROOT/requirements.txt"

if [[ "$mode" == --all ]]; then
    for program in cc make go javac java node ruby perl jq; do
        command -v "$program" >/dev/null || { echo "Missing optional dependency: $program" >&2; exit 2; }
    done
    python3 -c 'import lxml.etree'
    ruby -e 'require "rexml/document"; require "json"'
    perl -MJSON::PP -e 1
    fetch mxml https://github.com/michaelrsweet/mxml.git 0d5afc4278d7a336d554602b951c2979c3f8f296
    (cd "$ROOT/artifacts/mxml" && ./configure --disable-shared && make -j2 libmxml4.a)
    cc -O2 -I"$ROOT/artifacts/mxml" "$ROOT/subjects/mxml/harness.c" \
       "$ROOT/artifacts/mxml/libmxml4.a" -lpthread -lm -o "$ROOT/subjects/mxml/harness"
    go build -o "$ROOT/subjects/checkers/xml_go" "$ROOT/subjects/checkers/xml_go.go"
    go build -o "$ROOT/subjects/checkers/json_go" "$ROOT/subjects/checkers/json_go.go"
    javac "$ROOT/subjects/checkers/XmlBatch.java"
fi
PYTHONPATH="$ROOT/scripts:$ROOT/stubs" "$ROOT/.venv/bin/python" "$ROOT/scripts/environment.py"
