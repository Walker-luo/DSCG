"""Retired cohort entry points reject safely; historical list readers stay read-only."""
from contextlib import ExitStack, redirect_stderr, redirect_stdout
from copy import deepcopy
from io import StringIO
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from dscg.benchmark_catalog import benchmark_identity, get_backend
from dscg.model_config import ModelConfig
from experiments import run_benchmark as full
from experiments import run_partial_benchmark as partial
from experiments import run_injection_precheck as precheck
from experiments.common import injection_cohort as cohort


class PartialCohortTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.path = self.root / 'history' / 'cohort.json'
        self.path.parent.mkdir()
        self.suite_name = get_backend().suites[0]
        self.identity = benchmark_identity()
        self.config = ModelConfig('qwen3.7-flash', 'offline', 'https://example.invalid', 'dashscope', 'TEST_KEY')
        self.suite = SimpleNamespace(user_tasks={'user_task_0': object(), 'user_task_1': object()},
                                     injection_tasks={'injection_task_0': object(), 'injection_task_1': object()})
        self.value = {'schema_version': cohort.SCHEMA, 'benchmark': self.identity,
            'suite_version': 'v1.2', 'selection_rule': cohort.RULE,
            'binding': {'benchmark': self.identity, 'main_model': self.config.public_dict(),
                        'suite_version': 'v1.2', 'rule': cohort.RULE, 'catalog': {}},
            'suites': {self.suite_name: {'user_task_ids': list(self.suite.user_tasks),
                                       'injection_task_ids': ['injection_task_0']}},
            'decisions': {self.suite_name: {'injection_task_0': {'attempts': [
                {'trace_path': str(self.path.parent / 'unavailable_native_trace.json')}]}}}}
        self.save()
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(redirect_stdout(StringIO()))
        self.stack.enter_context(redirect_stderr(StringIO()))
        self.resolver = self.stack.enter_context(patch.object(partial, 'resolve_model_config'))
        self.factory = self.stack.enter_context(patch.object(partial, '_describe_pipeline'))
        self.scorer = self.stack.enter_context(patch.object(partial, '_run_single_attack'))

    def save(self):
        self.value['cohort_sha256'] = cohort._digest({key: value for key, value in self.value.items()
                                                    if key != 'cohort_sha256'})
        self.path.write_text(json.dumps(self.value))

    def snapshot(self):
        return {path.relative_to(self.root): path.read_bytes()
                for path in self.root.rglob('*') if path.is_file()}

    def assert_no_execution(self):
        self.resolver.assert_not_called()
        self.factory.assert_not_called()
        self.scorer.assert_not_called()
        self.assertFalse((self.root / 'runs').exists())

    def test_old_cli_flags_rejected_by_full_and_partial_without_writes_or_calls(self):
        before = self.snapshot()
        for entry in (partial.cli, full.cli):
            for flag in ('--cohort', '--screened', '--screen-reuse'):
                with self.subTest(entry=entry.__module__, flag=flag), self.assertRaises(SystemExit) as error:
                    entry([flag, str(self.path), '--name', 'retired', '--results-dir', str(self.root / 'runs')])
                self.assertEqual(error.exception.code, 2)
        self.assert_no_execution()
        self.assertEqual(self.snapshot(), before)

    def test_old_cohort_json_is_not_a_fliter_for_full_or_partial(self):
        before = self.snapshot()
        for entry in (partial.main, full.main):
            with self.subTest(entry=entry.__module__), self.assertRaisesRegex(ValueError, 'dscg.fliter.v1'):
                entry(fliter_path=self.path, origin=True, suites=[self.suite_name],
                      run_name='retired', results_dir=self.root / 'runs')
        self.assert_no_execution()
        self.assertEqual(self.snapshot(), before)

    def test_old_cohort_python_keyword_is_rejected_without_dispatch(self):
        before = self.snapshot()
        for entry in (partial.main, full.main):
            with self.subTest(entry=entry.__module__), self.assertRaises(TypeError):
                entry(cohort_path=self.path, origin=True, suites=[self.suite_name],
                      run_name='retired', results_dir=self.root / 'runs')
        self.assert_no_execution()
        self.assertEqual(self.snapshot(), before)

    def test_old_cohort_cannot_bypass_rejection_via_task_manifest(self):
        before = self.snapshot()
        for entry in (partial.main, full.main):
            with self.subTest(entry=entry.__module__), self.assertRaisesRegex(ValueError, 'read-only'):
                entry(task_manifest_path=self.path, origin=True, suites=[self.suite_name],
                      run_name='retired', results_dir=self.root / 'runs')
        self.assert_no_execution()
        self.assertEqual(self.snapshot(), before)

    def test_retired_screened_task_scope_is_rejected_without_dispatch(self):
        before = self.snapshot()
        for scope in ('screened', 'partial_screened'):
            with self.subTest(scope=scope), self.assertRaises(ValueError):
                partial.main(task_scope=scope, origin=True, suites=[self.suite_name],
                             run_name='retired', results_dir=self.root / 'runs')
        self.assert_no_execution()
        self.assertEqual(self.snapshot(), before)

    def test_old_screen_benchmark_alias_rejected_without_dispatch(self):
        before = self.snapshot()
        with self.assertRaises(SystemExit) as error:
            precheck.cli(['benchmark', '--cohort', str(self.path), '--name', 'retired'])
        self.assertEqual(error.exception.code, 2)
        self.assert_no_execution()
        self.assertEqual(self.snapshot(), before)

    def test_historical_reader_reads_list_once_without_native_evidence(self):
        before = self.snapshot()
        reads = []
        original_read = Path.read_text
        def read(path, *args, **kwargs):
            if path.is_relative_to(self.path.parent):
                reads.append(path)
            return original_read(path, *args, **kwargs)
        with patch.object(cohort, 'get_suite', return_value=self.suite), \
             patch.object(Path, 'read_text', read), \
             patch.object(cohort, '_file_hash', side_effect=AssertionError('reopened evidence')), \
             patch.object(cohort, '_trace_status', side_effect=AssertionError('regraded evidence')), \
             patch.object(cohort, '_binding', side_effect=AssertionError('rebuilt GOAL catalogue')):
            actual = cohort._validate_cohort(self.path, self.config, suites=[self.suite_name])
        self.assertEqual(actual, self.value)
        self.assertEqual(reads, [self.path])
        self.assertEqual(self.snapshot(), before)
        self.assert_no_execution()

    def test_historical_reader_still_rejects_digest_tampering(self):
        changed = deepcopy(self.value)
        changed['suites'][self.suite_name]['injection_task_ids'] = ['injection_task_1']
        self.path.write_text(json.dumps(changed))
        before = self.snapshot()
        with patch.object(cohort, 'get_suite', return_value=self.suite), self.assertRaises(ValueError):
            cohort._validate_cohort(self.path, self.config)
        self.assertEqual(self.snapshot(), before)
        self.assert_no_execution()

    def test_historical_source_hashes_remain_informational(self):
        current = self.value['binding']
        for hashes in ({'old.py': '0' * 64}, {'dscg/pipelines/baseline.py': '1' * 64}):
            recorded = deepcopy(current)
            recorded['source'] = {'source_sha256': hashes}
            self.assertTrue(cohort._bindings_compatible(recorded, current))
        self.assert_no_execution()


if __name__ == '__main__':
    unittest.main()
