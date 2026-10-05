"""Replay saved token-generalization decisions with identical entry RNG state."""

import argparse
import collections
import json
import pickle
import random
from pathlib import Path

from trace_xml_generalization import LAB, Worker, write_json
from common import RESULTS, rows, run_name
import token_expansion
from oracle import ParseException


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("control")
    parser.add_argument("name")
    parser.add_argument("--runs-dir", type=Path, default=RESULTS)
    parser.add_argument("--output-dir", type=Path, default=LAB / "runs")
    args = parser.parse_args()
    source = args.runs_dir.resolve() / run_name(args.control)
    out = args.output_dir.resolve() / run_name(args.name)
    out.mkdir(parents=True, exist_ok=False)
    events = rows(source / "events.jsonl")
    outcomes = {row["id"]: row["result"] for row in events if row["event"] == "exit"}
    worker = Worker()
    summaries = []
    try:
        for checkpoint in sorted(source.glob("generalize*.pickle")):
            pair = {}
            identifier = checkpoint.stem.rsplit("-", 1)
            identifier = ":".join(identifier)
            for relaxed in (False, True):
                saved = pickle.loads(checkpoint.read_bytes())
                random.setstate(saved["random"])
                queries = []

                class Oracle:
                    def parse(self, text):
                        verdict = worker.judge(text)
                        accepted = verdict["repaired" if relaxed else "strict"][
                            "accepted"
                        ]
                        queries.append({"text": text, "accepted": accepted, **verdict})
                        if not accepted:
                            raise ParseException(text)
                        return True

                result = getattr(token_expansion, saved["name"])(
                    Oracle(), *saved["args"], **saved["kwargs"]
                )
                key = "relaxed" if relaxed else "strict"
                with (out / (checkpoint.stem + "-" + key + ".jsonl")).open(
                    "w"
                ) as handle:
                    for query in queries:
                        handle.write(json.dumps(query) + "\n")
                pair[key] = {
                    "result": result,
                    "queries": len(queries),
                    "flips": sum(
                        q["accepted"] and not q["strict"]["accepted"] for q in queries
                    ),
                    "rejection_codes": dict(
                        collections.Counter(
                            q["strict"]["code"] for q in queries if not q["accepted"]
                        )
                    ),
                }
            strict_matches = (
                json.loads(json.dumps(pair["strict"]["result"])) == outcomes[identifier]
            )
            summary = {
                "id": identifier,
                "metadata": saved["metadata"],
                "strict_matches_trace": strict_matches,
                **pair,
            }
            summaries.append(summary)
            if not strict_matches:
                raise RuntimeError(
                    "Checkpoint replay disagrees with recorded decision: " + identifier
                )
    finally:
        worker.close()
    write_json(out / "summary.json", {"worker": worker.info, "decisions": summaries})
    print(json.dumps(summaries, indent=2))


if __name__ == "__main__":
    main()
