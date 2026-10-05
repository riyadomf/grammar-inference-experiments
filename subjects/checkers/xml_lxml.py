import sys, lxml.etree as L

for i, ln in enumerate(open(sys.argv[1])):
    p = ln.rstrip("\n")
    try:
        L.parse(p)
        print(i, 0)
    except L.XMLSyntaxError:
        print(i, 1)
