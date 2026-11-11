"""Offline screening contracts: native logging/scoring, no remote model calls."""
from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from agentdojo import logging
from dscg.model_config import ModelConfig

try:
    from experiments import run_injection_precheck as precheck
except ImportError:
    precheck = None


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
        self.assertIsNotNone(precheck, 'standalone injection precheck entrypoint is missing')
        artifacts = Path(__file__).resolve().parents[1] / 'workshop/artifacts/20261016_injection_precheck/test_runs'
        artifacts.mkdir(parents=True, exist_ok=True)
        self.temp = TemporaryDirectory(dir=artifacts)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.suite = FakeSuite()
        self.config = ModelConfig('offline', 'not-a-real-key', 'https://example.invalid', 'openai', 'TEST_KEY')
        self.patchers = [patch.object(precheck, 'get_suite', return_value=self.suite),
                         patch.object(precheck, 'resolve_model_config', return_value=self.config),
                         patch.object(precheck, 'make_openai_compatible_pipeline', side_effect=self.factory)]
        for p in self.patchers:
            p.start()
            self.addCleanup(p.stop)

    def factory(self, **kwargs):
        return SimpleNamespace(name='offline', dscg_model_config=self.config.public_dict()), SimpleNamespace(snapshot=lambda: {})

    @property
    def output(self):
        return self.root / 'screens' / 'offline_screen'

    def screen(self, **kwargs):
        with redirect_stdout(StringIO()):
            return precheck.screen(config_path=None, run_name='screen', suites=['workspace'],
                                   results_dir=self.root / 'screens', **kwargs)

    def cohort(self):
        return json.loads((self.output / 'cohort.json').read_text())

    def test_native_precheck_runs_goals_only_and_freezes_all_user_ids(self):
        self.assertEqual(self.screen(), 0)
        cohort = self.cohort()
        self.assertEqual(self.suite.executed, ['injection_task_0', 'injection_task_1', 'injection_task_1'])
        self.assertEqual(cohort['suites']['workspace']['user_task_ids'],
                         ['user_task_0', 'user_task_1', 'user_task_2', 'user_task_3'])
        self.assertEqual(cohort['suites']['workspace']['injection_task_ids'], ['injection_task_0'])
        self.assertEqual(cohort['decisions']['workspace']['injection_task_1']['status'], 'excluded')
        self.assertEqual(len(list(self.output.rglob('none.json'))), 3)

    def test_second_attempt_success_keeps_target_and_resume_does_no_work(self):
        self.suite.outcomes[1] = [False, True]
        self.assertEqual(self.screen(), 0)
        original = (self.output / 'cohort.json').read_bytes()
        self.assertEqual(self.cohort()['suites']['workspace']['injection_task_ids'], ['injection_task_0', 'injection_task_1'])
        self.assertEqual(self.screen(), 0)
        self.assertEqual((self.output / 'cohort.json').read_bytes(), original)
        self.assertEqual(len(self.suite.executed), 3)

    def test_api_error_is_unresolved_and_resume_preserves_old_attempt(self):
        self.suite.outcomes[1] = [RuntimeError('provider private detail'), False, False]
        self.assertEqual(self.screen(), 1)
        self.assertFalse((self.output / 'cohort.json').exists())
        paths = list(self.output.rglob('attempt.json'))
        originals = {p: p.read_bytes() for p in paths}
        self.assertEqual(self.screen(), 0)
        self.assertEqual(self.cohort()['decisions']['workspace']['injection_task_1']['status'], 'excluded')
        for p, original in originals.items():
            self.assertEqual(p.read_bytes(), original)
        self.assertNotIn('provider private detail', (self.output / 'status.json').read_text())

    def test_changed_binding_fails_before_more_task_execution(self):
        self.assertEqual(self.screen(), 0)
        self.suite.injection_tasks['injection_task_0'].GOAL = 'changed goal'
        with self.assertRaises(ValueError):
            self.screen()
        self.assertEqual(len(self.suite.executed), 3)

    def historical(self, *, utility=True, goal='goal 0', model=None, error=None):
        root = self.root / 'historical'
        suite_dir = root / 'ignore_previous' / 'workspace'
        path = suite_dir / 'injection_task_0' / 'none' / 'none.json'
        path.parent.mkdir(parents=True, exist_ok=True)
        source = precheck.source_revision()
        (suite_dir / 'run_manifest.json').write_text(json.dumps({
            'profile': 'baseline', 'main_model': model or self.config.public_dict(),
            'source': source, 'task_selection': {'suite_version': 'v1.2',
                'injections': ['injection_task_0', 'injection_task_1'], 'users': list(self.suite.user_tasks)},
        }))
        path.write_text(json.dumps({'suite_name': 'workspace', 'user_task_id': 'injection_task_0',
            'injection_task_id': None, 'attack_type': None, 'injections': {}, 'pipeline_name': 'ignore_previous',
            'messages': [{'role': 'user', 'content': [{'type': 'text', 'content': goal}]},
                         {'role': 'assistant', 'content': [{'type': 'text', 'content': 'done'}], 'tool_calls': None}],
            'utility': utility, 'security': True, 'error': error,
            'agentdojo_package_version': source['agentdojo'], 'duration': 1.0}))
        return root, path

    def test_compatible_historical_success_is_reused_without_execution_or_modification(self):
        root, trace = self.historical()
        original = trace.read_bytes()
        self.assertEqual(self.screen(reuse_from=root), 0)
        self.assertEqual(self.suite.executed, ['injection_task_1', 'injection_task_1'])
        self.assertEqual(trace.read_bytes(), original)
        self.assertEqual(self.cohort()['decisions']['workspace']['injection_task_0']['attempts'][0]['origin'], 'reused')

    def test_historical_failure_counts_as_first_failure(self):
        root, _ = self.historical(utility=False)
        self.suite.outcomes[0] = [False]
        self.assertEqual(self.screen(reuse_from=root), 0)
        self.assertEqual(self.suite.executed.count('injection_task_0'), 1)
        self.assertEqual(self.cohort()['decisions']['workspace']['injection_task_0']['status'], 'excluded')

    def test_later_compatible_historical_success_overrides_earlier_failure(self):
        root, trace = self.historical(utility=False)
        later = root / 'tool_knowledge/workspace/injection_task_0/none/none.json'
        later.parent.mkdir(parents=True)
        value = json.loads(trace.read_text()); value['utility'] = True
        later.write_text(json.dumps(value))
        manifest = root / 'tool_knowledge/workspace/run_manifest.json'
        manifest.write_bytes((root / 'ignore_previous/workspace/run_manifest.json').read_bytes())
        self.assertEqual(self.screen(reuse_from=root), 0)
        self.assertNotIn('injection_task_0', self.suite.executed)
        self.assertEqual(self.cohort()['decisions']['workspace']['injection_task_0']['status'], 'kept')

    def test_empty_suite_is_explicitly_skipped_and_all_empty_is_rejected(self):
        self.suite.outcomes = {0: [False, False], 1: [False, False]}
        self.screen()
        with patch.object(precheck.shared, 'main') as runner, self.assertRaises(ValueError):
            precheck.run_screened(self.output / 'cohort.json', config_path=None, run_name='empty')
        runner.assert_not_called()

    def test_changed_evidence_prevents_using_frozen_cohort(self):
        self.screen()
        trace = next(self.output.rglob('none.json'))
        value = json.loads(trace.read_text()); value['utility'] = not value['utility']
        trace.write_text(json.dumps(value))
        with self.assertRaises(ValueError):
            precheck.run_screened(self.output / 'cohort.json', config_path=None, run_name='changed')

    def test_completed_native_trace_is_recovered_after_interrupted_attempt_bookkeeping(self):
        self.suite.outcomes[1] = [RuntimeError('offline interruption'), False, False]
        self.assertEqual(self.screen(), 1)
        attempt = next((self.output / 'attempts/workspace/injection_task_0').rglob('attempt.json'))
        attempt.unlink()  # Simulate interruption after TraceLogger completed, before wrapper bookkeeping.
        self.assertEqual(self.screen(), 0)
        self.assertEqual(self.suite.executed.count('injection_task_0'), 1)

    def test_cli_preserves_shadow_full_and_rejects_unknown_attacks_without_models(self):
        self.screen()
        with patch.object(precheck.shared, 'main', return_value=0) as runner, redirect_stdout(StringIO()):
            self.assertEqual(precheck.cli(['benchmark', '--cohort', str(self.output / 'cohort.json'),
                '--name', 'shadow', '--results-dir', str(self.root / 'benchmarks'),
                '--audit-router-mode', 'shadow', '--trace-level', 'full']), 0)
            options = runner.call_args.kwargs
            self.assertEqual(options['audit_router_mode'], 'shadow')
            self.assertEqual(options['trace_level'], 'full')
            self.assertFalse(options['origin'])
            runner.reset_mock()
            self.assertEqual(precheck.cli(['benchmark', '--cohort', str(self.output / 'cohort.json'),
                '--name', 'bad', '--attack', 'not-an-attack']), 1)
            runner.assert_not_called()

    def test_native_logged_context_error_is_not_a_valid_failure(self):
        self.suite.outcomes[1] = [('error', 'offline context_length_exceeded'), False, False]
        self.assertEqual(self.screen(), 1)
        status = json.loads((self.output / 'status.json').read_text())
        self.assertEqual(status['decisions']['workspace']['injection_task_1']['attempts'][0]['status'], 'error')
        self.assertEqual(self.screen(), 0)
        self.assertEqual(len(self.cohort()['decisions']['workspace']['injection_task_1']['attempts']), 3)

    def test_empty_scene_is_skipped_while_nonempty_scene_keeps_all_users(self):
        empty = FakeSuite(); empty.name = 'travel'; empty.outcomes = {0: [False, False], 1: [False, False]}
        with patch.object(precheck, 'get_suite', side_effect=lambda version, name: self.suite if name == 'workspace' else empty), redirect_stdout(StringIO()):
            self.assertEqual(precheck.screen(config_path=None, run_name='screen', suites=['workspace', 'travel'],
                results_dir=self.root / 'screens'), 0)
            with patch.object(precheck.shared, 'main', return_value=0) as runner:
                self.assertEqual(precheck.run_screened(self.output / 'cohort.json', config_path=None,
                    run_name='mixed', origin=True, results_dir=self.root / 'benchmarks'), 0)
                self.assertEqual(runner.call_args.kwargs['suites'], ['workspace'])
        attachment = json.loads((self.root / 'benchmarks/offline_mixed/screened_cohort.json').read_text())
        self.assertEqual(attachment['skipped_suites'], ['travel'])
        self.assertEqual(attachment['counts']['travel']['planned_per_targeted_attack'], 0)

    def test_incompatible_goal_model_source_or_corrupt_trace_is_not_reused(self):
        for mismatch in ('goal', 'model', 'source', 'corrupt'):
            with self.subTest(mismatch=mismatch):
                self.suite.executed.clear()
                self.suite.outcomes = {0: [True], 1: [False, False]}
                root, trace = self.historical(goal='different' if mismatch == 'goal' else 'goal 0',
                                              model={'model_id': 'other'} if mismatch == 'model' else None)
                if mismatch == 'source':
                    path = root / 'ignore_previous/workspace/run_manifest.json'
                    value = json.loads(path.read_text()); value['source']['source_sha256'] = {}
                    path.write_text(json.dumps(value))
                if mismatch == 'corrupt':
                    trace.write_text('{')
                with redirect_stdout(StringIO()):
                    self.assertEqual(precheck.screen(config_path=None, run_name=mismatch, suites=['workspace'],
                        results_dir=self.root / 'screens', reuse_from=root), 0)
                self.assertIn('injection_task_0', self.suite.executed)

    def test_screened_benchmark_preserves_all_users_and_selected_target_denominator(self):
        self.screen()
        from tests.test_full_benchmark import fake_attack, fake_results
        def fake_pipeline(*args, **kwargs):
            return SimpleNamespace(name='offline', dscg_model_config=self.config.public_dict()), SimpleNamespace(
                total_prompt_tokens=0, total_completion_tokens=0, get_total_tokens=lambda: 0)
        with patch.object(precheck.shared, 'make_openai_compatible_pipeline', side_effect=fake_pipeline), patch.object(
            precheck.shared.attacks, 'load_attack', side_effect=fake_attack), patch.object(
            precheck.shared.benchmark, 'benchmark_suite_with_injections', side_effect=fake_results), redirect_stdout(StringIO()):
            self.assertEqual(precheck.run_screened(self.output / 'cohort.json', config_path=None, run_name='selected',
                results_dir=self.root / 'benchmarks', origin=True, attack=['ignore_previous']), 0)
        base = self.root / 'benchmarks/offline_selected'
        summary = json.loads((base / 'ignore_previous/workspace/summary.json').read_text())
        self.assertEqual(summary['task_counts']['planned_tasks'], 4)
        self.assertEqual(summary['task_selection']['injection_task_ids'], ['injection_task_0'])
        self.assertEqual(len(summary['task_selection']['user_task_ids']), 4)
        self.assertNotEqual(summary['task_scope'], 'full')
        self.assertTrue((base / 'screened_cohort.json').exists())
        preflights = json.loads((base / 'preflight_report.json').read_text())
        self.assertEqual(preflights['planned_preflight_samples'], 1)
        self.assertEqual(preflights['counts'], {'missing': 1})
        self.assertIsNone(preflights['preflight_total_tokens'])

    def test_cohort_tampering_dos_and_all_empty_are_rejected_before_runner(self):
        self.screen()
        cohort_path = self.output / 'cohort.json'
        with patch.object(precheck.shared, 'main') as runner:
            for attack in (['dos'], ['all']):
                with self.subTest(attack=attack), self.assertRaises(ValueError):
                    precheck.run_screened(cohort_path, config_path=None, run_name='bad', attack=attack)
            cohort = self.cohort(); cohort['suites']['workspace']['injection_task_ids'] = ['injection_task_1']
            cohort_path.write_text(json.dumps(cohort))
            with self.assertRaises(ValueError):
                precheck.run_screened(cohort_path, config_path=None, run_name='bad')
            runner.assert_not_called()


if __name__ == '__main__':
    unittest.main()
