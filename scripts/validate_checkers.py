"""Replay recorded input batches through the current parser checkers."""

import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile

from common import RESULTS, ROOT, rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir", type=Path, default=ROOT / "runs/checker-validation"
    )
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=False)
    reports = {}
    for source in sorted((RESULTS / "parser-differential").glob("*/verdicts.jsonl")):
        recorded = rows(source)
        kind = source.parent.name.split("-", 1)[0]
        output = args.output_dir / source.parent.name
        with tempfile.TemporaryDirectory(prefix="checker-replay-") as temporary:
            inputs = Path(temporary) / "inputs.jsonl"
            inputs.write_text("".join(json.dumps(r["s"]) + "\n" for r in recorded))
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/diff_probe_batch.py"),
                    "--inputs",
                    str(inputs),
                    "--kind",
                    kind,
                    "--out",
                    str(output),
                ],
                check=True,
                stdout=subprocess.DEVNULL,
            )
        observed = rows(output / "verdicts.jsonl")
        if observed != recorded:
            raise RuntimeError("Checker verdicts changed: " + source.parent.name)
        reports[source.parent.name] = len(observed)
        print(source.parent.name, len(observed), "matched", flush=True)
    (args.output_dir / "verification.json").write_text(
        json.dumps(reports, indent=2) + "\n"
    )


if __name__ == "__main__":
    main()
