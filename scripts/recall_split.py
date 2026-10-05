"""Recompute recall for a learned XVada grammar, split by train/test overlap.

The XVada/TreeVada test sets for several subjects contain every training seed.
Training examples are reported separately from held-out inputs.
This script parses each test file with the learned grammar (same Lark parser
eval.py builds) and reports recall on all files, on files that are also
training seeds, and on the truly held-out remainder.

Usage: python recall_split.py <log_file> <train_dir> <test_dir>
"""

import os, sys, pickle, json

LAB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(LAB, "artifacts", os.environ.get("GI_TOOL", "xvada")))
sys.path.insert(0, os.path.join(LAB, "stubs"))
from grammar import Grammar
from start import START
from lark.exceptions import UnexpectedInput

log, train_dir, test_dir = sys.argv[1:4]
g = Grammar(START)
for _, rule in pickle.load(open(log + ".gramdict", "rb")).items():
    g.add_rule(rule)
parser = g.parser()

read = lambda d: {f: open(os.path.join(d, f)).read() for f in sorted(os.listdir(d))}
train = set(read(train_dir).values())
test = read(test_dir)

hits = {"leaked": [0, 0], "heldout": [0, 0]}
for name, text in test.items():
    k = "leaked" if text in train else "heldout"
    hits[k][1] += 1
    try:
        parser.parse(text)
        hits[k][0] += 1
    except UnexpectedInput:
        pass

allp = hits["leaked"][0] + hits["heldout"][0]
alln = hits["leaked"][1] + hits["heldout"][1]
out = {
    "recall_all": round(allp / alln, 4),
    "leaked_parsed": f"{hits['leaked'][0]}/{hits['leaked'][1]}",
    "recall_heldout": round(hits["heldout"][0] / hits["heldout"][1], 4)
    if hits["heldout"][1]
    else None,
    "heldout_n": hits["heldout"][1],
}
print(json.dumps(out))
