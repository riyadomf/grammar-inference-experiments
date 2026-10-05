#!/usr/bin/env python3
"""Benchmark JSON oracle with an additional unique-key constraint."""

import sys, subprocess, json, os
from pathlib import Path

GOLD = str(
    Path(__file__).resolve().parents[1] / "artifacts/xvada/experiments/json/parse_json"
)
LOG = os.environ.get("ORACLE_LOG")


def log(text):
    if LOG:
        with open(LOG, "a") as handle:
            handle.write(text + "\n")


path = sys.argv[1]
code = subprocess.run(
    [GOLD, path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
).returncode
if code not in (0, 1):
    raise RuntimeError("Benchmark oracle failed: %s" % code)
if code == 1:
    sys.exit(1)
text = open(path, encoding="utf-8", errors="surrogateescape").read()
dup = []


def hook(pairs):
    ks = [k for k, _ in pairs]
    if len(ks) != len(set(ks)):
        dup.append(sorted({k for k in ks if ks.count(k) > 1}))
    return dict(pairs)


try:
    json.loads(text, object_pairs_hook=hook)
except (json.JSONDecodeError, UnicodeError):
    # Retain the benchmark verdict when Python cannot check its accepted input.
    log("PYFAIL\t" + repr(text[:200]))
    sys.exit(0)
if dup:
    log("DUP\t" + repr(dup[0][:5]) + "\t" + repr(text[:200]))
    sys.exit(1)
sys.exit(0)
