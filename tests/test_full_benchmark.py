"""Offline full-run contracts; model factories and scored execution are mocked."""
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import json
import os
from pathlib import Path
from test_partial_agentdyn import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from agentdojo.attacks.attack_registry import ATTACKS
from agentdojo.task_suite import get_suite

from dscg.paths import BENCHMARK_RESULTS_DIR
from experiments import run_benchmark as full
from experiments import run_partial_benchmark as shared
from experiments.common.partial_controls import make_task_manifest, select_tasks, source_revision
from dscg.pipelines.defended import _append_full_trace

SUITES = ('workspace', 'travel', 'banking', 'slack')


def fake_pipeline(*args, **kwargs):
    return SimpleNamespace(name='offline-model', dscg_model_config={'model_id': 'offline-model'}), SimpleNamespace(
        total_prompt_tokens=0, total_completion_tokens=0, get_total_tokens=lambda: 0,
    )


def fake_attack(name, suite, pipeline):
    return SimpleNamespace(name=name, is_dos_attack=ATTACKS[name].is_dos_attack)


def fake_results(pipeline, suite, attack, logdir, **kwargs):
    keys = [(u, i) for u in kwargs['user_tasks'] for i in kwargs['injection_tasks']]
    return {'utility_results': dict.fromkeys(keys, True), 'security_results': dict.fromkeys(keys, False)}


class FullSelectionTests(unittest.TestCase):
    def test_full_selection_never_uses_partial_prefix_and_dos_keeps_native_denominator(self):
        users = [f'u{i}' for i in range(5)]
        injections = [f'i{i}' for i in range(4)]
        self.assertEqual(select_tasks(None, 's', users, injections, True, False), (users[:3], injections[:3]))
        self.assertEqual(select_tasks(None, 's', users, injections, True, False, task_scope='full'), (users, injections))
        self.assertEqual(select_tasks(None, 's', users, injections, True, True, task_scope='full'), (users, injections[:1]))
        self.assertEqual(select_tasks(None, 's', users, injections, False, False, task_scope='full'), (users, []))

    def test_full_manifest_cannot_silently_reduce_scope_and_is_reusable_for_dos(self):
        users = [f'u{i}' for i in range(5)]
        injections = [f'i{i}' for i in range(4)]
        manifest = {'benchmark': __import__('test_partial_agentdyn').DOJO_IDENTITY, 'suite_version': 'v1.2', 'suites': {'s': {
            'user_task_ids': users, 'injection_task_ids': injections,
        }}}
        self.assertEqual(select_tasks(manifest, 's', users, injections, True, True, task_scope='full'), (users, injections[:1]))
        self.assertEqual(manifest['suites']['s']['injection_task_ids'], injections)
        for field in ('user_task_ids', 'injection_task_ids'):
            smaller = json.loads(json.dumps(manifest))
            smaller['suites']['s'][field] = smaller['suites']['s'][field][:3]
            with self.subTest(field=field), self.assertRaises(ValueError):
                select_tasks(smaller, 's', users, injections, True, False, task_scope='full')

    def test_partial_manifest_rejected_before_any_model_factory(self):
        with TemporaryDirectory() as directory, patch.object(shared, 'make_openai_compatible_pipeline') as model:
            path = Path(directory) / 'partial.json'
            path.write_text(json.dumps(make_task_manifest()))
            with self.assertRaises(ValueError):
                full.main(origin=True, suites=['slack'], task_manifest_path=path,
                          results_dir=directory, attack='injecagent')
            model.assert_not_called()

    def test_manifest_export_contains_all_registered_ids_without_models_or_overwrite(self):
        with TemporaryDirectory() as directory, redirect_stdout(StringIO()), redirect_stderr(StringIO()), patch.object(shared, 'main') as run:
            path = Path(directory) / 'full_tasks.json'
            self.assertEqual(full.cli(['--write-task-manifest', str(path)]), 0)
            run.assert_not_called()
            manifest = json.loads(path.read_text())
            for name in SUITES:
                suite = get_suite('v1.2', name)
                self.assertEqual(manifest['suites'][name]['user_task_ids'], list(suite.user_tasks))
                self.assertEqual(manifest['suites'][name]['injection_task_ids'], list(suite.injection_tasks))
            original = path.read_bytes()
            with self.assertRaises(SystemExit):
                full.cli(['--write-task-manifest', str(path)])
            self.assertEqual(path.read_bytes(), original)
        self.assertEqual(len(make_task_manifest()['suites']['workspace']['user_task_ids']), 3)

    def test_source_is_informational_metadata_without_source_hashes(self):
        self.assertNotIn('source_sha256', source_revision())
        self.assertIn('commit', source_revision())


