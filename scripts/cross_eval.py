"""Paired precision of one learned grammar under several oracles, plus recall
on several test sets.

eval.py measures precision only against the oracle used for training. Here the
same 1,000 samples (same sampler, same seed, same depth rule as eval.py) go to
every oracle, so differences come from the oracle alone.

Usage: python cross_eval.py <log_file> --oracle name=cmd ... [--test name=dir ...] [--dump DIR]
"""

import os, sys, random, pickle, json, subprocess, tempfile, argparse

LAB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(LAB, "artifacts", "xvada"))
sys.path.insert(0, os.path.join(LAB, "stubs"))
from grammar import Grammar
from start import START
from lark.exceptions import UnexpectedInput

ap = argparse.ArgumentParser()
ap.add_argument("log")
ap.add_argument("--oracle", action="append", default=[])
ap.add_argument("--test", action="append", default=[])
ap.add_argument("--dump", help="write rejected samples per oracle here")
ap.add_argument("-n", type=int, default=1000)
a = ap.parse_args()
if not a.oracle:
    ap.error("Supply at least one --oracle NAME=COMMAND")
if a.dump:
    os.makedirs(a.dump, exist_ok=False)

g = Grammar(START)
for _, rule in pickle.load(open(a.log + ".gramdict", "rb")).items():
    g.add_rule(rule)
random.seed(0)  # eval.py seeds the same way
depth = max(g.max_rule_distance(), 5)  # eval.py's depth rule
samples = sorted(g.sample_positives(a.n, depth))


def accepts(cmd, text):
    with tempfile.NamedTemporaryFile() as f:
        f.write(text.encode("utf-8"))
        f.flush()
        rc = subprocess.run(
            [cmd, f.name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=30,
        ).returncode
        if rc not in (0, 1, 3):
            raise RuntimeError("Oracle failed: %s (exit %d)" % (cmd, rc))
        return rc == 0


out = {
    "log": a.log,
    "n_samples": len(samples),
    "depth": depth,
    "precision": {},
    "recall": {},
}
verdict = {}
for spec in a.oracle:
    name, cmd = spec.split("=", 1)
    if name in verdict or os.path.basename(name) != name or name in (".", ".."):
        raise ValueError("Oracle names must be unique filename components")
    verdict[name] = [accepts(cmd, s) for s in samples]
    out["precision"][name] = round(sum(verdict[name]) / len(samples), 4)
    if a.dump:
        with open(os.path.join(a.dump, f"rejected_by_{name}.txt"), "w") as f:
            for s, ok in zip(samples, verdict[name]):
                if not ok:
                    f.write(repr(s) + "\n")
names = list(verdict)
if len(names) > 1:
    out["agreement"] = {}
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            x, y = verdict[names[i]], verdict[names[j]]
            out["agreement"][f"{names[i]}|{names[j]}"] = {
                "both_accept": sum(p and q for p, q in zip(x, y)),
                f"only_{names[i]}": sum(p and not q for p, q in zip(x, y)),
                f"only_{names[j]}": sum(q and not p for p, q in zip(x, y)),
                "both_reject": sum((not p) and (not q) for p, q in zip(x, y)),
            }
parser = g.parser()
for spec in a.test:
    name, d = spec.split("=", 1)
    files = sorted(os.listdir(d))
    ok = 0
    for fn in files:
        text = open(os.path.join(d, fn)).read()
        try:
            parser.parse(text)
            ok += 1
        except UnexpectedInput:
            pass
    out["recall"][name] = {"recall": round(ok / len(files), 4), "n": len(files)}
print(json.dumps(out, indent=1))
