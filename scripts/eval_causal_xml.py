"""Evaluate the XML experiment with strict Expat and held-out recall."""

import argparse
import collections
import json
import pickle
import random
import resource
import signal
from pathlib import Path
from common import run_name

from trace_xml_generalization import LAB, Worker, write_json
from grammar import Grammar
from parse_tree import START
from lark.exceptions import UnexpectedInput


class ParseTimeout(Exception):
    pass


def expired(signum, frame):
    raise ParseTimeout()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name")
    parser.add_argument("--runs-dir", type=Path, default=LAB / "runs")
    args = parser.parse_args()
    out = args.runs_dir.resolve() / run_name(args.name)
    if (out / "evaluation.json").exists():
        raise RuntimeError("Refusing to overwrite completed evaluation")
    limit = 3 * 1024**3
    resource.setrlimit(resource.RLIMIT_AS, (limit, limit))
    rules = pickle.loads((out / "search.log.gramdict").read_bytes())
    grammar = Grammar(START)
    for rule in rules.values():
        grammar.add_rule(rule)
    (out / "grammar.txt").write_text(str(grammar))
    random.seed(0)
    depth = max(grammar.max_rule_distance(), 5)
    samples = sorted(grammar.sample_positives(1000, depth))
    worker = Worker()
    precision = collections.Counter()
    with (out / "precision.jsonl").open("w") as handle:
        for text in samples:
            verdict = worker.judge(text)
            precision[
                "accepted"
                if verdict["strict"]["accepted"]
                else str(verdict["strict"]["code"])
            ] += 1
            handle.write(json.dumps({"text": text, **verdict}) + "\n")
    seed_dir = LAB / "artifacts/xvada/experiments/xml/xml-train"
    test_dir = LAB / "artifacts/xvada/experiments/xml/xml-test"
    seeds = {path.read_text() for path in seed_dir.iterdir()}
    grammar_parser = grammar.parser()
    signal.signal(signal.SIGALRM, expired)
    groups = collections.defaultdict(collections.Counter)
    with (out / "recall.jsonl").open("w") as handle:
        for path in sorted(test_dir.iterdir()):
            text = path.read_text()
            strict_valid = worker.judge(text)["strict"]["accepted"]
            leaked = text in seeds
            try:
                signal.setitimer(signal.ITIMER_REAL, 10)
                grammar_parser.parse(text)
                status = "parsed"
            except UnexpectedInput:
                status = "rejected"
            except ParseTimeout:
                status = "timeout"
            except MemoryError:
                status = "memory"
            finally:
                signal.setitimer(signal.ITIMER_REAL, 0)
            groups["all"][status] += 1
            if not leaked:
                groups["heldout"][status] += 1
            if strict_valid:
                groups["strict_valid"][status] += 1
                if not leaked:
                    groups["strict_valid_heldout"][status] += 1
            handle.write(
                json.dumps(
                    {
                        "file": path.name,
                        "status": status,
                        "leaked": leaked,
                        "strict_valid": strict_valid,
                    }
                )
                + "\n"
            )
            handle.flush()
    worker.close()
    result = {
        "worker": worker.info,
        "rules_including_start": len(rules),
        "alternatives_including_start": sum(len(r.bodies) for r in rules.values()),
        "sample_seed": 0,
        "sample_depth": depth,
        "samples": len(samples),
        "precision": precision,
        "recall": groups,
        "per_parse_limit_s": 10,
        "process_memory_limit_gib": 3,
    }
    write_json(out / "evaluation.json", result)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
