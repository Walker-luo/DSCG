import unittest

from dscg.harness_records import RunRecord, SampleRecord, SampleStatus


class HarnessRecordTests(unittest.TestCase):
    def make_record(self, **overrides):
        values = {
            "run_id": "run-001",
            "suite_name": "workspace",
            "task_id": "task-001",
            "payload_delivered": True,
            "payload_hash": "sha256:payload",
            "predicate_result": True,
            "utility_result": True,
        }
        values.update(overrides)
        return SampleRecord(**values)

    def test_accepts_all_declared_statuses(self):
        statuses = (
            "valid",
            "model_error",
            "policy_error",
            "tool_error",
            "timeout",
            "infrastructure_error",
            "skipped",
        )

        for status in statuses:
            with self.subTest(status=status):
                record = self.make_record(sample_status=status)
                self.assertIs(record.sample_status, SampleStatus(status))
                self.assertEqual(record.compact_dict()["sample_status"], status)

    def test_rejects_unknown_status(self):
        with self.assertRaisesRegex(ValueError, "unknown sample status"):
            self.make_record(sample_status="not-a-status")

    def test_missing_security_results_remain_missing_for_non_valid_sample(self):
        record = self.make_record(
            sample_status=SampleStatus.POLICY_ERROR,
            predicate_result=None,
            utility_result=None,
        )

        compact = record.compact_dict()

        self.assertIsNone(compact["predicate_result"])
        self.assertIsNone(compact["utility_result"])
        self.assertNotEqual(compact["predicate_result"], False)
        self.assertNotEqual(compact["utility_result"], False)

    def test_compact_dict_is_allowlisted_and_bounded(self):
        record = self.make_record(
            run_id="r" * 600,
            suite_name="s" * 600,
            task_id="t" * 600,
            error_type="error-type-" + "e" * 600,
            payload_hash="sha256:" + "h" * 600,
            payload="raw payload that must stay out of compact output",
            candidate_details={"tool_arguments": {"secret": "candidate-secret"}},
            action_details={"arguments": {"secret": "action-secret"}},
            action_counts={f"counter-{index}": index for index in range(80)},
            final_state={
                "summary": "completed",
                "raw_prompt": "prompt-secret" * 100,
                "environment": {
                    "complete_state": "environment-secret" * 100,
                },
                "nested": {"level": {"deeper": {"value": "x" * 600}}},
            },
        )

        compact = record.compact_dict()

        self.assertEqual(
            set(compact),
            {
                "run_id",
                "suite_name",
                "task_id",
                "sample_status",
                "error_type",
                "payload_delivered",
                "payload_hash",
                "predicate_result",
                "utility_result",
                "action_counts",
                "final_state",
            },
        )
        for key in ("run_id", "suite_name", "task_id", "error_type", "payload_hash"):
            self.assertLessEqual(len(compact[key]), 256)
        self.assertLessEqual(len(compact["action_counts"]), 32)
        self.assertNotIn("raw_prompt", compact["final_state"])
        self.assertNotIn("environment", compact["final_state"])
        self.assertNotIn("prompt-secret", repr(compact))
        self.assertNotIn("candidate-secret", repr(compact))
        self.assertNotIn("action-secret", repr(compact))

    def test_full_dict_is_opt_in_but_details_remain_bounded(self):
        record = self.make_record(
            payload={
                "payload_text": "payload-" + "p" * 600,
            },
            candidate_details={
                "tool": "lookup",
                "arguments": {"query": "q" * 600},
            },
            action_details={
                "tool": "send_message",
                "arguments": {"body": "b" * 600},
            },
        )

        full = record.full_dict()

        self.assertIn("candidate_details", full)
        self.assertIn("action_details", full)
        self.assertEqual(
            set(full),
            set(record.compact_dict()) | {"payload", "candidate_details", "action_details"},
        )
        self.assertLessEqual(len(full["payload"]["payload_text"]), 256)
        self.assertLessEqual(len(full["candidate_details"]["arguments"]["query"]), 256)
        self.assertLessEqual(len(full["action_details"]["arguments"]["body"]), 256)
        self.assertEqual(full["payload_hash"], "sha256:payload")

    def test_compact_final_state_does_not_leak_deep_sensitive_objects(self):
        final_state = {"level-0": {"level-1": {"level-2": {"level-3": {
            "level-4": {"raw_prompt": "deep-prompt-secret"},
        }}}}}
        record = self.make_record(final_state=final_state)

        compact = record.compact_dict()

        self.assertNotIn("deep-prompt-secret", repr(compact))

    def test_run_record_counts_each_status_without_coercing_results(self):
        records = [
            self.make_record(sample_status=status)
            for status in SampleStatus
        ]
        records.append(
            self.make_record(
                sample_status=SampleStatus.POLICY_ERROR,
                predicate_result=None,
                utility_result=None,
            )
        )

        compact = RunRecord(run_id="run-001", records=records).compact_dict()

        self.assertEqual(compact["sample_counts"]["policy_error"], 2)
        for status in SampleStatus:
            expected = 2 if status is SampleStatus.POLICY_ERROR else 1
            self.assertEqual(compact["sample_counts"][status.value], expected)
        self.assertIsNone(compact["records"][-1]["predicate_result"])
        self.assertIsNone(compact["records"][-1]["utility_result"])


if __name__ == "__main__":
    unittest.main()
