"""Report exact input duplication, seed overlap, and repeat-run determinism."""

import collections
import json
from pathlib import Path

from common import ROOT, RESULTS
from trace_xml_generalization import canonical


def main():
    subjects = {}
    for directory in sorted((ROOT / "artifacts/xvada/experiments").iterdir()):
        train = directory / (directory.name + "-train")
        test = directory / (directory.name + "-test")
        if not train.is_dir() or not test.is_dir():
            continue
        seeds = {p.read_bytes() for p in train.iterdir() if p.is_file()}
        inputs = [p.read_bytes() for p in test.iterdir() if p.is_file()]
        subjects[directory.name] = {
            "train_unique": len(seeds),
            "test_files": len(inputs),
            "test_unique": len(set(inputs)),
            "train_test_overlap": len(seeds & set(inputs)),
        }
    grammars = [
        canonical(RESULTS / ("repro-json-r%d" % i) / "search.log.gramdict")
        for i in (1, 2, 3)
    ]
    print(
        json.dumps(
            {
                "subjects": subjects,
                "json_repeat_grammars_equal": grammars[0] == grammars[1] == grammars[2],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
