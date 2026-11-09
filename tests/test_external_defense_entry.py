"""Offline tests for the built-in defense comparison entry; factories never create clients."""
from contextlib import redirect_stderr
import io
import unittest
from unittest.mock import patch

from experiments import run_external_defense as entry


class ExternalDefenseEntryTests(unittest.TestCase):
    def capture(self, argv):
        seen = {}
        def fake(**kwargs):
            seen.update(kwargs)
            return 0
        with patch.object(entry.benchmark_runner, "main", fake):
            rc = entry.main(argv)
        return rc, seen

    def test_attack_arm_forwarding(self):
        rc, seen = self.capture([
            "--defense", "spotlighting_with_delimiting", "--name", "spotlighting",
            "--task-manifest", "/tmp/grid.json", "--fliter", "/tmp/fliter.json",
            "--attack", "typical",
        ])
        self.assertEqual(rc, 0)
        self.assertTrue(seen["origin"])
        self.assertEqual(seen["defense"], "spotlighting_with_delimiting")
        self.assertTrue(seen["run_attack"])
        self.assertFalse(seen["use_sandbox"])
        self.assertFalse(seen["use_security_checker"])
        self.assertEqual(seen["attack"], ["typical"])
        self.assertEqual(seen["audit_router_mode"], "off")
        self.assertTrue(str(seen["results_dir"]).endswith("workshop"))

    def test_clean_arm_drops_selection(self):
        rc, seen = self.capture(["--defense", "tool_filter", "--name", "tool_filter_clean", "--clean"])
        self.assertEqual(rc, 0)
        self.assertFalse(seen["run_attack"])
        self.assertIsNone(seen["fliter_path"])
        self.assertIsNone(seen["attack"])

    def test_clean_rejects_selection_flags(self):
        with self.assertRaises(SystemExit):
            with redirect_stderr(io.StringIO()):
                entry.main(["--defense", "tool_filter", "--name", "x", "--clean", "--fliter", "f.json"])

    def test_unknown_defense_rejected(self):
        with self.assertRaises(SystemExit):
            with redirect_stderr(io.StringIO()):
                entry.main(["--defense", "repeat_user_prompt", "--name", "x"])
