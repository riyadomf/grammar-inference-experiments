"""Recall of a learned XVada grammar, one fresh process per test file.

Each file is parsed in its own child process with a wall-clock limit and an
address-space cap, a few at a time. A crash or an abort at the cap affects only
that file. Every result is appended to a JSONL file as soon as it is known, so
the run can be resumed: files already in the output are skipped.

Statuses: parsed, failed (grammar rejects it), timeout (no answer in time),
crashed (child exited abnormally, e.g. PyPy aborting at the memory cap).

Usage: python recall_robust.py <log_file> <test_dir> <out.jsonl> [--jobs N] [--timeout S] [--mem-mb M]
"""

import os, sys, json, argparse, subprocess, threading
from concurrent.futures import ThreadPoolExecutor

LAB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CHILD = r"""
import os, sys, pickle, resource
limit = int(sys.argv[4]) * 1024 * 1024
resource.setrlimit(resource.RLIMIT_AS, (limit, limit))
sys.path.insert(0, os.path.join(sys.argv[1], "artifacts", "xvada"))
sys.path.insert(0, os.path.join(sys.argv[1], "stubs"))
from grammar import Grammar
from start import START
from lark.exceptions import UnexpectedInput
g = Grammar(START)
for _, r in pickle.load(open(sys.argv[2] + ".gramdict", "rb")).items():
    g.add_rule(r)
p = g.parser()
text = open(sys.argv[3]).read()
try:
    p.parse(text)
except UnexpectedInput:
    sys.exit(10)
sys.exit(0)
"""

ap = argparse.ArgumentParser()
ap.add_argument("log")
ap.add_argument("test_dir")
ap.add_argument("out")
ap.add_argument("--jobs", type=int, default=2)
ap.add_argument("--timeout", type=int, default=300)
ap.add_argument("--mem-mb", type=int, default=3000)
a = ap.parse_args()
if min(a.jobs, a.timeout, a.mem_mb) <= 0:
    ap.error("jobs, timeout, and mem-mb must be positive")

done = set()
if os.path.exists(a.out):
    for line in open(a.out):
        done.add(json.loads(line)["file"])
files = [f for f in sorted(os.listdir(a.test_dir)) if f not in done]
lock = threading.Lock()
env = dict(os.environ, PYTHONPATH=os.path.join(LAB, "stubs"))
py = os.path.join(LAB, ".venv-pypy", "bin", "python")


def one(fn):
    try:
        r = subprocess.run(
            [py, "-c", CHILD, LAB, a.log, os.path.join(a.test_dir, fn), str(a.mem_mb)],
            env=env,
            timeout=a.timeout,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        status = {0: "parsed", 10: "failed"}.get(r.returncode, "crashed")
    except subprocess.TimeoutExpired:
        status = "timeout"
    with lock:
        with open(a.out, "a") as f:
            f.write(json.dumps({"file": fn, "status": status}) + "\n")


print(f"{len(done)} already done, {len(files)} to go", file=sys.stderr, flush=True)
with ThreadPoolExecutor(a.jobs) as ex:
    list(ex.map(one, files))
