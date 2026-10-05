"""Trace XVada and apply scoped duplicate-attribute interventions."""

import argparse
import ast
import collections
import contextlib
import functools
import hashlib
import inspect
import json
import os
from pathlib import Path
import pickle
import random
import select
import shutil
import subprocess
import sys
import time
from common import ROOT, RESULTS, open_text, run_name

LAB = ROOT
ARTIFACT = LAB / "artifacts/xvada"
sys.path.insert(0, str(ARTIFACT))
sys.path.insert(0, str(LAB / "stubs"))


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


class Worker:
    def __init__(self):
        self.process = subprocess.Popen(
            [
                os.environ.get("GI_ORACLE_PYTHON")
                or shutil.which("python3")
                or "python3",
                "-S",
                str(LAB / "scripts/causal_xml_worker.py"),
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        self.info = self.receive()
        if self.info.get("expat") != "expat_2.6.1":
            self.process.stdin.close()
            self.process.wait(timeout=10)
            self.process.stdout.close()
            raise RuntimeError(
                "This experiment requires Expat 2.6.1; select its interpreter with GI_ORACLE_PYTHON. Got "
                + repr(self.info)
            )
        self.count = 0

    def receive(self):
        if not select.select([self.process.stdout], [], [], 10)[0]:
            raise RuntimeError("Oracle worker timed out")
        line = self.process.stdout.readline()
        if not line:
            raise RuntimeError("Oracle worker exited without a verdict")
        return json.loads(line)

    def judge(self, text):
        self.count += 1
        self.process.stdin.write(json.dumps({"id": self.count, "text": text}) + "\n")
        self.process.stdin.flush()
        result = self.receive()
        if result["id"] != self.count:
            raise RuntimeError("Oracle response ID mismatch")
        for name in ("strict", "repaired"):
            if type(result[name]["accepted"]) is not bool:
                raise RuntimeError("Malformed oracle verdict")
        return result

    def close(self):
        self.process.stdin.close()
        try:
            code = self.process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait()
            raise RuntimeError("Oracle worker failed to exit")
        finally:
            self.process.stdout.close()
        if code:
            raise RuntimeError("Oracle worker exit code %s" % code)


def canonical(path):
    rules = pickle.loads(path.read_bytes())
    return {
        name: sorted([list(body) for body in rule.bodies])
        for name, rule in sorted(rules.items())
    }


def verify(out, reference=RESULTS / "reference"):
    worker = Worker()
    count = 0
    mismatches = []
    source = reference / "oracle_calls.log"
    for line in open_text(source):
        accepted, reason, literal = line.rstrip("\n").split("\t", 2)
        text = ast.literal_eval(literal)
        result = worker.judge(text)
        if result["strict"]["accepted"] != bool(int(accepted)):
            mismatches.append({"line": count + 1, "text": text})
        count += 1
    worker.close()
    result = {
        "worker": worker.info,
        "checked": count,
        "source_sha256": hashlib.sha256(open_text(source).read().encode()).hexdigest(),
        "learning_queries": 69829,
        "evaluation_queries": 1000,
        "mismatches": mismatches,
    }
    write_json(out / "harness-check.json", result)
    if mismatches:
        raise RuntimeError("Worker does not reproduce historical oracle answers")
    print(json.dumps(result, indent=2))


class Trace:
    def __init__(self, out, allow):
        self.out = out
        self.allow = set(allow)
        self.stack = []
        self.counts = collections.Counter()
        self.saved = set()
        self.events = (out / "events.jsonl").open("w")
        self.queries = (out / "uncached-queries.jsonl").open("w")
        self.flips = 0
        self.instances = []

    def event(self, **value):
        self.events.write(json.dumps(value) + "\n")

    def relaxed(self):
        return "all" in self.allow or any(
            frame["id"] in self.allow for frame in self.stack
        )

    def wrap(self, module, name):
        original = getattr(module, name)
        signature = inspect.signature(original)

        @functools.wraps(original)
        def wrapped(*args, **kwargs):
            self.counts[name] += 1
            ident = "%s:%d" % (name, self.counts[name])
            values = signature.bind(*args, **kwargs).arguments
            frame = {
                "id": ident,
                "name": name,
                "args": args,
                "kwargs": kwargs,
                "random": random.getstate(),
            }
            metadata = {
                key: values[key]
                for key in ("rule_start", "body_idxs", "expansion_type", "replacee")
                if key in values
            }
            if "grammar" in values and "rule_start" in values:
                metadata["bodies"] = [
                    list(x)
                    for x in values["grammar"].rules[values["rule_start"]].bodies
                ]
            if name == "replacement_valid":
                caller = inspect.currentframe().f_back
                metadata["pair"] = {
                    key: caller.f_locals.get(key) for key in ("nt1", "nt2")
                }
                del caller
            frame["metadata"] = metadata
            if name == "expand_tokens":
                pickle.dump(
                    {"args": args[1:], "kwargs": kwargs, "random": frame["random"]},
                    (self.out / (ident.replace(":", "-") + ".pickle")).open("wb"),
                )
            self.stack.append(frame)
            self.event(
                event="enter",
                id=ident,
                parents=[f["id"] for f in self.stack[:-1]],
                **metadata,
            )
            try:
                result = original(*args, **kwargs)
                summary = result
                if name == "replacement_valid":
                    summary = {"valid": result[0], "n_candidates": len(result[1])}
                elif name in (
                    "expand_tokens",
                    "build_trees",
                    "hdd_decompose",
                    "coalesce",
                ):
                    summary = "completed"
                self.event(event="exit", id=ident, result=summary)
                return result
            finally:
                self.stack.pop()

        setattr(module, name, wrapped)
        return wrapped

    def duplicate(self, text, verdict, cached):
        contexts = [f["id"] for f in self.stack]
        self.event(
            event="duplicate",
            text=text,
            cached=cached,
            contexts=contexts,
            relaxed=self.relaxed(),
            verdict=verdict,
        )
        for frame in reversed(self.stack):
            if (
                frame["name"].startswith("generalize_")
                and frame["id"] not in self.saved
            ):
                # These token generalizers do not mutate the grammar or trees.
                pickle.dump(
                    {
                        "name": frame["name"],
                        "args": frame["args"][1:],
                        "kwargs": frame["kwargs"],
                        "random": frame["random"],
                        "metadata": frame["metadata"],
                    },
                    (self.out / (frame["id"].replace(":", "-") + ".pickle")).open("wb"),
                )
                self.saved.add(frame["id"])


def run(out, allow, reference=RESULTS / "reference"):
    import search
    import start
    import token_expansion
    import config
    from oracle import ExternalOracle, ParseException

    assert not config.USE_LLM and not config.AI_LABEL
    trace = Trace(out, allow)
    worker = Worker()

    class TracedOracle(ExternalOracle):
        def __init__(self, command):
            super().__init__(command)
            self.details = {}
            trace.instances.append(self)

        def parse(self, text, timeout=3):
            self.parse_calls += 1
            relaxed = trace.relaxed()
            key = (relaxed, text)
            cached = key in self.cache_set
            try:
                if not cached:
                    began = time.monotonic()
                    verdict = worker.judge(text)
                    self.time_spent += time.monotonic() - began
                    self.real_calls += 1
                    self.details[key] = verdict
                    self.cache_set[key] = verdict["repaired" if relaxed else "strict"][
                        "accepted"
                    ]
                    trace.queries.write(
                        json.dumps(
                            {
                                "text": text,
                                "accepted": self.cache_set[key],
                                "strict": verdict["strict"]["accepted"],
                                "contexts": [f["id"] for f in trace.stack],
                                "relaxed": relaxed,
                            }
                        )
                        + "\n"
                    )
                    if (
                        relaxed
                        and self.cache_set[key]
                        and not verdict["strict"]["accepted"]
                    ):
                        trace.flips += 1
                verdict = self.details[key]
                if verdict["strict"]["code"] == 8:
                    trace.duplicate(text, verdict, cached)
            except BaseException as error:
                # Upstream bare except clauses must not swallow worker failures.
                write_json(out / "FATAL.json", {"error": repr(error)})
                trace.events.flush()
                trace.queries.flush()
                os._exit(70)
            if self.cache_set[key]:
                return True
            raise ParseException("doesn't parse: " + text)

    for name in ("build_trees", "coalesce", "hdd_decompose", "replacement_valid"):
        trace.wrap(start, name)
    for name in (
        "generalize_whitespace_in_rule",
        "generalize_digits_in_rule",
        "generalize_letters_in_rule",
        "generalize_to_alphanum",
        "generalize_to_strings",
        "generalize_special_symbols",
    ):
        trace.wrap(token_expansion, name)
    start.expand_tokens = trace.wrap(token_expansion, "expand_tokens")
    search.ExternalOracle = TracedOracle
    metadata = {
        "worker": worker.info,
        "allow_contexts": allow,
        "random_seed": 0,
        "artifact_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ARTIFACT, text=True
        ).strip(),
        "config": {key: value for key, value in vars(config).items() if key.isupper()},
        "harness_sha256": {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [Path(__file__), LAB / "scripts/causal_xml_worker.py"]
        },
        "started": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    write_json(out / "meta.json", metadata)
    began = time.monotonic()
    try:
        with (
            (out / "search.out").open("w") as console,
            contextlib.redirect_stdout(console),
            contextlib.redirect_stderr(console),
        ):
            search.main(
                str(LAB / "subjects/expat/oracle_expat.py"),
                str(ARTIFACT / "experiments/xml/xml-train"),
                str(out / "search.log"),
            )
    finally:
        trace.events.close()
        trace.queries.close()
        worker.close()
    metadata.update(
        seconds=time.monotonic() - began,
        flips=trace.flips,
        parse_calls=trace.instances[0].parse_calls,
        real_calls=trace.instances[0].real_calls,
        saved_decisions=sorted(trace.saved),
    )
    rules = canonical(out / "search.log.gramdict")
    metadata.update(
        rules=len(rules),
        alternatives=sum(map(len, rules.values())),
        matches_original_grammar=rules == canonical(reference / "search.log.gramdict"),
    )
    if not allow:
        historical = []
        for line in open_text(reference / "oracle_calls.log"):
            accepted, _, literal = line.rstrip("\n").split("\t", 2)
            historical.append((ast.literal_eval(literal), bool(int(accepted))))
            if len(historical) == 69829:
                break
        observed = [
            (x["text"], x["accepted"])
            for x in map(json.loads, (out / "uncached-queries.jsonl").open())
        ]
        metadata["matches_original_query_sequence"] = observed == historical
        if (
            not metadata["matches_original_query_sequence"]
            or not metadata["matches_original_grammar"]
        ):
            metadata["control_validated"] = False
        else:
            metadata["control_validated"] = True
    write_json(out / "meta.json", metadata)
    print(json.dumps(metadata, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--allow-context", action="append", default=[])
    parser.add_argument("--runs-dir", type=Path, default=LAB / "runs")
    parser.add_argument("--reference-dir", type=Path, default=RESULTS / "reference")
    args = parser.parse_args()
    try:
        run_name(args.name)
    except ValueError as error:
        parser.error(str(error))
    out = args.runs_dir.resolve() / args.name
    out.mkdir(parents=True, exist_ok=False)
    if args.verify:
        verify(out, args.reference_dir.resolve())
    else:
        run(out, args.allow_context, args.reference_dir.resolve())


if __name__ == "__main__":
    main()
