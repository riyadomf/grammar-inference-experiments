"""Recheck JSON recall and cross-grammar acceptance on fixed samples."""

import json
import pickle
import random
import sys

from common import ROOT, RESULTS

sys.path.insert(0, str(ROOT / "artifacts/xvada"))
sys.path.insert(0, str(ROOT / "stubs"))
from grammar import Grammar
from start import START
from lark.exceptions import UnexpectedInput


class DuplicateKey(ValueError):
    pass


def unique_keys(pairs):
    keys = [key for key, _ in pairs]
    if len(keys) != len(set(keys)):
        raise DuplicateKey("Duplicate JSON key")
    return dict(pairs)


def accepts(parser, text):
    try:
        parser.parse(text)
    except UnexpectedInput:
        return False
    return True


def main():
    tests = []
    for path in sorted((ROOT / "artifacts/xvada/experiments/json/json-test").iterdir()):
        text = path.read_text()
        try:
            json.loads(text, object_pairs_hook=unique_keys)
        except DuplicateKey:
            continue
        tests.append(text)
    assert len(tests) == 994, len(tests)

    grammars, parsers, report = {}, {}, {"test_count": len(tests), "grammars": {}}
    for name, directory in [
        ("baseline", "repro-json-r1"),
        ("unique", "pilot-json-uniqkeys"),
    ]:
        grammar = Grammar(START)
        for rule in pickle.loads(
            (RESULTS / directory / "search.log.gramdict").read_bytes()
        ).values():
            grammar.add_rule(rule)
        grammars[name] = grammar
        parsers[name] = grammar.parser()
        report["grammars"][name] = {
            "accepted_tests": sum(accepts(parsers[name], text) for text in tests)
        }

    for source, target in [("baseline", "unique"), ("unique", "baseline")]:
        random.seed(0)
        grammar = grammars[source]
        samples = sorted(
            grammar.sample_positives(500, max(grammar.max_rule_distance(), 5))
        )
        count = sum(accepts(parsers[target], text) for text in samples)
        report["grammars"][source]["cross_check"] = {
            "target": target,
            "samples": len(samples),
            "accepted": count,
        }
        assert len(samples) == count == 500
    assert (
        report["grammars"]["baseline"]["accepted_tests"]
        == report["grammars"]["unique"]["accepted_tests"]
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
