"""Contract tests for the counterfactual oracle, not XVada research claims."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from causal_xml_worker import judge
from trace_xml_generalization import Worker


class OracleContract(unittest.TestCase):
    def test_valid_unchanged(self):
        for text in ("<a/>", '<a x="1"><b x="2"/></a>', '<a x="1" X="2"/>'):
            result = judge(text)
            self.assertTrue(result["strict"]["accepted"])
            self.assertEqual(result["edits"], [])

    def test_duplicate_only(self):
        for text in (
            '<a x="1" x="2"/>',
            '<a x=">" x="2"/>',
            '<a>é<b x="1" x="2"/></a>',
            '<a x="1" x="2" x="3"/>',
            '<a __xvada_probe_0="0" x="1" x="2"/>',
        ):
            result = judge(text)
            self.assertEqual(result["strict"]["code"], 8)
            self.assertTrue(result["repaired"]["accepted"])
            self.assertTrue(result["edits"])

    def test_other_errors_remain(self):
        for text in (
            '<a x="1" x="2"></b>',
            '<a x="1" x="2"/>junk',
            '<a x="&missing;" x="2"/>',
            "<a><b></a>",
        ):
            self.assertFalse(judge(text)["repaired"]["accepted"])

    def test_text_is_not_rewritten(self):
        text = '<a x="1" x="2"><![CDATA[<b x="1" x="2"/>]]><!--<c x="1" x="2"/>--></a>'
        result = judge(text)
        self.assertTrue(result["repaired"]["accepted"])
        self.assertEqual(len(result["edits"]), 1)
        self.assertIn('<![CDATA[<b x="1" x="2"/>]]>', result["repair_text"])
        self.assertIn('<!--<c x="1" x="2"/>-->', result["repair_text"])

    def test_dtd_is_excluded(self):
        result = judge('<!DOCTYPE a><a x="1" x="2"/>')
        self.assertFalse(result["repaired"]["accepted"])
        self.assertEqual(result["edits"], [])

    def test_worker_resets_and_handles_multiline(self):
        worker = Worker()
        try:
            self.assertFalse(worker.judge("<a>")["strict"]["accepted"])
            self.assertTrue(worker.judge("<b>\nline\n</b>")["strict"]["accepted"])
            self.assertFalse(worker.judge('<a x="1" x="2"/>')["strict"]["accepted"])
            self.assertTrue(worker.judge("<c/>")["strict"]["accepted"])
        finally:
            worker.close()

    def test_harness_fault_aborts_instead_of_rejecting(self):
        scripts = str(Path(__file__).resolve().parents[1] / "scripts")
        code = """
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from trace_xml_generalization import Worker, run
def broken(self, text):
    raise RuntimeError("injected worker protocol failure")
Worker.judge = broken
run(Path(sys.argv[2]), [])
"""
        with tempfile.TemporaryDirectory(prefix="causal-xml-fault-") as directory:
            result = subprocess.run(
                [sys.executable, "-c", code, scripts, directory],
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(result.returncode, 70, result.stderr)
            fatal = json.loads((Path(directory) / "FATAL.json").read_text())
            self.assertIn("injected worker protocol failure", fatal["error"])
            self.assertFalse((Path(directory) / "search.log.gramdict").exists())


if __name__ == "__main__":
    unittest.main()