class FullCliTests(unittest.TestCase):
    def test_current_framework_and_baseline_clean_controls_reach_shared_runner(self):
        with patch.object(shared, 'main', return_value=0) as run, patch.dict(os.environ, {}, clear=True):
            self.assertEqual(full.cli(['--baseline', '--clean', '--force-rerun', '--name', 'global',
                                       '--model-config', 'models.toml', '--results-dir', '/tmp/full-output']), 0)
            options = run.call_args.kwargs
            self.assertEqual(options['task_scope'], 'full')
            self.assertTrue(options['origin'])
            self.assertFalse(options['run_attack'])
            self.assertTrue(options['force_rerun'])
            self.assertIsNone(options['defense'])
            self.assertFalse(options['planning_tool_view'])
            self.assertFalse(options['delegated_tasks'])
            self.assertEqual(options['l1_projection_mode'], 'off')
            self.assertEqual(options['config_path'], 'models.toml')
            self.assertEqual(options['results_dir'], '/tmp/full-output')
            self.assertEqual(full.cli(['--attack', 'all']), 0)
            self.assertEqual(run.call_args.kwargs['attack'], ['all'])
            self.assertEqual(run.call_args.kwargs['results_dir'], BENCHMARK_RESULTS_DIR)
            self.assertEqual(run.call_args.kwargs['l1_projection_mode'], 'off')
            self.assertTrue(run.call_args.kwargs['planning_tool_view'])
            self.assertTrue(run.call_args.kwargs['delegated_tasks'])
            self.assertEqual(run.call_args.kwargs['audit_router_mode'], 'shadow')
            self.assertEqual(run.call_args.kwargs['audit_retries'], 0)
            self.assertFalse(run.call_args.kwargs['completion_prompt'])

    def test_defaults_match_partial_attacks_but_not_its_task_scope(self):
        with patch.object(shared, 'main', return_value=0) as run, patch.dict(os.environ, {}, clear=True):
            self.assertEqual(full.cli([]), 0)
            self.assertEqual(run.call_args.kwargs['task_scope'], 'full')
            self.assertEqual(run.call_args.kwargs['attack'], ['typical'])
            self.assertEqual(shared.cli([]), 0)
            self.assertEqual(run.call_args.kwargs['task_scope'], 'partial')

    def test_progress_flag_reaches_full_and_partial_python_runner(self):
        import inspect
        self.assertIs(inspect.signature(full.main).parameters['progress'].default, False)
        self.assertIs(inspect.signature(shared.main).parameters['progress'].default, False)
        with patch.object(shared, 'main', return_value=0) as run:
            self.assertEqual(full.cli(['--progress']), 0)
            self.assertTrue(run.call_args.kwargs['progress'])
            self.assertEqual(shared.cli(['--progress']), 0)
            self.assertTrue(run.call_args.kwargs['progress'])

    def test_cli_returns_failure_and_rejects_interactive_attack_without_models(self):
        with patch.object(shared, 'main', return_value=1) as run, redirect_stderr(StringIO()):
            self.assertEqual(full.cli(['--attack', 'injecagent']), 1)
            run.reset_mock()
            with self.assertRaises(SystemExit):
                full.cli(['--attack', 'manual'])
            run.assert_not_called()

    def test_legacy_full_python_arguments_are_forwarded(self):
        with patch.object(shared, 'main', return_value=0) as run:
            self.assertEqual(full.main('main', 'audit', ['slack'], False, False, None, False, True,
                                       run_name='api', l1_projection_mode='shadow'), 0)
        self.assertFalse(run.call_args.kwargs['use_sandbox'])
        self.assertTrue(run.call_args.kwargs['use_security_checker'])
        self.assertEqual(run.call_args.kwargs['task_scope'], 'full')
        self.assertEqual(run.call_args.kwargs['results_dir'], BENCHMARK_RESULTS_DIR)


