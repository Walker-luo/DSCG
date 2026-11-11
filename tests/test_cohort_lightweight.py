"""Frozen-list validation never opens the original screening evidence."""
from copy import deepcopy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from dscg.model_config import ModelConfig
from experiments.common import injection_cohort as cohort
from test_injection_precheck import FakeSuite
from test_partial_agentdyn import TemporaryDirectory, DOJO_IDENTITY, profile


class CohortLightweightTests(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).resolve().parents[1] / 'workshop/artifacts/20261021_cohort_lightweight/tests'
        root.mkdir(parents=True, exist_ok=True)
        temp = TemporaryDirectory(dir=root); self.addCleanup(temp.cleanup)
        self.path = Path(temp.name) / 'cohort.json'
        self.config = ModelConfig('qwen3.7-flash', 'offline', 'https://example.invalid', 'dashscope', 'TEST_KEY')
        self.suite = FakeSuite()
        for item in [patch.object(cohort, 'benchmark_identity', return_value=DOJO_IDENTITY),
                     patch.object(cohort, 'get_backend', return_value=profile(DOJO_IDENTITY)),
                     patch.object(cohort, 'get_suite', return_value=self.suite)]:
            item.start(); self.addCleanup(item.stop)
        self.value = {'schema_version': cohort.SCHEMA, 'benchmark': deepcopy(DOJO_IDENTITY),
            'suite_version': 'v1.2', 'selection_rule': cohort.RULE,
            'binding': {'benchmark': deepcopy(DOJO_IDENTITY), 'main_model': self.config.public_dict(),
                        'source': {'agentdojo': '0.1.35'}, 'catalog': {}},
            'suites': {'workspace': {'user_task_ids': list(self.suite.user_tasks),
                                     'injection_task_ids': list(self.suite.injection_tasks)}},
            'decisions': {'workspace': {'unresolved': {'attempts': [{'trace_path': '/unavailable/trace.json'}]}}}}
        self.save()

    def save(self):
        self.value['cohort_sha256'] = cohort._digest({k: v for k, v in self.value.items() if k != 'cohort_sha256'})
        self.path.write_text(json.dumps(self.value))

    def test_reads_only_frozen_list_and_ignores_original_goals_decisions_and_evidence(self):
        original = self.path.read_bytes()
        with patch.object(cohort, '_file_hash', side_effect=AssertionError('evidence hash')), \
             patch.object(cohort, '_trace_status', side_effect=AssertionError('native scoring')), \
             patch.object(cohort, '_decision', side_effect=AssertionError('decision reconstruction')), \
             patch.object(cohort, '_binding', side_effect=AssertionError('GOAL catalogue')):
            self.assertEqual(cohort._validate_cohort(self.path, self.config), self.value)
        self.assertEqual(self.path.read_bytes(), original)

    def test_transport_request_settings_are_not_capability_identity(self):
        for field, value in [('chat_request_adapter', 'different-or-missing'),
                             ('base_url', 'https://different.invalid'), ('api_key_env', 'OLD_KEY'),
                             ('reasoning_effort', 'high')]:
            with self.subTest(field=field):
                self.value['binding']['main_model'][field] = value; self.save()
                self.assertEqual(cohort._validate_cohort(self.path, self.config), self.value)

    def test_model_id_and_provider_must_match_without_printing_values(self):
        for field in ['model_id', 'provider']:
            with self.subTest(field=field):
                original = self.value['binding']['main_model'][field]
                self.value['binding']['main_model'][field] = 'private-different-value'; self.save()
                with self.assertRaisesRegex(ValueError, field) as error:
                    cohort._validate_cohort(self.path, self.config)
                self.assertNotIn('private-different-value', str(error.exception))
                self.value['binding']['main_model'][field] = original

    def test_backend_version_revision_and_protocol_mismatches_reject(self):
        original = deepcopy(self.value)
        for field in ['id', 'package_version', 'revision', 'suite_version']:
            with self.subTest(field=field):
                self.value = deepcopy(original); self.value['benchmark'][field] = 'different'; self.save()
                with self.assertRaises(ValueError): cohort._validate_cohort(self.path, self.config)

    def test_only_requested_suites_are_loaded(self):
        self.value['suites']['travel'] = {'user_task_ids': ['invalid'], 'injection_task_ids': ['invalid']}
        self.save()
        def lookup(version, name):
            self.assertEqual(name, 'workspace')
            return self.suite
        with patch.object(cohort, 'get_suite', side_effect=lookup) as suite:
            cohort._validate_cohort(self.path, self.config, suites=['workspace'])
            self.assertEqual(suite.call_count, 1)
        with self.assertRaises(ValueError): cohort._validate_cohort(self.path, self.config, suites=['banking'])

    def test_file_digest_schema_and_selected_ids_are_checked(self):
        original = deepcopy(self.value)
        self.value['schema_version'] = 'unknown'; self.save()
        with self.assertRaises(ValueError): cohort._validate_cohort(self.path, self.config)
        self.value = deepcopy(original); self.value['suites']['workspace']['injection_task_ids'] = []
        self.path.write_text(json.dumps(self.value))
        with self.assertRaises(ValueError): cohort._validate_cohort(self.path, self.config)
        for key, ids in [('user_task_ids', ['user_task_0']),
                         ('injection_task_ids', ['injection_task_0', 'injection_task_0']),
                         ('injection_task_ids', ['injection_task_1', 'injection_task_0']),
                         ('injection_task_ids', ['missing'])]:
            with self.subTest(key=key, ids=ids):
                self.value = deepcopy(original); self.value['suites']['workspace'][key] = ids; self.save()
                with self.assertRaises(ValueError): cohort._validate_cohort(self.path, self.config)
        self.value = deepcopy(original); self.value['suites']['workspace']['injection_task_ids'] = []; self.save()
        cohort._validate_cohort(self.path, self.config)


if __name__ == '__main__': unittest.main()
