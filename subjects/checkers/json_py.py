import sys, json

for i, ln in enumerate(open(sys.argv[1])):
    p = ln.rstrip("\n")
    data = open(p, "rb").read()
    try:
        json.loads(data.decode("utf-8", "surrogateescape"))
        print(i, 0)
    except (json.JSONDecodeError, UnicodeError):
        print(i, 1)
