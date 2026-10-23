"""Offline reproduction of server source-pin and runtime diagnostics."""
from contextlib import redirect_stdout
from copy import deepcopy
from io import StringIO
import hashlib
from pathlib import Path
import unittest
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

    def test_reviewed_code_accepts_matching_server_runtime_independently_of_mapping_runtime(self):
        path = Path(reuse.__file__)
        old = {'benchmark': __import__('test_partial_agentdyn').DOJO_IDENTITY, 'python': '3.10.19', 'agentdojo': '0.1.35', 'source_sha256': {'old.py': 'known'}}
        current = {**old, 'source_sha256': {'new.py': 'current'}}
        mapping = {'schema_version': 'dscg.benchmark-reuse-compatibility.v2', 'benchmark': __import__('test_partial_agentdyn').DOJO_IDENTITY,
                   'reviewed_sources': [{**old, 'python': '3.10.21'}],
                   'current_source_paths': ['new.py'],
                   'current_harness_sha256': {'experiments/common/benchmark_reuse.py': hashlib.sha256(path.read_bytes()).hexdigest()}}
        with patch.object(reuse, '_read', return_value=mapping):
            self.assertTrue(reuse.compatible_source(old, current))
            self.assertFalse(reuse.compatible_source(old, {**current, 'python': '3.10.21'}))
            self.assertFalse(reuse.compatible_source({**old, 'source_sha256': {'unknown.py': 'unknown'}}, current))
            self.assertFalse(reuse.compatible_source(old, {**current, 'agentdojo': 'changed'}))
            mapping['current_harness_sha256']['experiments/common/benchmark_reuse.py'] = '0' * 64
            self.assertFalse(reuse.compatible_source(old, current))

    def rejected_cohort(self, recorded, current):
        frozen = {'schema_version': cohort.SCHEMA, 'benchmark': __import__('test_partial_agentdyn').DOJO_IDENTITY, 'selection_rule': cohort.RULE, 'binding': recorded}
        frozen['cohort_sha256'] = cohort._digest(frozen)
        with patch.object(cohort, '_binding', return_value=current):
            with self.assertRaises(ValueError) as error:
                cohort._validate_cohort_data(frozen, None)
        return str(error.exception)

    def binding(self):
        return {'benchmark': __import__('test_partial_agentdyn').DOJO_IDENTITY, 'catalog': {}, 'main_model': {'model_id': 'offline', 'base_url': 'private-url'},
                'source': {'benchmark': __import__('test_partial_agentdyn').DOJO_IDENTITY, 'python': '3.10.19', 'agentdojo': '0.1.35', 'source_sha256': {'old.py': 'known'}},
                'screening_script_sha256': 'old'}

    def test_cohort_error_reports_runtime_versions(self):
        old = self.binding(); current = deepcopy(old)
        current['source']['python'] = '3.10.21'
        message = self.rejected_cohort(old, current)
        self.assertIn('3.10.19', message)
        self.assertIn('3.10.21', message)

    def test_cohort_error_names_model_fields_without_exposing_values(self):
        old = self.binding(); current = deepcopy(old)
        current['main_model']['base_url'] = 'other-private-url'
        message = self.rejected_cohort(old, current)
        self.assertIn('main_model.base_url', message)
        self.assertNotIn('private-url', message)

    def test_cohort_error_identifies_modified_server_file(self):
        old = self.binding(); current = deepcopy(old)
        current['source']['source_sha256'] = {'new.py': 'current'}
        path = 'experiments/run_partial_benchmark.py'
        mapping = {'schema_version': 'dscg.injection-compatibility.v1',
                   'current_harness_sha256': {path: 'f' * 64}}
        with patch.object(cohort, '_read', return_value=mapping), patch.object(cohort, '_file_hash', return_value='a' * 64):
            message = self.rejected_cohort(old, current)
        self.assertIn(path, message)
        self.assertIn('ffffffffffff', message)
        self.assertIn('aaaaaaaaaaaa', message)

    def test_cohort_error_is_not_reported_as_missing_model_configuration(self):
        for cli in (partial.cli, full.cli):
            with self.subTest(cli=cli), patch.object(partial, 'main', side_effect=ValueError('screening source changed')):
                stream = StringIO()
                with redirect_stdout(stream):
                    self.assertEqual(cli(['--baseline']), 1)
                self.assertIn('screening source changed', stream.getvalue())
                self.assertNotIn('模型配置错误', stream.getvalue())
                self.assertNotIn('DSCG_MAIN_*', stream.getvalue())


# Explicitly retain historical upstream suites as generic offline fixtures.
def setUpModule():
    global _fixture_backend
    from test_partial_agentdyn import legacy_fixture_backend
    _fixture_backend = legacy_fixture_backend(globals())


def tearDownModule():
    _fixture_backend.close()
