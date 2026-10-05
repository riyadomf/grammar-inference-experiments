"""Compare parser verdicts on grammar samples or a fixed JSONL input batch."""

import os, sys, random, pickle, subprocess, tempfile, argparse, json, collections, shutil
from checker_protocol import parse_verdicts

LAB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
B = os.path.join(LAB, "subjects", "checkers")
MX = os.path.join(LAB, "subjects", "mxml", "oracle_strict.sh")
SETS = {
    # main: namespace checking on wherever the parser offers it
    "xml": [
        ("expat_ns", ["python3", f"{B}/xml_expat_ns.py"]),
        ("lxml", ["python3", f"{B}/xml_lxml.py"]),
        ("go", [f"{B}/xml_go"]),
        ("java", ["java", "-cp", B, "XmlBatch"]),
        ("rexml", ["ruby", f"{B}/xml_rexml.rb"]),
    ],
    "json": [
        ("python", ["python3", f"{B}/json_py.py"]),
        ("node", ["node", f"{B}/json_node.js"]),
        ("jq", ["bash", f"{B}/json_jq.sh"]),
        ("ruby", ["ruby", f"{B}/json_rb.rb"]),
        ("go", [f"{B}/json_go"]),
        ("perl", ["perl", f"{B}/json_pl.pl"]),
    ],
}
EXTRA = {
    "xml": [("expat", ["python3", f"{B}/xml_expat.py"]), ("mxml", None)],
    "json": [],
}

ap = argparse.ArgumentParser()
ap.add_argument("log", nargs="?")
ap.add_argument("--inputs")
ap.add_argument("--kind", choices=("xml", "json"), required=True)
ap.add_argument("-n", type=int, default=500)
ap.add_argument("--out", required=True)
a = ap.parse_args()
if bool(a.log) == bool(a.inputs):
    ap.error("Supply either a grammar log or --inputs")
if os.path.exists(a.out):
    ap.error("Output directory already exists")
if a.inputs:
    samples = [json.loads(l) for l in open(a.inputs) if l.strip()]
    depth = None
else:
    sys.path.insert(0, os.path.join(LAB, "artifacts", "xvada"))
    sys.path.insert(0, os.path.join(LAB, "stubs"))
    from grammar import Grammar
    from start import START

    g = Grammar(START)
    for _, r in pickle.load(open(a.log + ".gramdict", "rb")).items():
        g.add_rule(r)
    random.seed(0)
    depth = max(g.max_rule_distance(), 5)
    samples = sorted(g.sample_positives(a.n, depth))
if not samples or not all(isinstance(s, str) for s in samples):
    ap.error("Expected a nonempty batch of strings")
temporary = tempfile.TemporaryDirectory(prefix="parser-comparison-")
tmp = temporary.name
paths = []
for i, s in enumerate(samples):
    p = os.path.join(tmp, f"s{i}")
    open(p, "wb").write(s.encode("utf-8", "surrogateescape"))
    paths.append(p)
man = os.path.join(tmp, "manifest")
open(man, "w").write("\n".join(paths) + "\n")


def run(name, cmd):
    if cmd is None:  # Strict mode rejects parsed documents with diagnostics (exit 3).
        out = []
        for p in paths:
            rc = subprocess.run(
                [MX, p],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=30,
            ).returncode
            if rc not in (0, 1, 3):
                raise RuntimeError("Mini-XML harness failed: %s" % rc)
            out.append(rc == 0)
        return out
    r = subprocess.run(cmd + [man], capture_output=True, text=True, timeout=3600)
    if r.returncode != 0:
        sys.exit(f"checker {name} failed rc={r.returncode}: {r.stderr[:300]}")
    return parse_verdicts(r.stdout, len(paths))


main = SETS[a.kind]
extra = EXTRA[a.kind]
verd = {n: run(n, c) for n, c in main + extra}
names = [n for n, _ in main]
os.makedirs(a.out, exist_ok=False)
hist = collections.Counter()
allacc = allrej = split = 0
with open(os.path.join(a.out, "verdicts.jsonl"), "w") as f:
    for i, s in enumerate(samples):
        acc = {n: verd[n][i] for n in verd}
        f.write(json.dumps({"s": s, "accept": acc}) + "\n")
        k = sum(acc[n] for n in names)
        hist[k] += 1
        if k == len(names):
            allacc += 1
        elif k == 0:
            allrej += 1
        else:
            split += 1
summary = {
    "source": a.inputs or a.log,
    "kind": a.kind,
    "depth": depth,
    "n": len(samples),
    "main_parsers": names,
    "extra_parsers": [n for n, _ in extra],
    "all_accept": allacc,
    "all_reject": allrej,
    "split": split,
    "hist": dict(sorted(hist.items())),
}
json.dump(summary, open(os.path.join(a.out, "summary.json"), "w"), indent=1)
print(json.dumps(summary))
temporary.cleanup()
