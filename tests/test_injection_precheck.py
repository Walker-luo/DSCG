"""Offline screening contracts: native logging/scoring, no remote model calls."""
from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
import json
import threading
from pathlib import Path
from test_partial_agentdyn import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from agentdojo import logging
from dscg.model_config import ModelConfig

try:
    from experiments import run_injection_precheck as precheck
    from experiments.common import injection_cohort as cohort_module
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
        artifacts = Path(__file__).resolve().parents[1] / 'workshop/artifacts/20261018_dual_benchmark/runner/test_runs'
        artifacts.mkdir(parents=True, exist_ok=True)
        self.temp = TemporaryDirectory(dir=artifacts)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.suite = FakeSuite()
        self.config = ModelConfig('offline', 'not-a-real-key', 'https://example.invalid', 'openai', 'TEST_KEY')
        self.patchers = [patch.object(precheck, 'get_suite', return_value=self.suite),
                         patch.object(cohort_module, 'get_suite', return_value=self.suite),
                         patch.object(precheck, 'resolve_model_config', return_value=self.config),
                         patch.object(cohort_module, 'resolve_model_config', return_value=self.config),
                         patch.object(precheck, 'make_openai_compatible_pipeline', side_effect=self.factory)]
        for p in self.patchers:
            p.start()
            self.addCleanup(p.stop)

    def factory(self, **kwargs):
        return SimpleNamespace(name='offline', dscg_model_config=self.config.public_dict()), SimpleNamespace(snapshot=lambda: {})

    @property
    def output(self):
        return self.root / 'screens' / 'offline_agentdojo_screen'

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

    def test_progress_is_visible_before_model_work_and_after_each_result(self):
        stream = StringIO()
        snapshots = []
        def observed_factory(**kwargs):
            snapshots.append(stream.getvalue())
            return self.factory(**kwargs)
        with patch.object(precheck, 'make_openai_compatible_pipeline', side_effect=observed_factory), redirect_stdout(stream):
            self.assertEqual(precheck.screen(config_path=None, run_name='screen', suites=['workspace'],
                results_dir=self.root / 'screens'), 0)
        text = stream.getvalue()
        self.assertTrue(all('开始尝试' in value for value in snapshots), text)
        self.assertIn('[1/2]', text)
        self.assertIn('[2/2]', text)
        self.assertIn('复测', text)
        self.assertIn('保留=1', text)
        self.assertIn('排除=1', text)
        self.assertNotIn('goal 0', text)
        self.assertNotIn(self.config.api_key, text)

    def test_waiting_progress_flushes_and_stops_when_work_finishes(self):
        self.assertTrue(hasattr(precheck, 'Progress'), 'periodic progress reporter missing')
        noticed = threading.Event()
        class Sink(StringIO):
            flushes = 0
            def write(self, value):
                if '等待' in value:
                    noticed.set()
                return super().write(value)
            def flush(self):
                self.flushes += 1
        stream = Sink()
        with redirect_stdout(stream):
            progress = precheck.Progress()
            with progress.waiting('workspace/injection_task_0', interval=0.01):
                self.assertTrue(noticed.wait(1), stream.getvalue())
            done = stream.getvalue()
            threading.Event().wait(0.03)
        self.assertEqual(stream.getvalue(), done)
        self.assertGreater(stream.flushes, 0)

    def test_keyboard_interrupt_stops_progress_and_preserves_attempt_for_resume(self):
        stream = StringIO()
        with patch.object(precheck, 'make_openai_compatible_pipeline', side_effect=KeyboardInterrupt), redirect_stdout(stream):
            self.assertEqual(precheck.cli(['screen', '--name', 'interrupt',
                '--results-dir', str(self.root / 'screens')]), 130)
        self.assertIn('同一条 screen 命令续跑', stream.getvalue())
        self.assertFalse(any(t.name == 'injection-precheck-progress' for t in threading.enumerate()))
        output = self.root / 'screens/offline_agentdojo_interrupt'
        self.assertFalse((output / 'cohort.json').exists())
        self.assertEqual(len(list(output.rglob('attempt.json'))), 1)

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
            'benchmark': __import__('test_partial_agentdyn').DOJO_IDENTITY, 'profile': 'baseline', 'main_model': model or self.config.public_dict(),
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
            with redirect_stderr(StringIO()), self.assertRaises(SystemExit):
                precheck.cli(['benchmark', '--cohort', str(self.output / 'cohort.json'),
                    '--name', 'bad', '--attack', 'not-an-attack'])
            runner.assert_not_called()

    def test_full_entry_accepts_cohort_and_forwards_all_existing_defense_controls(self):
        self.screen()
        from experiments import run_benchmark as full
        with patch.object(precheck.shared, 'main', return_value=0) as runner, redirect_stdout(StringIO()):
            self.assertEqual(full.cli(['--cohort', str(self.output / 'cohort.json'), '--name', 'unified',
                '--results-dir', str(self.root / 'benchmarks'), '--audit-router-mode', 'shadow',
                '--trace-level', 'full', '--no-tool-view', '--no-delegated-tasks',
                '--l1-projection-mode', 'off', '--audit-retries', '1', '--completion-prompt']), 0)
            options = runner.call_args.kwargs
            self.assertEqual(options['task_scope'], 'screened')
            self.assertEqual(options['audit_router_mode'], 'shadow')
            self.assertEqual(options['trace_level'], 'full')
            self.assertFalse(options['planning_tool_view'])
            self.assertFalse(options['delegated_tasks'])
            self.assertEqual(options['l1_projection_mode'], 'off')
            self.assertEqual(options['audit_retries'], 1)
            self.assertTrue(options['completion_prompt'])

    def test_cohort_conflicts_are_rejected_before_model_resolution(self):
        from experiments import run_benchmark as full
        for conflicting in (['--clean'], ['--task-manifest', 'tasks.json'], ['--write-task-manifest', 'out.json']):
            with self.subTest(conflicting=conflicting), patch.object(precheck, 'resolve_model_config') as resolve, redirect_stderr(StringIO()):
                with self.assertRaises(SystemExit):
                    full.cli(['--cohort', 'cohort.json', '--name', 'bad', *conflicting])
                resolve.assert_not_called()

    def test_legacy_benchmark_alias_requires_nonempty_cohort_before_dispatch(self):
        for extra in ([], ['--cohort=']):
            with self.subTest(extra=extra), patch.object(precheck.shared, 'main') as runner, redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                with self.assertRaises(SystemExit):
                    precheck.cli(['benchmark', '--name', 'must_not_run_full', *extra])
                runner.assert_not_called()

    def test_cohort_python_entry_rejects_suite_selection_that_would_expand_work(self):
        self.screen()
        from experiments import run_benchmark as full
        with patch.object(precheck.shared, 'main') as runner, self.assertRaises(ValueError):
            full.main(cohort_path=self.output / 'cohort.json', suites=['travel'], run_name='bad_suite')
        runner.assert_not_called()

    def legacy_binding(self):
        mapping = json.loads(Path(cohort_module.__file__).with_name('injection_cohort_compatibility.json').read_text())
        binding = precheck._binding(self.config, ['workspace'])
        binding['source'] = mapping['legacy_source']
        binding['screening_script_sha256'] = mapping['legacy_screening_script_sha256']
        return binding

    def test_old_agentdojo_frozen_cohort_and_manifest_reject_without_rewriting(self):
        self.screen()
        cohort = self.cohort(); binding = self.legacy_binding()
        cohort['binding'] = binding
        cohort['cohort_sha256'] = precheck._digest({k: v for k, v in cohort.items() if k != 'cohort_sha256'})
        cohort_path = self.output / 'cohort.json'
        cohort_path.write_text(json.dumps(cohort))
        manifest = self.output / 'screen_manifest.json'; manifest.write_text(json.dumps(binding))
        originals = {p: p.read_bytes() for p in [cohort_path, manifest, *self.output.rglob('attempt.json')]}
        with self.assertRaises(ValueError):
            self.screen()
        self.assertEqual(len(self.suite.executed), 3)
        for p, content in originals.items():
            self.assertEqual(p.read_bytes(), content)

    def test_old_agentdojo_pending_screen_rejects_without_repeating_completed_goal(self):
        self.suite.outcomes[1] = [RuntimeError('offline'), False, False]
        self.assertEqual(self.screen(), 1)
        binding = self.legacy_binding()
        manifest = self.output / 'screen_manifest.json'; manifest.write_text(json.dumps(binding))
        for p in self.output.rglob('attempt_manifest.json'):
            record = json.loads(p.read_text()); record['binding_sha256'] = precheck._digest(binding)
            p.write_text(json.dumps(record))
        original = manifest.read_bytes()
        with self.assertRaises(ValueError):
            self.screen()
        self.assertEqual(self.suite.executed.count('injection_task_0'), 1)
        self.assertEqual(manifest.read_bytes(), original)

    def test_old_agentdojo_unified_screen_rejects_after_backend_change(self):
        self.suite.outcomes[1] = [RuntimeError('offline'), False, False]
        self.assertEqual(self.screen(), 1)
        mapping = json.loads(Path(cohort_module.__file__).with_name('injection_cohort_compatibility.json').read_text())
        binding = precheck._binding(self.config, ['workspace'])
        binding['source']['source_sha256'] = mapping['equivalent_source_sha256'][0]
        manifest = self.output / 'screen_manifest.json'
        manifest.write_text(json.dumps(binding))
        for p in self.output.rglob('attempt_manifest.json'):
            record = json.loads(p.read_text()); record['binding_sha256'] = precheck._digest(binding)
            p.write_text(json.dumps(record))
        originals = {p: p.read_bytes() for p in [manifest, *self.output.rglob('attempt.json')]}
        with self.assertRaises(ValueError):
            self.screen()
        self.assertEqual(self.suite.executed.count('injection_task_0'), 1)
        for p, content in originals.items():
            self.assertEqual(p.read_bytes(), content)

    def test_unknown_legacy_script_or_changed_defense_runtime_is_not_accepted(self):
        self.screen()
        binding = self.legacy_binding(); binding['screening_script_sha256'] = '0' * 64
        (self.output / 'screen_manifest.json').write_text(json.dumps(binding))
        with self.assertRaises(ValueError):
            self.screen()
        binding = self.legacy_binding()
        (self.output / 'screen_manifest.json').write_text(json.dumps(binding))
        current = precheck.source_revision()
        current['source_sha256']['dscg/pipelines/baseline.py'] = '0' * 64
        with patch.object(cohort_module, 'source_revision', return_value=current), self.assertRaises(ValueError):
            self.screen()
        self.assertEqual(len(self.suite.executed), 3)

    def test_old_agentdojo_pre_relocation_cohort_rejects_without_rewriting_or_repeating_goals(self):
        self.screen()
        previous = json.loads((Path(__file__).with_name('fixtures') /
                               'experiments_layout_source_20261017.json').read_text())
        binding = precheck._binding(self.config, ['workspace'])
        binding.update(previous)
        cohort = self.cohort()
        cohort['binding'] = binding
        cohort['cohort_sha256'] = precheck._digest({k: v for k, v in cohort.items() if k != 'cohort_sha256'})
        cohort_path = self.output / 'cohort.json'
        cohort_path.write_text(json.dumps(cohort))
        manifest = self.output / 'screen_manifest.json'
        manifest.write_text(json.dumps(binding))
        originals = {p: p.read_bytes() for p in [manifest, cohort_path, *self.output.rglob('attempt.json')]}
        with self.assertRaises(ValueError):
            self.screen()
        self.assertEqual(self.suite.executed, ['injection_task_0', 'injection_task_1', 'injection_task_1'])
        for p, data in originals.items():
            self.assertEqual(p.read_bytes(), data)
        current = precheck._binding(self.config, ['workspace'])
        binding['screening_script_sha256'] = '0' * 64
        self.assertFalse(cohort_module._bindings_compatible(binding, current))

    def test_legacy_compatibility_rejects_unknown_added_runtime_source(self):
        binding = self.legacy_binding()
        current = precheck._binding(self.config, ['workspace'])
        current['source']['source_sha256']['dscg/unknown_new_layer.py'] = '0' * 64
        self.assertFalse(cohort_module._bindings_compatible(binding, current))

    def test_native_logged_context_error_is_not_a_valid_failure(self):
        self.suite.outcomes[1] = [('error', 'offline context_length_exceeded'), False, False]
        self.assertEqual(self.screen(), 1)
        status = json.loads((self.output / 'status.json').read_text())
        self.assertEqual(status['decisions']['workspace']['injection_task_1']['attempts'][0]['status'], 'error')
        self.assertEqual(self.screen(), 0)
        self.assertEqual(len(self.cohort()['decisions']['workspace']['injection_task_1']['attempts']), 3)

    def test_empty_scene_is_skipped_while_nonempty_scene_keeps_all_users(self):
        empty = FakeSuite(); empty.name = 'travel'; empty.outcomes = {0: [False, False], 1: [False, False]}
        lookup = lambda version, name: self.suite if name == 'workspace' else empty
        with patch.object(precheck, 'get_suite', side_effect=lookup), patch.object(cohort_module, 'get_suite', side_effect=lookup), redirect_stdout(StringIO()):
            self.assertEqual(precheck.screen(config_path=None, run_name='screen', suites=['workspace', 'travel'],
                results_dir=self.root / 'screens'), 0)
            with patch.object(precheck.shared, 'main', return_value=0) as runner:
                self.assertEqual(precheck.run_screened(self.output / 'cohort.json', config_path=None,
                    run_name='mixed', origin=True, results_dir=self.root / 'benchmarks'), 0)
                self.assertEqual(runner.call_args.kwargs['suites'], ['workspace'])
        attachment = json.loads((self.root / 'benchmarks/offline_agentdojo_mixed/screened_cohort.json').read_text())
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
        from experiments import run_benchmark as full
        with patch.object(precheck.shared, 'get_suite', return_value=self.suite), patch.object(precheck.shared, 'make_openai_compatible_pipeline', side_effect=fake_pipeline), patch.object(
            precheck.shared.attacks, 'load_attack', side_effect=fake_attack), patch.object(
            precheck.shared.benchmark, 'benchmark_suite_with_injections', side_effect=fake_results), redirect_stdout(StringIO()):
            self.assertEqual(full.main(cohort_path=self.output / 'cohort.json', config_path=None, run_name='selected',
                results_dir=self.root / 'benchmarks', origin=True, attack=['ignore_previous']), 0)
        base = self.root / 'benchmarks/offline_agentdojo_selected'
        summary = json.loads((base / 'ignore_previous/workspace/summary.json').read_text())
        self.assertEqual(summary['task_counts']['planned_tasks'], 4)
        self.assertEqual(summary['task_selection']['injection_task_ids'], ['injection_task_0'])
        self.assertEqual(len(summary['task_selection']['user_task_ids']), 4)
        self.assertEqual(summary['task_scope'], 'screened')
        self.assertEqual(summary['cohort_sha256'], self.cohort()['cohort_sha256'])
        self.assertIn('筛选目标', (base / 'summary.md').read_text())
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


# Explicitly retain historical upstream suites as generic offline fixtures.
def setUpModule():
    global _fixture_backend
    from test_partial_agentdyn import legacy_fixture_backend
    _fixture_backend = legacy_fixture_backend(globals())


def tearDownModule():
    _fixture_backend.close()
