# expat with namespace processing on (namespace_separator set). Rejects unbound
# prefixes and malformed qualified names, like the other namespace-aware parsers.
import sys, xml.parsers.expat as E

for i, ln in enumerate(open(sys.argv[1])):
    p = ln.rstrip("\n")
    data = open(p, "rb").read()
    try:
        x = E.ParserCreate(namespace_separator=" ")
        x.Parse(data, True)
        print(i, 0)
    except E.ExpatError:
        print(i, 1)
