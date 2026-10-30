"""Standalone screen regression using native execution/logging and offline pipelines."""
from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from agentdojo import logging
from dscg.model_config import ModelConfig
from dscg.benchmark_catalog import benchmark_identity, get_backend
from experiments import run_injection_precheck as precheck
from experiments.common import injection_cohort as helpers

class FakeSuite:
    name = 'workspace'
    user_tasks = dict.fromkeys(['user_task_0', 'user_task_1', 'user_task_2', 'user_task_3'])

    def __init__(self):
        self.injection_tasks = {f'injection_task_{i}': SimpleNamespace(ID=f'injection_task_{i}', GOAL=f'goal {i}')
                                for i in range(2)}
        self.outcomes = {0: [True], 1: [False, False]}
        self.executed = []

    def get_injection_task_by_id(self, name):
        return self.injection_tasks[name]

    def run_task_with_pipeline(self, pipeline, task, injection_task, injections):
        if injection_task is not None or injections:
            raise AssertionError('screening must not inject content')
        self.executed.append(task.ID)
        outcome = self.outcomes[int(task.ID.rsplit('_', 1)[1])].pop(0)
        messages = [{'role': 'user', 'content': [{'type': 'text', 'content': task.GOAL}]},
                    {'role': 'assistant', 'content': [{'type': 'text', 'content': 'offline response'}],
                     'tool_calls': None}]
        logging.Logger.get().log(messages)
        if isinstance(outcome, Exception):
            raise outcome
        if isinstance(outcome, tuple):
            logging.Logger.get().log_error(outcome[1])
            return False, True
        return outcome, True



class InjectionPrecheckTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.suite = FakeSuite()
        self.suite.name = get_backend().suites[0]
        self.config = ModelConfig('qwen3.7-flash', 'fake', 'https://example.invalid', 'dashscope', 'TEST_KEY')
        for patcher in [patch.object(precheck, 'get_suite', return_value=self.suite),
                        patch.object(helpers, 'get_suite', return_value=self.suite),
                        patch.object(precheck, 'resolve_model_config', return_value=self.config),
                        patch.object(precheck, 'make_openai_compatible_pipeline', side_effect=self.factory)]:
            patcher.start()
            self.addCleanup(patcher.stop)

    def factory(self, **kwargs):
        return SimpleNamespace(name='offline'), SimpleNamespace(snapshot=lambda: {})

    @property
    def output(self):
        return self.root / 'screens' / get_backend().id / 'qwen3.7-flash_screen'

    def screen(self, **kwargs):
        with redirect_stdout(StringIO()):
            return precheck.screen(config_path=None, run_name='screen', suites=[self.suite.name],
                                   results_dir=self.root / 'screens', **kwargs)

    def filtered(self):
        return json.loads((self.output / 'fliter.json').read_text())

    def test_native_goal_evidence_is_flat_and_resume_preserves_it(self):
        self.assertEqual(self.screen(), 0)
        goal = self.output / 'goal' / self.suite.name
        self.assertEqual(sorted(p.name for p in goal.glob('*.json')), ['injection_task_0.json', 'injection_task_1.json'])
        evidence = {p: p.read_bytes() for p in self.output.rglob('*') if p.is_file() and p.name != '.screening.lock'}
        self.assertEqual(self.filtered()['excluded'][self.suite.name], ['injection_task_1'])
        self.assertFalse((self.output / 'cohort.json').exists())
        self.assertEqual(self.screen(), 0)
        self.assertEqual(self.suite.executed, ['injection_task_0', 'injection_task_1'])
        for p, content in evidence.items():
            self.assertEqual(p.read_bytes(), content)

    def test_error_is_separate_excluded_and_never_retried(self):
        self.suite.outcomes[1] = [RuntimeError('private details'), True]
        self.assertEqual(self.screen(), 1)
        self.assertEqual(self.screen(), 1)
        self.assertEqual(self.suite.executed, ['injection_task_0', 'injection_task_1'])
        self.assertEqual(self.filtered()['excluded'][self.suite.name], ['injection_task_1'])
        status = (self.output / 'summary.json').read_text()
        self.assertEqual(json.loads(status)['counts'], {'kept': 1, 'error': 1})
        self.assertNotIn('private details', status)

    def test_interrupt_skips_started_and_runs_only_unstarted_goals(self):
        with patch.object(precheck, 'make_openai_compatible_pipeline', side_effect=KeyboardInterrupt), redirect_stdout(StringIO()):
            self.assertEqual(precheck.cli(['screen', '--name', 'screen', '--suites', self.suite.name,
                '--results-dir', str(self.root / 'screens')]), 130)
        self.assertEqual(self.screen(), 1)
        self.assertEqual(self.suite.executed, ['injection_task_1'])
        self.assertEqual(set(self.filtered()['excluded'][self.suite.name]), {'injection_task_0', 'injection_task_1'})

    def test_completed_trace_recovered_without_retry(self):
        self.assertEqual(self.screen(), 0)
        attempt = next((self.output / 'attempts' / self.suite.name / 'injection_task_0').rglob('attempt.json'))
        attempt.unlink()
        self.assertEqual(self.screen(), 0)
        self.assertEqual(json.loads(attempt.read_text())['origin'], 'recovered')
        self.assertEqual(self.suite.executed.count('injection_task_0'), 1)

    def test_historical_cohort_screen_is_read_only(self):
        self.output.mkdir(parents=True)
        cohort = self.output / 'cohort.json'
        cohort.write_text('{"historical": true}')
        original = cohort.read_bytes()
        with self.assertRaises(ValueError):
            self.screen()
        self.assertEqual(cohort.read_bytes(), original)
        self.assertFalse(self.suite.executed)

    def test_changed_goal_binding_fails_before_execution(self):
        self.assertEqual(self.screen(), 0)
        self.suite.injection_tasks['injection_task_0'].GOAL = 'changed'
        with self.assertRaises(ValueError):
            self.screen()
        self.assertEqual(len(self.suite.executed), 2)

    def test_changed_evidence_rejected_before_aggregate_writes(self):
        self.assertEqual(self.screen(), 0)
        path = self.output / 'goal' / self.suite.name / 'injection_task_1.json'
        path.write_text(path.read_text() + '\n')
        summary = (self.output / 'summary.md').read_bytes()
        with self.assertRaises(ValueError):
            self.screen()
        self.assertEqual((self.output / 'summary.md').read_bytes(), summary)
        self.assertEqual(len(self.suite.executed), 2)

    def historical(self, utility=True, error=None):
        root = self.root / 'historical'
        suite_dir = root / 'ignore_previous' / self.suite.name
        path = suite_dir / 'injection_task_0/none/none.json'
        path.parent.mkdir(parents=True)
        source = precheck.source_revision()
        (suite_dir / 'run_manifest.json').write_text(json.dumps({
            'benchmark': benchmark_identity(), 'profile': 'baseline', 'main_model': self.config.public_dict(),
            'source': source, 'task_selection': {'suite_version': 'v1.2', 'injections': list(self.suite.injection_tasks)},
        }))
        path.write_text(json.dumps({'suite_name': self.suite.name, 'user_task_id': 'injection_task_0',
            'injection_task_id': None, 'attack_type': None, 'injections': {},
            'messages': [{'role': 'user', 'content': 'goal 0'}, {'role': 'assistant', 'content': 'done'}],
            'utility': utility, 'security': True, 'error': error, 'agentdojo_package_version': source['agentdojo']}))
        return root, path

    def test_historical_failure_and_error_are_reused_once_read_only(self):
        for utility, error, exit_code in [(False, None, 0), (True, 'error', 1)]:
            with self.subTest(error=error):
                # Each case owns its run and history.
                self.root = self.root / ('error' if error else 'failure')
                self.suite.executed.clear()
                self.suite.outcomes = {0: [True], 1: [False]}
                root, path = self.historical(utility, error)
                original = path.read_bytes()
                self.assertEqual(self.screen(reuse_from=root), exit_code)
                self.assertEqual(self.suite.executed, ['injection_task_1'])
                self.assertEqual(path.read_bytes(), original)

    def flat_history(self, *, kind, utility=True, profile='baseline', model=None):
        root, old_trace = self.historical(utility)
        old_manifest = json.loads((old_trace.parents[2] / 'run_manifest.json').read_text())
        path = root / 'goal' / self.suite.name / 'injection_task_0.json'
        path.parent.mkdir(parents=True)
        path.write_bytes(old_trace.read_bytes())
        # No legacy candidate remains: the test must exercise flat reuse.
        old_trace.unlink()
        if kind in {'screen', 'oldscreen'}:
            binding = precheck._binding(self.config, [self.suite.name])
            binding.update(schema_version=precheck.SCREEN_SCHEMA)
            if model is not None:
                binding['main_model'] = model
            (root / ('screen_manifest.json' if kind == 'oldscreen' else 'run_manifest.json')).write_text(json.dumps(binding))
        else:
            from experiments.common.run_bindings import SCHEMA, LAYOUT
            manifest = {**old_manifest, 'profile': profile, 'agentdojo_defense': None,
                        'selection_options': {'goal': True}}
            if model is not None:
                manifest['main_model'] = model
            (old_trace.parents[2] / 'run_manifest.json').unlink()
            (root / 'run_manifest.json').write_text(json.dumps({'schema_version': SCHEMA,
                'task_layout': LAYOUT, 'common': manifest,
                'groups': {f'ignore_previous/{self.suite.name}': {}}, 'bindings': {}}))
        return root, path

    def test_new_flat_screen_goal_reused_without_execution_or_source_writes(self):
        root, _ = self.flat_history(kind='screen', utility=False)
        originals = {p: p.read_bytes() for p in root.rglob('*') if p.is_file()}
        self.assertEqual(self.screen(reuse_from=root), 0)
        self.assertEqual(self.suite.executed, ['injection_task_1'])
        for path, content in originals.items():
            self.assertEqual(path.read_bytes(), content)

    def test_new_screen_has_one_manifest_and_compact_goal_summary(self):
        self.assertEqual(self.screen(), 0)
        self.assertTrue((self.output / 'run_manifest.json').exists())
        self.assertFalse((self.output / 'screen_manifest.json').exists())
        self.assertFalse((self.output / 'status.json').exists())
        summary = json.loads((self.output / 'summary.json').read_text())
        self.assertNotIn('main_model', summary)
        self.assertNotIn('benchmark', summary)
        checks = summary['selection_report']['goal_checks']
        self.assertEqual([(record['injection_task_id'], record['status']) for record in checks],
                         [('injection_task_0', 'passed'), ('injection_task_1', 'failed')])
        self.assertTrue(all(record['path'] == f"goal/{self.suite.name}/{record['injection_task_id']}.json"
                            and record['cost'] is None for record in checks))

    def test_old_screen_manifest_is_read_only_reuse_source(self):
        root, _ = self.flat_history(kind='oldscreen', utility=False)
        before = {path: path.read_bytes() for path in root.rglob('*') if path.is_file()}
        self.assertEqual(self.screen(reuse_from=root), 0)
        self.assertEqual(self.suite.executed, ['injection_task_1'])
        for path, content in before.items():
            self.assertEqual(path.read_bytes(), content)
        self.assertFalse((root / 'run_manifest.json').exists())

    def test_old_screen_directory_cannot_be_resumed_or_migrated(self):
        self.assertEqual(self.screen(), 0)
        (self.output / 'run_manifest.json').rename(self.output / 'screen_manifest.json')
        (self.output / 'summary.json').rename(self.output / 'status.json')
        before = {path: path.read_bytes() for path in self.output.rglob('*') if path.is_file()}
        with self.assertRaises(ValueError):
            self.screen()
        for path, content in before.items():
            self.assertEqual(path.read_bytes(), content)
        self.assertFalse((self.output / 'run_manifest.json').exists())
        self.assertFalse((self.output / 'summary.json').exists())

    def test_new_flat_baseline_measurement_goal_reused(self):
        root, _ = self.flat_history(kind='measurement')
        self.assertEqual(self.screen(reuse_from=root), 0)
        self.assertEqual(self.suite.executed, ['injection_task_1'])

    def test_new_flat_defended_measurement_goal_is_not_baseline_evidence(self):
        root, _ = self.flat_history(kind='measurement', profile='full')
        self.assertEqual(self.screen(reuse_from=root), 0)
        self.assertEqual(self.suite.executed, ['injection_task_0', 'injection_task_1'])

    def test_new_flat_model_mismatch_is_not_reused(self):
        root, _ = self.flat_history(kind='screen', model={'model_id': 'different'})
        self.assertEqual(self.screen(reuse_from=root), 0)
        self.assertEqual(self.suite.executed, ['injection_task_0', 'injection_task_1'])

    def test_new_flat_measurement_error_status_is_not_rescored_success(self):
        root, _ = self.flat_history(kind='measurement', utility=True)
        (root / 'summary.json').write_text(json.dumps({'selection_report': {'goal_checks': [
            {'suite': self.suite.name, 'injection_task_id': 'injection_task_0', 'status': 'error',
             'path': f'goal/{self.suite.name}/injection_task_0.json'}]}}))
        self.assertEqual(self.screen(reuse_from=root), 1)
        self.assertEqual(self.suite.executed, ['injection_task_1'])
        self.assertIn('injection_task_0', self.filtered()['excluded'][self.suite.name])

    def test_new_flat_running_measurement_is_skipped_as_interrupted(self):
        root, _ = self.flat_history(kind='measurement', utility=True)
        (root / 'summary.json').write_text(json.dumps({'selection_report': {'goal_checks': [
            {'suite': self.suite.name, 'injection_task_id': 'injection_task_0', 'status': 'running',
             'path': f'goal/{self.suite.name}/injection_task_0.json'}]}}))
        self.assertEqual(self.screen(reuse_from=root), 1)
        self.assertEqual(self.suite.executed, ['injection_task_1'])

    def test_recorded_api_failure_is_error_even_when_native_utility_succeeds(self):
        phases = {'generation': {'api_calls': 2, 'failed_calls': 1, 'missing_usage_calls': 0,
                                 'total_tokens': 25}}
        tracker = SimpleNamespace(snapshot=lambda: phases)
        with patch.object(precheck, 'make_openai_compatible_pipeline',
                          return_value=(SimpleNamespace(name='offline'), tracker)):
            self.assertEqual(self.screen(), 1)
        record_path = next((self.output / 'attempts' / self.suite.name / 'injection_task_0').rglob('attempt.json'))
        record = json.loads(record_path.read_text())
        self.assertEqual(record['status'], 'error')
        self.assertIsNone(record['native_utility'])
        self.assertIsNone(record['total_tokens'])
        self.assertEqual(record['error_code'], 'RECORDED_API_FAILURE')
        checks = json.loads((self.output / 'summary.json').read_text())['selection_report']['goal_checks']
        self.assertEqual(checks[0]['status'], 'error')
        self.assertEqual(checks[0]['cost'], {'models': [phases]})
        self.assertIn('injection_task_0', self.filtered()['excluded'][self.suite.name])
        self.assertEqual(json.loads((self.output / 'summary.json').read_text())['counts'], {'error': 2})
        # Retain the backend's original grade in its immutable evidence.
        trace = json.loads((self.output / 'goal' / self.suite.name / 'injection_task_0.json').read_text())
        self.assertIs(trace['utility'], True)

    def test_reused_screen_preserves_recorded_api_failure_without_reexecution(self):
        tracker = SimpleNamespace(snapshot=lambda: {'generation': {'api_calls': 2,
                                  'failed_calls': 1, 'missing_usage_calls': 0, 'total_tokens': 25}})
        with patch.object(precheck, 'make_openai_compatible_pipeline',
                          return_value=(SimpleNamespace(name='offline'), tracker)):
            self.assertEqual(self.screen(), 1)
        source = self.output
        before = {p: p.read_bytes() for p in source.rglob('*') if p.is_file()}
        self.suite.executed.clear()
        with redirect_stdout(StringIO()):
            self.assertEqual(precheck.screen(config_path=None, run_name='reused', suites=[self.suite.name],
                             results_dir=self.root / 'screens', reuse_from=source), 1)
        self.assertEqual(self.suite.executed, [])
        target = source.with_name('qwen3.7-flash_reused')
        self.assertEqual(json.loads((target / 'summary.json').read_text())['counts'], {'error': 2})
        for path, content in before.items():
            self.assertEqual(path.read_bytes(), content)

    def test_native_logged_error_is_not_valid_failure(self):
        self.suite.outcomes[1] = [('error', 'offline infrastructure error')]
        self.assertEqual(self.screen(), 1)
        self.assertEqual(json.loads((self.output / 'summary.json').read_text())['counts'], {'kept': 1, 'error': 1})


if __name__ == '__main__':
    unittest.main()
