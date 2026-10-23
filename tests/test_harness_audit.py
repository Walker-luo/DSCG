import json
import tempfile
import unittest
from pathlib import Path

from dscg.harness_records import SampleStatus
from experiments.diagnostics.harness_audit import (
    audit_cases,
    classify_sample,
    manifest_hash,
    payload_hash,
    payload_was_delivered,
    rank_ids,
    replay_attack_predicate,
    security_result_fields,
)


class HarnessAuditTests(unittest.TestCase):
    def test_sha256_ranking_is_stable_and_seeded(self):
        ids = [f"task-{index}" for index in range(12)]
        self.assertEqual(rank_ids(ids, 20260927), rank_ids(ids, 20260927))
        self.assertNotEqual(rank_ids(ids, 20260927), rank_ids(ids, 20260928))
        self.assertEqual(len(rank_ids(ids, 20260927, limit=2)), 2)

    def test_manifest_hash_uses_one_canonical_run_manifest(self):
        manifest = {
            "suite": "workspace",
            "seed": 20260927,
            "users": ["user_task_1", "user_task_0"],
            "injections": ["injection_task_1", "injection_task_0"],
        }
        reordered = dict(manifest)
        reordered["users"] = list(reversed(manifest["users"]))
        reordered["injections"] = list(reversed(manifest["injections"]))
        self.assertEqual(manifest_hash(manifest), manifest_hash(reordered))
        self.assertEqual(len(manifest_hash(manifest)), 64)

    def test_payload_delivery_requires_payload_text_in_messages(self):
        payload = {"notice": "AUDIT-ME-42"}
        self.assertTrue(payload_was_delivered(payload, [{"content": "AUDIT-ME-42"}]))
        self.assertFalse(payload_was_delivered(payload, [{"content": "unrelated"}]))
        self.assertEqual(len(payload_hash(payload)), 64)

    def test_missing_security_result_is_infrastructure_error(self):
        self.assertEqual(
            classify_sample(
                payload_delivered=True,
                predicate_replayable=True,
                trace_replayable=True,
                utility_result=True,
                security_result=None,
            ),
            SampleStatus.INFRASTRUCTURE_ERROR,
        )

    def test_security_result_fields_never_default_missing_to_safe(self):
        attack, defense, status = security_result_fields({}, ("u0", "i0"), run_attack=True)
        self.assertIsNone(attack)
        self.assertIsNone(defense)
        self.assertEqual(status, SampleStatus.INFRASTRUCTURE_ERROR.value)

        attack, defense, status = security_result_fields({("u0", "i0"): False}, ("u0", "i0"), run_attack=True)
        self.assertFalse(attack)
        self.assertTrue(defense)
        self.assertEqual(status, SampleStatus.VALID.value)

    def test_predicate_replay_uses_final_state_oracle(self):
        self.assertFalse(replay_attack_predicate({"unauthorized_side_effects": 0}))
        self.assertTrue(replay_attack_predicate({"unauthorized_side_effects": 1}))
        with self.assertRaises(ValueError):
            replay_attack_predicate({"unrelated": True})

    def test_fixture_audit_preserves_error_denominators(self):
        cases = [
            {
                "run_id": "run",
                "suite": "workspace",
                "user_task_id": "u0",
                "injection_task_id": "i0",
                "payload": {"notice": "PAYLOAD"},
                "messages": [{"role": "user", "content": "PAYLOAD"}],
                "final_state": {"unauthorized_side_effects": 0},
                "predicate_result": False,
                "utility_result": True,
                "security_result": False,
                "trace_replayable": True,
            },
            {
                "run_id": "run",
                "suite": "workspace",
                "user_task_id": "u0",
                "injection_task_id": "i1",
                "payload": {"notice": "MISSING"},
                "messages": [{"role": "user", "content": "different"}],
                "final_state": {"unauthorized_side_effects": 0},
                "predicate_result": False,
                "utility_result": True,
                "security_result": False,
                "trace_replayable": True,
            },
        ]
        report = audit_cases(cases, seed=20260927)
        self.assertEqual(report["sample_counts"][SampleStatus.VALID.value], 1)
        self.assertEqual(
            report["sample_counts"][SampleStatus.INFRASTRUCTURE_ERROR.value], 1
        )
        self.assertEqual(len(report["manifest_hash"]), 64)
        self.assertNotIn("PAYLOAD", json.dumps(report["records"]))


if __name__ == "__main__":
    unittest.main()
