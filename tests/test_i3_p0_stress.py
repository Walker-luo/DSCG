import json
import tempfile
import unittest
from pathlib import Path

from experiments.i3_p0_stress import REQUIRED_CASES, audit_i3, write_report


class I3P0StressTests(unittest.TestCase):
    def test_fixture_contains_all_required_recovery_paths(self):
        self.assertEqual(
            set(REQUIRED_CASES),
            {
                "in_scope_retry",
                "unauthorized_tool",
                "expanded_object_scope",
                "disable_checks",
                "forged_administrator",
                "stale_ticket_replay",
                "modified_destination",
                "duplicate_submission",
            },
        )

    def test_p0_blocks_unauthorized_recovery_and_keeps_in_scope_retry(self):
        report = audit_i3()
        self.assertEqual(report["status"], "no_go")
        self.assertEqual(len(report["records"]), len(REQUIRED_CASES))
        by_name = {record["case"]: record for record in report["records"]}
        self.assertEqual(by_name["in_scope_retry"]["outcome"], "executed")
        for case in REQUIRED_CASES:
            if case != "in_scope_retry":
                self.assertEqual(by_name[case]["outcome"], "blocked")
        self.assertEqual(report["counts"]["executed"], 1)
        self.assertEqual(report["counts"]["blocked"], 7)

    def test_report_is_compact_and_serializable(self):
        report = audit_i3()
        encoded = json.dumps(report, ensure_ascii=False)
        self.assertNotIn("admin_tool", encoded.lower())
        self.assertNotIn("disable checks", encoded.lower())
        self.assertNotIn("args", encoded)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "i3.json"
            write_report(report, path)
            saved = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(saved, report)
        self.assertEqual(saved["status"], "no_go")


if __name__ == "__main__":
    unittest.main()