class FullExecutionTests(unittest.TestCase):
    def test_baseline_and_current_framework_score_all_catalog_ids_with_nested_reports(self):
        with TemporaryDirectory() as directory, redirect_stdout(StringIO()), patch.object(
            shared, 'make_openai_compatible_pipeline', side_effect=fake_pipeline,
        ) as native, patch.object(shared, 'make_defended_pipeline', side_effect=lambda *a, **k: (*fake_pipeline(), None)) as defended, patch.object(
            shared, 'load_tool_metadata', return_value={},
        ) as metadata, patch.object(shared.attacks, 'load_attack', side_effect=fake_attack), patch.object(
            shared.benchmark, 'benchmark_suite_with_injections', side_effect=fake_results,
        ) as benchmark:
            for origin, name in ((True, 'baseline'), (False, 'defended')):
                self.assertEqual(full.main(origin=origin, suites=list(SUITES), run_name=name,
                                           results_dir=directory, attack='injecagent', force_rerun=True), 0)
                base = Path(directory) / f'agentdojo/offline-model_{name}'
                self.assertEqual(json.loads((base / 'attack_manifest.json').read_text())['task_scope'], 'full')
                self.assertTrue((base / 'summary.md').exists())
                self.assertTrue((base / 'failure_cases.jsonl').exists())
                for suite_name in SUITES:
                    suite = get_suite('v1.2', suite_name)
                    output = base / 'injecagent' / suite_name
                    summary = json.loads((output / 'summary.json').read_text())
                    self.assertEqual(summary['task_selection']['user_task_ids'], list(suite.user_tasks))
                    self.assertEqual(summary['task_selection']['injection_task_ids'], list(suite.injection_tasks))
                    self.assertEqual(summary['task_counts']['planned_tasks'], len(suite.user_tasks) * len(suite.injection_tasks))
                    self.assertEqual(summary['task_scope'], 'full')
                    self.assertEqual(summary['defense'], None if origin else 'dscg')
                    self.assertTrue((output / 'run_manifest.json').exists())
                    if origin:
                        self.assertNotIn('sec_overhead', summary)
            self.assertEqual(benchmark.call_count, 8)
            self.assertEqual(native.call_count, 4)
            self.assertEqual(defended.call_count, 4)
            self.assertEqual(metadata.call_count, 1)
            self.assertTrue(all(call.kwargs['force_rerun'] for call in benchmark.call_args_list))
            self.assertTrue(all(call.kwargs['l1_projection_mode'] == 'projected' for call in defended.call_args_list))

    def test_full_clean_runs_every_user_and_never_loads_attack_or_security_metadata(self):
        def clean_results(pipeline, suite, logdir, **kwargs):
            return {'utility_results': {(user, None): True for user in kwargs['user_tasks']}}

        with TemporaryDirectory() as directory, redirect_stdout(StringIO()), patch.object(
            shared, 'make_openai_compatible_pipeline', side_effect=fake_pipeline,
        ), patch.object(shared, 'make_defended_pipeline') as defended, patch.object(shared, 'load_tool_metadata') as metadata, patch.object(
            shared.attacks, 'load_attack',
        ) as attack, patch.object(shared.benchmark, 'benchmark_suite_without_injections', side_effect=clean_results) as benchmark:
            self.assertEqual(full.main(origin=True, run_attack=False, suites=list(SUITES), results_dir=directory, run_name='clean'), 0)
            attack.assert_not_called()
            defended.assert_not_called()
            metadata.assert_not_called()
            self.assertEqual(sum(len(call.kwargs['user_tasks']) for call in benchmark.call_args_list),
                             sum(len(get_suite('v1.2', name).user_tasks) for name in SUITES))
            for path in Path(directory).rglob('summary.json'):
                summary = json.loads(path.read_text())
                self.assertIsNone(summary['metrics']['attack_success_rate'])
                self.assertEqual(summary['task_counts']['attacked_tasks'], 0)

    def test_dos_and_failed_attacks_keep_distinct_status_and_full_user_scope(self):
        def results(pipeline, suite, attack, logdir, **kwargs):
            if attack.name == 'injecagent':
                raise RuntimeError('offline attack failure')
            self.assertEqual(kwargs['user_tasks'], list(suite.user_tasks))
            self.assertEqual(kwargs['injection_tasks'], list(suite.injection_tasks)[:1])
            return fake_results(pipeline, suite, attack, logdir, **kwargs)

        with TemporaryDirectory() as directory, redirect_stdout(StringIO()), patch.object(
            shared, 'make_openai_compatible_pipeline', side_effect=fake_pipeline,
        ), patch.object(shared.attacks, 'load_attack', side_effect=fake_attack), patch.object(
            shared.benchmark, 'benchmark_suite_with_injections', side_effect=results,
        ):
            self.assertEqual(full.main(origin=True, suites=['slack'], results_dir=directory, run_name='mixed',
                                       attack=['injecagent', 'dos']), 1)
            base = Path(directory) / 'agentdojo/offline-model_mixed'
            statuses = json.loads((base / 'attack_manifest.json').read_text())['runs']
            self.assertEqual([run['status'] for run in statuses], ['error', 'completed'])
            summary = json.loads((base / 'dos/slack/summary.json').read_text())
            self.assertEqual(summary['attack_kind'], 'dos')
            self.assertEqual(summary['task_counts']['planned_tasks'], len(get_suite('v1.2', 'slack').user_tasks))

    def test_missing_security_is_unknown_rather_than_zero_asr(self):
        def results(pipeline, suite, attack, logdir, **kwargs):
            value = fake_results(pipeline, suite, attack, logdir, **kwargs)
            value['security_results'] = {}
            return value

        with TemporaryDirectory() as directory, redirect_stdout(StringIO()), patch.object(
            shared, 'make_openai_compatible_pipeline', side_effect=fake_pipeline,
        ), patch.object(shared.attacks, 'load_attack', side_effect=fake_attack), patch.object(
            shared.benchmark, 'benchmark_suite_with_injections', side_effect=results,
        ):
            self.assertEqual(full.main(origin=True, suites=['slack'], results_dir=directory,
                                       run_name='unknown', attack='injecagent'), 0)
            summary = json.loads(next(Path(directory).rglob('summary.json')).read_text())
            self.assertIsNone(summary['metrics']['attack_success_rate'])
            self.assertIsNone(summary['metrics']['defense_success_rate'])
            self.assertEqual(summary['task_counts']['attacked_tasks'], 0)

    def test_native_full_logging_sidecars_and_resume_use_every_task_in_nested_layout(self):
        suite = get_suite('v1.2', 'slack')
        model = 'gpt-4o-2024-05-13'

        def factory(*args, **kwargs):
            pipeline, tracker = fake_pipeline()
            pipeline.name = model
            pipeline.dscg_model_config['model_id'] = model
            return pipeline, tracker

        def execute(*args, **kwargs):
            shared.logging.Logger.get().log([
                {'role': 'user', 'content': [{'type': 'text', 'content': 'offline full fixture'}]},
                {'role': 'assistant', 'content': [{'type': 'text', 'content': 'done'}], 'tool_calls': None},
            ])
            _append_full_trace({'_dscg_trace_level': 'full'}, 'fixture', {'offline': True})
            return True, False

        with TemporaryDirectory() as directory, redirect_stdout(StringIO()), patch.object(
            shared, 'make_openai_compatible_pipeline', side_effect=factory,
        ), patch.object(type(suite), 'run_task_with_pipeline', autospec=True, side_effect=execute) as task:
            options = dict(model_id=model, origin=True, suites=['slack'], results_dir=directory, run_name='native',
                           attack='tool_knowledge')
            self.assertEqual(full.main(**options), 0)
            expected = len(suite.injection_tasks) * (len(suite.user_tasks) + 1)
            self.assertEqual(task.call_count, expected)  # Includes unscored injection-task preflights.
            base = Path(directory) / f'agentdojo/{model}_native'
            output = base / 'tool_knowledge/slack'
            scored = list(output.glob('user_task_*/tool_knowledge/injection_task_*.json'))
            self.assertEqual(len(scored), len(suite.user_tasks) * len(suite.injection_tasks))
            last = output / list(suite.user_tasks)[-1] / 'tool_knowledge' / f'{list(suite.injection_tasks)[-1]}.json'
            self.assertTrue(last.with_suffix('.dscg_trace.jsonl.gz').exists())
            original = last.read_bytes()
            self.assertEqual(full.main(**options), 0)
            self.assertEqual(task.call_count, expected)
            self.assertEqual(last.read_bytes(), original)
            self.assertEqual(full.main(**options, progress=True), 0)
            self.assertEqual(task.call_count, expected)
            self.assertEqual(last.read_bytes(), original)
            progress_options = {**options, 'run_name': 'native_progress', 'progress': True}
            self.assertEqual(full.main(**progress_options), 0)
            self.assertEqual(task.call_count, 2 * expected)
            progress_summary = json.loads((base.parent / f'{model}_native_progress' /
                'tool_knowledge/slack/summary.json').read_text())
            standard_summary = json.loads((output / 'summary.json').read_text())
            self.assertEqual(progress_summary['task_selection'], standard_summary['task_selection'])
            self.assertEqual(progress_summary['task_counts'], standard_summary['task_counts'])
            self.assertEqual(progress_summary['metrics'], standard_summary['metrics'])
            self.assertEqual(full.main(**options, force_rerun=True, progress=True), 0)
            self.assertEqual(task.call_count, 3 * expected)

    def test_scope_binding_rejects_partial_cache_and_preserves_existing_manifest(self):
        with TemporaryDirectory() as directory, redirect_stdout(StringIO()), patch.object(
            shared, 'make_openai_compatible_pipeline', side_effect=fake_pipeline,
        ), patch.object(shared.attacks, 'load_attack', side_effect=fake_attack), patch.object(
            shared.benchmark, 'benchmark_suite_with_injections', side_effect=fake_results,
        ) as benchmark:
            options = dict(origin=True, suites=['slack'], results_dir=directory, run_name='same', attack='injecagent')
            self.assertEqual(shared.main(**options), 0)
            path = Path(directory) / 'agentdojo/offline-model_same/injecagent/slack/run_manifest.json'
            original = path.read_bytes()
            root = Path(directory) / 'agentdojo/offline-model_same'
            previous_reports = {p: p.read_bytes() for p in root.rglob('*') if p.is_file()}
            benchmark.reset_mock()
            self.assertEqual(full.main(**options, force_rerun=True), 1)
            benchmark.assert_not_called()
            self.assertEqual(path.read_bytes(), original)
            self.assertTrue(all(p.read_bytes() == raw for p, raw in previous_reports.items()))


if __name__ == '__main__':
    unittest.main()


# Explicitly retain historical upstream suites as generic offline fixtures.
def setUpModule():
    global _fixture_backend
    from test_partial_agentdyn import legacy_fixture_backend
    _fixture_backend = legacy_fixture_backend(globals())


def tearDownModule():
    _fixture_backend.close()
