"""Native caught errors must not become successful attacks or defenses."""

from artifact_support import ensure_artifacts
ensure_artifacts('test_agentdyn_outcomes')
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest


class OutcomeTests(unittest.TestCase):
    def test_error_trace_excluded_without_modifying_native_fields_or_other_samples(self):
        from experiments.common.benchmark_outcomes import project_outcomes
        root = Path(__file__).resolve().parents[1] / 'artifacts/tests/test_agentdyn_outcomes'
        root.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(dir=root) as directory:
            suite = Path(directory)
            trace = suite/'u0/attack/i0.json';trace.parent.mkdir(parents=True)
            raw = json.dumps({'messages': [], 'error': 'JSONDecodeError: fixture', 'utility': False, 'security': True})
            trace.write_text(raw)
            records = project_outcomes({('u0','i0'):False, ('u1','i0'):True},
                {('u0','i0'):True, ('u1','i0'):False}, suite, 'attack', run_attack=True)
            error, valid = records[('u0','i0')], records[('u1','i0')]
            self.assertEqual(error['sample_status'], 'infrastructure_error')
            self.assertIsNone(error['utility_success'])
            self.assertIsNone(error['attack_success'])
            self.assertIsNone(error['defense_success'])
            self.assertTrue(error['native_attack_success'])
            self.assertFalse(error['native_utility_success'])
            self.assertTrue(valid['utility_success'])
            self.assertFalse(valid['attack_success'])
            self.assertEqual(trace.read_text(), raw)

    def test_clean_error_has_no_utility_label_and_no_security_denominator(self):
        from experiments.common.benchmark_outcomes import project_outcomes
        root = Path(__file__).resolve().parents[1] / 'artifacts/tests/test_agentdyn_outcomes'
        root.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(dir=root) as directory:
            trace = Path(directory)/'u0/none/none.json';trace.parent.mkdir(parents=True)
            trace.write_text(json.dumps({'error': 'ServerError'}))
            row = project_outcomes({('u0',None):False}, {}, Path(directory), 'none', run_attack=False)[('u0',None)]
            self.assertIsNone(row['utility_success'])
            self.assertIsNone(row['attack_success'])
            self.assertTrue(row['execution_error'])
