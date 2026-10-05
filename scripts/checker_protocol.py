"""Validate the batch checkers' index/verdict protocol."""


def parse_verdicts(output, count):
    verdicts = {}
    for line in output.splitlines():
        fields = line.split()
        if len(fields) != 2:
            raise RuntimeError("Malformed checker response")
        index, value = fields
        index = int(index)
        if index in verdicts or value not in {"0", "1"}:
            raise RuntimeError("Duplicate index or invalid checker verdict")
        verdicts[index] = value == "0"
    if sorted(verdicts) != list(range(count)):
        raise RuntimeError("Checker did not answer every input")
    return [verdicts[i] for i in range(count)]
