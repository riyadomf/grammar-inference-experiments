"""Group samples rejected by mxml by the first diagnostic mxml prints.

Input: a file of repr()'d strings, one per line (cross_eval.py --dump output).
Numbers, quoted names and line numbers in messages are masked so messages of
the same kind group together.
"""

import sys, ast, re, subprocess, tempfile, collections, os

H = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "subjects/mxml/harness"
)
c = collections.Counter()
ex = {}
for line in open(sys.argv[1]):
    s = ast.literal_eval(line)
    with tempfile.NamedTemporaryFile() as f:
        f.write(s.encode())
        f.flush()
        out = subprocess.run([H, f.name], capture_output=True).stdout.decode(
            "utf-8", "replace"
        )
    diags = [l.split("\t", 1)[1] for l in out.splitlines() if l.startswith("DIAG\t")]
    key = diags[0] if diags else "(no diagnostic; rejected silently)"
    key = re.sub(r"<[^>]*>", "<TAG>", key)
    key = re.sub(r"'[^']*'", "'X'", key)
    key = re.sub(r"line \d+", "line N", key)
    key = re.sub(r"0x[0-9a-fA-F]+", "0xNN", key)
    c[key] += 1
    ex.setdefault(key, s[:120])
tot = sum(c.values())
for k, v in c.most_common():
    print(f"{v:5} {100 * v / tot:5.1f}%  {k}\n              e.g. {ex[k]!r}")
