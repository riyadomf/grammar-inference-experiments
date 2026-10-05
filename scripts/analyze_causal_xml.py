"""Compare the four XML interventions and check their shared trace prefix."""

import argparse
import json
import pickle
from pathlib import Path

from trace_xml_generalization import LAB, Worker, write_json
from grammar import Grammar
from parse_tree import START
from lark.exceptions import UnexpectedInput
from common import RESULTS, rows


def read_rows(path):
    return rows(path)


def prefix_to(rows, identifier):
    for index, row in enumerate(rows):
        if row.get("event") == "enter" and row.get("id") == identifier:
            return rows[: index + 1]
    raise RuntimeError("Missing target event: " + identifier)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs-dir", type=Path, default=RESULTS)
    parser.add_argument("--output-dir", type=Path, default=LAB / "runs/analysis")
    args = parser.parse_args()
    names = [
        "causal-xml-control",
        "causal-xml-one-decision",
        "causal-xml-final-expansion",
        "causal-xml-repair-all",
    ]
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=False)
    control_rows = read_rows(args.runs_dir / names[0] / "events.jsonl")
    baseline = {
        r["file"]: r for r in read_rows(args.runs_dir / names[0] / "recall.jsonl")
    }
    summaries = {}
    grammar_parsers = {}
    for name in names:
        directory = args.runs_dir / name
        metadata = json.loads((directory / "meta.json").read_text())
        evaluation = json.loads((directory / "evaluation.json").read_text())
        rows = read_rows(directory / "events.jsonl")
        if name in names[1:3]:
            target = metadata["allow_contexts"][0]
            matched = prefix_to(control_rows, target) == prefix_to(rows, target)
            if not matched:
                raise RuntimeError("Trace differs before intervention: " + name)
            metadata["identical_events_through_target_entry"] = True
        recall = read_rows(directory / "recall.jsonl")
        gained = [
            r["file"]
            for r in recall
            if r["status"] == "parsed" and baseline[r["file"]]["status"] == "rejected"
        ]
        lost = [
            r["file"]
            for r in recall
            if r["status"] == "rejected" and baseline[r["file"]]["status"] == "parsed"
        ]
        unknown = [r for r in recall if r["status"] not in ("parsed", "rejected")]
        summaries[name] = {
            "metadata": metadata,
            "evaluation": evaluation,
            "gained_files": gained,
            "lost_files": lost,
            "unknown": unknown,
        }
        rules = pickle.loads((directory / "search.log.gramdict").read_bytes())
        grammar = Grammar(START)
        for rule in rules.values():
            grammar.add_rule(rule)
        grammar_parsers[name] = grammar.parser()
    probes = [
        "<e>FreshName</e>",
        "<e>freshname</e>",
        "<e>UPPERCASE</e>",
        '<e FreshName="value"><a/></e>',
        '<e x="1" y="2"><a/></e>',
        '<e x="1" x="2"><a/></e>',
        "<e>text</d>",
    ]
    worker = Worker()
    results = []
    try:
        for text in probes:
            result = {
                "text": text,
                "strict_oracle": worker.judge(text)["strict"]["accepted"],
                "grammars": {},
            }
            for name, parser in grammar_parsers.items():
                try:
                    parser.parse(text)
                    result["grammars"][name] = True
                except UnexpectedInput:
                    result["grammars"][name] = False
            results.append(result)
    finally:
        worker.close()
    duplicates = [r for r in control_rows if r["event"] == "duplicate"]
    write_json(
        out / "summary.json",
        {
            "runs": summaries,
            "probes": results,
            "learning_duplicate_events": len(duplicates),
            "uncached_learning_duplicates": sum(not r["cached"] for r in duplicates),
        },
    )
    for name, result in summaries.items():
        print(
            name,
            json.dumps(result["evaluation"]),
            "gained",
            len(result["gained_files"]),
            "lost",
            len(result["lost_files"]),
        )
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
