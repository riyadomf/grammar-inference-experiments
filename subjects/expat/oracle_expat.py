#!/usr/bin/env python3
# Namespace processing is intentionally disabled.
import sys
from xml.parsers import expat

p = expat.ParserCreate()
try:
    with open(sys.argv[1], "rb") as f:
        p.Parse(f.read(), True)
except expat.ExpatError:
    sys.exit(1)
