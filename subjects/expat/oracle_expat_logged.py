#!/usr/bin/env python3
# Same verdict as oracle_expat.py, plus one log line per call:
# "<verdict>\t<expat error or ok>\t<repr(input)>". XVada calls the oracle
# sequentially, so appends do not interleave.
import sys, os
from xml.parsers import expat

LOG = os.environ.get(
    "ORACLE_LOG",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "oracle_calls.log"),
)
data = open(sys.argv[1], "rb").read()
p = expat.ParserCreate()
try:
    p.Parse(data, True)
    ok, why = True, "ok"
except expat.ExpatError as e:
    ok, why = False, str(e).split(":")[0]
with open(LOG, "a") as f:
    f.write(f"{int(ok)}\t{why}\t{data.decode('utf-8', 'replace')!r}\n")
sys.exit(0 if ok else 1)
