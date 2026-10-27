"""Offline reproduction of server source-pin and runtime diagnostics."""
from contextlib import redirect_stdout
from copy import deepcopy
from io import StringIO
import hashlib
from pathlib import Path
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from experiments import run_benchmark as full, run_partial_benchmark as partial
from experiments.common import benchmark_reuse as reuse, injection_cohort as cohort


class ResumeDiagnosticsTests(unittest.TestCase):
    def test_automatic_router_default_and_explicit_original_mode(self):
        for cli in (partial.cli, full.cli):
            for flags, expected in (([], 'shadow'), (['--baseline'], 'off'),
                                    (['--no-checker'], 'off'), (['--audit-router-mode', 'off'], 'off')):
                with self.subTest(cli=cli, flags=flags), patch.object(partial, 'main', return_value=0) as run:
                    self.assertEqual(cli(flags), 0)
                    self.assertEqual(run.call_args.kwargs['audit_router_mode'], expected)

    def test_source_and_python_changes_do_not_read_compatibility_mapping(self):
        identity = __import__('test_partial_agentdyn').DOJO_IDENTITY
        old = {'benchmark': identity, 'python': '3.10.19', 'agentdojo': '0.1.35', 'source_sha256': {'old.py': 'known'}}
        current = {**old, 'python': '3.10.21', 'source_sha256': {'new.py': 'unknown'}}
        with patch.object(reuse, '_read', side_effect=AssertionError('compatibility map read')):
            self.assertTrue(reuse.compatible_source(old, current))
            self.assertFalse(reuse.compatible_source(old, {**current, 'agentdojo': 'changed'}))

    def rejected_cohort(self, recorded, current):
        frozen = {'schema_version': cohort.SCHEMA, 'benchmark': __import__('test_partial_agentdyn').DOJO_IDENTITY,
                  'suite_version': 'v1.2', 'selection_rule': cohort.RULE, 'binding': recorded,
                  'suites': {'workspace': {'user_task_ids': ['user_task_0'], 'injection_task_ids': ['injection_task_0']}}}
        frozen['cohort_sha256'] = cohort._digest(frozen)
        config = SimpleNamespace(public_dict=lambda: current['main_model'])
        with patch.object(cohort, 'get_suite', return_value=SimpleNamespace(
                user_tasks={'user_task_0': None}, injection_tasks={'injection_task_0': None})):
            with self.assertRaises(ValueError) as error:
                cohort._validate_cohort_data(frozen, config)
        return str(error.exception)

    def binding(self):
        return {'benchmark': __import__('test_partial_agentdyn').DOJO_IDENTITY, 'catalog': {}, 'main_model': {'model_id': 'offline', 'provider': 'openai', 'base_url': 'private-url'},
                'source': {'benchmark': __import__('test_partial_agentdyn').DOJO_IDENTITY, 'python': '3.10.19', 'agentdojo': '0.1.35', 'source_sha256': {'old.py': 'known'}},
                'screening_script_sha256': 'old'}

    def test_python_patch_differences_do_not_change_screen_configuration(self):
        old = self.binding(); current = deepcopy(old)
        current['source']['python'] = '3.10.21'
        self.assertTrue(cohort._bindings_compatible(old, current))

    def test_cohort_error_names_model_fields_without_exposing_values(self):
        old = self.binding(); current = deepcopy(old)
        current['main_model']['model_id'] = 'other-private-model'
        message = self.rejected_cohort(old, current)
        self.assertIn('main_model.model_id', message)
        self.assertNotIn('private-url', message)
        self.assertNotIn('other-private-model', message)

    def test_source_hash_changes_do_not_change_screen_configuration(self):
        old = self.binding(); current = deepcopy(old)
        current['source']['source_sha256'] = {'new.py': 'current'}
        with patch.object(cohort, '_file_hash', side_effect=AssertionError('source hash read')):
            self.assertTrue(cohort._bindings_compatible(old, current))

    def test_cohort_error_is_not_reported_as_missing_model_configuration(self):
        for cli in (partial.cli, full.cli):
            with self.subTest(cli=cli), patch.object(partial, 'main', side_effect=ValueError('screening source changed')):
                stream = StringIO()
                with redirect_stdout(stream):
                    self.assertEqual(cli(['--baseline']), 1)
                self.assertIn('screening source changed', stream.getvalue())
                self.assertNotIn('模型配置错误', stream.getvalue())
                self.assertNotIn('BASEINTENT_MAIN_*', stream.getvalue())


# Explicitly retain historical upstream suites as generic offline fixtures.
def setUpModule():
    global _fixture_backend
    from test_partial_agentdyn import legacy_fixture_backend
    _fixture_backend = legacy_fixture_backend(globals())


def tearDownModule():
    _fixture_backend.close()
