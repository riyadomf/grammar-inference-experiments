"""Fresh Expat parser per JSONL request, using the original oracle interpreter.

Repair is an experimental counterfactual, not a replacement XML validator.
Only Expat-identified duplicate attribute names are changed. DTD inputs are
excluded from repair because attribute declarations could affect semantics.
"""

import json
import sys
from xml.parsers import expat

DUPLICATE = expat.errors.codes[expat.errors.XML_ERROR_DUPLICATE_ATTRIBUTE]


def parse(data):
    parser = expat.ParserCreate()
    try:
        parser.Parse(data, True)
        return {"accepted": True, "code": None, "index": None}
    except expat.ExpatError as error:
        return {
            "accepted": False,
            "code": error.code,
            "index": parser.ErrorByteIndex,
            "error": str(error),
        }


def judge(text):
    data = text.encode("utf-8")
    strict = parse(data)
    current = strict
    edits = []
    if b"<!DOCTYPE" not in data:
        while current["code"] == DUPLICATE:
            start = current["index"]
            end = start
            while end < len(data) and data[end] not in b" \t\r\n=":
                end += 1
            if end == start or end == len(data):
                raise RuntimeError("Expat duplicate offset is not an attribute name")
            suffix = len(edits)
            fresh = ("__xvada_probe_%d" % suffix).encode("ascii")
            while fresh in data:
                suffix += 1
                fresh = ("__xvada_probe_%d" % suffix).encode("ascii")
            edits.append(
                {
                    "byte_index": start,
                    "old": data[start:end].decode("utf-8"),
                    "new": fresh.decode("ascii"),
                }
            )
            data = data[:start] + fresh + data[end:]
            current = parse(data)
            if len(edits) > len(text):
                raise RuntimeError("Non-terminating duplicate repair")
    return {
        "strict": strict,
        "repaired": current,
        "edits": edits,
        "repair_text": data.decode("utf-8") if edits else None,
    }


def main():
    print(
        json.dumps(
            {
                "python": sys.version,
                "expat": expat.EXPAT_VERSION,
                "namespace_processing": False,
            }
        ),
        flush=True,
    )
    for line in sys.stdin:
        request = json.loads(line)
        result = judge(request["text"])
        print(json.dumps({"id": request["id"], **result}), flush=True)


if __name__ == "__main__":
    main()
