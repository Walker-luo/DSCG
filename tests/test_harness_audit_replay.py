import json
import tempfile
import unittest
from pathlib import Path

from experiments.harness_audit import audit_fixture_file


class HarnessAuditReplayTests(unittest.TestCase):
    def test_fixture_report_is_replayable_and_compact(self):
        fixture = [
            {
                "run_id": "run",
                "suite": "workspace",
                "user_task_id": "u0",
                "injection_task_id": "i0",
                "payload": {"notice": "FIXTURE-PAYLOAD"},
                "messages": [{"role": "user", "content": "FIXTURE-PAYLOAD"}],
                "final_state": {"unauthorized_side_effects": 0},
                "predicate_result": False,
                "utility_result": True,
                "security_result": False,
                "trace_replayable": True,
            }
        ]
        with tempfile.TemporaryDirectory() as directory:
            fixture_path = Path(directory) / "fixture.json"
            output_path = Path(directory) / "report.json"
            fixture_path.write_text(json.dumps(fixture), encoding="utf-8")
            report = audit_fixture_file(fixture_path, output_path, seed=20260927)
            saved = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(saved, report)
        self.assertEqual(saved["sample_counts"]["valid"], 1)
        self.assertNotIn("messages", json.dumps(saved))
        self.assertNotIn("FIXTURE-PAYLOAD", json.dumps(saved))


if __name__ == "__main__":
    unittest.main()
