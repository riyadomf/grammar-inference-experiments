"""Check recorded XML results, differential counts, and file checksums."""

import collections
import hashlib
import json
from pathlib import Path

from common import RESULTS, ROOT, rows


def main():
    expected = {
        "causal-xml-control": (234, 828, 33, 191),
        "causal-xml-one-decision": (310, 885, 34, 144),
        "causal-xml-final-expansion": (842, 803, 31, 135),
        "causal-xml-repair-all": (842, 935, 20, 107),
    }
    for name, (recall, precision, rules, alternatives) in expected.items():
        directory = RESULTS / name
        report = json.loads((directory / "evaluation.json").read_text())
        heldout = [
            r
            for r in rows(directory / "recall.jsonl")
            if not r["leaked"] and r["strict_valid"]
        ]
        accepted = sum(
            r["strict"]["accepted"] for r in rows(directory / "precision.jsonl")
        )
        assert len(heldout) == 973
        assert sum(r["status"] == "parsed" for r in heldout) == recall
        assert accepted == precision
        assert report["rules_including_start"] == rules
        assert report["alternatives_including_start"] == alternatives
        assert report["recall"]["strict_valid_heldout"] == dict(
            collections.Counter(r["status"] for r in heldout)
        )
        assert report["precision"]["accepted"] == accepted
        print("%s: %d/973 held-out, %d/1000 precision" % (name, recall, precision))
    for path in sorted((RESULTS / "parser-differential").glob("*/summary.json")):
        summary = json.loads(path.read_text())
        verdicts = rows(path.parent / "verdicts.jsonl")
        parsers = summary["main_parsers"]
        counts = collections.Counter(
            sum(r["accept"][p] for p in parsers) for r in verdicts
        )
        assert len(verdicts) == summary["n"]
        assert summary["split"] == sum(
            n for k, n in counts.items() if 0 < k < len(parsers)
        )
        assert summary["all_accept"] == counts[len(parsers)]
        assert summary["all_reject"] == counts[0]
    manifest = RESULTS / "checksums.json"
    if not manifest.exists():
        raise RuntimeError("Missing recorded-evidence checksum manifest")
    for name, checksum in json.loads(manifest.read_text()).items():
        path = (ROOT / name).resolve()
        if ROOT not in path.parents:
            raise RuntimeError("Invalid manifest path")
        assert hashlib.sha256(path.read_bytes()).hexdigest() == checksum, name
    print("Recorded tables and checksums verified.")


if __name__ == "__main__":
    main()
