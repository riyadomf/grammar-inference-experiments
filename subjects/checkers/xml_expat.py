import sys, xml.parsers.expat as E

for i, ln in enumerate(open(sys.argv[1])):
    p = ln.rstrip("\n")
    data = open(p, "rb").read()
    try:
        x = E.ParserCreate()
        x.Parse(data, True)
        print(i, 0)
    except E.ExpatError:
        print(i, 1)
