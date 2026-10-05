import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

from checker_protocol import parse_verdicts
from common import ROOT, open_text, run_name
from trace_xml_generalization import Worker


class ProtocolTests(unittest.TestCase):
    def test_complete_batch(self):
        self.assertEqual(parse_verdicts("1 1\n0 0\n", 2), [True, False])

    def test_invalid_batches(self):
        for output in ("0 0\n0 1\n", "0 0\n", "0 0\n1 4\n", "1 0\n2 1\n", "invalid"):
            with (
                self.subTest(output=output),
                self.assertRaises((ValueError, RuntimeError)),
            ):
                parse_verdicts(output, 2)

    def test_missing_interpreter(self):
        with patch.dict(os.environ, {"GI_ORACLE_PYTHON": "/missing/oracle-python"}):
            with self.assertRaises(FileNotFoundError):
                Worker()

    def test_wrong_expat_version(self):
        with patch.object(Worker, "receive", return_value={"expat": "expat_0.0"}):
            with self.assertRaisesRegex(RuntimeError, "requires Expat"):
                Worker()

    def test_worker_timeout(self):
        worker = Worker.__new__(Worker)
        worker.process = Mock()
        with patch("trace_xml_generalization.select.select", return_value=([], [], [])):
            with self.assertRaisesRegex(RuntimeError, "timed out"):
                worker.receive()

    def test_worker_eof(self):
        worker = Worker.__new__(Worker)
        worker.process = Mock()
        worker.process.stdout.readline.return_value = ""
        with patch(
            "trace_xml_generalization.select.select", return_value=([1], [], [])
        ):
            with self.assertRaisesRegex(RuntimeError, "without a verdict"):
                worker.receive()

    def test_worker_response_id(self):
        worker = Worker.__new__(Worker)
        worker.process = Mock()
        worker.count = 0
        with patch.object(worker, "receive", return_value={"id": 7}):
            with self.assertRaisesRegex(RuntimeError, "ID mismatch"):
                worker.judge("<a/>")

    def test_invalid_run_names(self):
        for name in ("", ".", "..", "../outside", "x/y"):
            with self.assertRaises(ValueError):
                run_name(name)

    def test_compressed_reference(self):
        with open_text(ROOT / "results/reference/oracle_calls.log") as stream:
            self.assertEqual(sum(1 for _ in stream), 70829)

    def test_existing_output_is_not_overwritten(self):
        with tempfile.TemporaryDirectory(prefix="output collision ") as directory:
            marker = Path(directory) / "keep"
            marker.write_text("untouched")
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/diff_probe_batch.py"),
                    "--inputs",
                    str(ROOT / "results/parser-differential/inputs/xml-control.jsonl"),
                    "--kind",
                    "xml",
                    "--out",
                    directory,
                ],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(marker.read_text(), "untouched")

    def test_missing_input_is_not_a_rejection(self):
        with tempfile.TemporaryDirectory(prefix="parser input ") as directory:
            manifest = Path(directory) / "manifest"
            manifest.write_text(str(Path(directory) / "missing.xml") + "\n")
            result = subprocess.run(
                [
                    os.environ.get("GI_ORACLE_PYTHON", "python3"),
                    str(ROOT / "subjects/checkers/xml_expat.py"),
                    str(manifest),
                ],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(result.stdout, "")

    def test_input_path_with_spaces_from_other_directory(self):
        with tempfile.TemporaryDirectory(prefix="parser input ") as directory:
            sample = Path(directory) / "valid sample.xml"
            sample.write_text("<a/>")
            manifest = Path(directory) / "input list"
            manifest.write_text(str(sample) + "\n")
            result = subprocess.run(
                [
                    "python3",
                    str(ROOT / "subjects/checkers/xml_expat.py"),
                    str(manifest),
                ],
                cwd=directory,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, "0 0\n")


if __name__ == "__main__":
    unittest.main()
