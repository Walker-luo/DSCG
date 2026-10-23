from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from dscg.benchmark_catalog import get_suites, get_backend
from experiments import run_benchmark as full, run_partial_benchmark as partial
from test_partial_attacks import fake_pipeline, fake_attack, fake_results
import parallel_fixture


class ParallelRunnerTests(unittest.TestCase):
    def test_later_group_binding_conflict_precedes_spawn_and_preserves_outputs(self):
        root = Path(__file__).resolve().parents[1] / 'workshop/artifacts/20261018_qwen_parallel/test_runs'
        root.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(dir=root) as temp, parallel_fixture.patched(), redirect_stdout(StringIO()):
            options = dict(origin=True, suites=list(get_suites())[:2], attack='tool_knowledge',
                           results_dir=temp, run_name='conflict')
            self.assertEqual(partial.main(**options), 0)
            base = Path(temp) / f'offline-model_{get_backend().id}_conflict'
            path = sorted(base.glob('*/*/run_manifest.json'))[-1]
            binding = json.loads(path.read_text()); binding['profile'] = 'changed'
            path.write_text(json.dumps(binding))
            before = {p: p.read_bytes() for p in base.rglob('*') if p.is_file()}
            for reuse in (False, True):
                with patch.object(partial, 'execute_groups') as dispatch:
                    self.assertEqual(partial.main(**options, workers=2, reuse=reuse), 1)
                dispatch.assert_not_called()
                self.assertEqual(before, {p: p.read_bytes() for p in base.rglob('*') if p.is_file()})

    def test_full_spawn_retains_all_ids_in_selected_suites(self):
        from dscg.benchmark_catalog import get_suite
        root = Path(__file__).resolve().parents[1] / 'workshop/artifacts/20261018_qwen_parallel/test_runs'
        root.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(dir=root) as temp, parallel_fixture.patched(), \
             patch.object(partial, '_execute_group', parallel_fixture.group), redirect_stdout(StringIO()):
            suites = list(get_suites())[-2:]
            self.assertEqual(full.main(suites=suites, attack='tool_knowledge', workers=2,
                results_dir=temp, run_name='full'), 0)
            base = Path(temp) / f'offline-model_{get_backend().id}_full'
            for name in suites:
                summary = json.loads((base / 'tool_knowledge' / name / 'summary.json').read_text())
                native = get_suite('v1.2', name)
                self.assertEqual(summary['task_selection']['user_task_ids'], list(native.user_tasks))
                self.assertEqual(summary['task_selection']['injection_task_ids'], list(native.injection_tasks))

    def test_frozen_cohort_spawn_skips_empty_scene_without_backfilling_prefix(self):
        from experiments import run_injection_precheck as precheck
        from experiments.common import injection_cohort as cohorts
        from dscg.benchmark_catalog import get_suite
        root = Path(__file__).resolve().parents[1] / 'workshop/artifacts/20261018_qwen_parallel/test_runs'
        root.mkdir(parents=True, exist_ok=True)
        output = StringIO()
        with TemporaryDirectory(dir=root) as temp, redirect_stdout(output):
            names = list(get_suites())[:3]
            excluded = {name: next(iter(get_suite('v1.2', name).injection_tasks)) for name in names}
            def screen_goal(suite, pipeline, task, injection_task=None, injections=None):
                parallel_fixture.execute(suite, pipeline, task, injection_task, injections)
                return suite.name != names[-1] and task.ID != excluded[suite.name], False
            with parallel_fixture.patched(execute_fn=screen_goal), \
                 patch.object(precheck, 'resolve_model_config', return_value=parallel_fixture.MAIN), \
                 patch.object(precheck, 'make_openai_compatible_pipeline', side_effect=parallel_fixture.baseline):
                status = precheck.screen(config_path=None, run_name='screen', suites=names, results_dir=temp)
                attempts = [json.loads(p.read_text()) for p in Path(temp).glob('*/attempts/*/*/*/attempt.json')]
                self.assertEqual(status, 0, [(a.get('error_type'), a.get('trace_path')) for a in attempts if a['status'] == 'error'])
            cohort = Path(temp) / f'offline-model_{get_backend().id}_screen/cohort.json'
            with parallel_fixture.patched(), patch.object(cohorts, 'resolve_model_config', side_effect=parallel_fixture.resolve), \
                 patch.object(partial, '_execute_group', parallel_fixture.group):
                self.assertEqual(partial.main(cohort_path=cohort, suites=names, origin=True,
                    results_dir=temp, run_name='screened', workers=2, attack='tool_knowledge'), 0)
            base = Path(temp) / f'offline-model_{get_backend().id}_screened'
            attached = json.loads((base / 'screened_cohort.json').read_text())
            self.assertEqual(attached['skipped_suites'], names[-1:])
            for name in names[:-1]:
                native = get_suite('v1.2', name)
                summary = json.loads((base / 'tool_knowledge' / name / 'summary.json').read_text())
                self.assertEqual(summary['task_selection']['user_task_ids'], list(native.user_tasks)[:3])
                self.assertEqual(summary['task_selection']['injection_task_ids'], list(native.injection_tasks)[1:3])
            with parallel_fixture.patched(), patch.object(cohorts, 'resolve_model_config', side_effect=parallel_fixture.resolve), \
                 patch.object(partial, '_execute_group', parallel_fixture.group):
                status = partial.main(cohort_path=cohort, suites=names, origin=True,
                    results_dir=temp, run_name='screened', workers=1, attack='tool_knowledge', reuse=True)
                self.assertEqual(status, 0, '\n'.join(output.getvalue().splitlines()[-15:]))

    def test_native_spawn_matches_serial_scores_costs_preflights_and_reuse(self):
        root = Path(__file__).resolve().parents[1] / 'workshop/artifacts/20261018_qwen_parallel/test_runs'
        root.mkdir(parents=True, exist_ok=True)
        original = partial._execute_group
        for origin in (True, False):
            for clean in (True, False):
                with self.subTest(origin=origin, clean=clean), TemporaryDirectory(dir=root) as temp, \
                     parallel_fixture.patched(), redirect_stdout(StringIO()):
                    options = dict(origin=origin, run_attack=not clean, suites=list(get_suites())[:2],
                                   results_dir=temp, attack='tool_knowledge')
                    self.assertEqual(partial.main(**options, workers=1, run_name='serial'), 0)
                    # The importable fixture patches only inside each real spawned process.
                    with patch.object(partial, '_execute_group', parallel_fixture.group):
                        self.assertEqual(partial.main(**options, workers=2, run_name='parallel'), 0)
                    serial = Path(temp) / f'offline-model_{get_backend().id}_serial'
                    parallel = Path(temp) / f'offline-model_{get_backend().id}_parallel'
                    for p in serial.glob('*/*/summary.json'):
                        a = json.loads(p.read_text()); b = json.loads((parallel / p.relative_to(serial)).read_text())
                        for field in ('task_selection', 'utility_score', 'security_score', 'overhead', 'sec_overhead'):
                            self.assertEqual(a.get(field), b.get(field), field)
                    before = {p: p.read_bytes() for p in parallel.glob('*/*/*/*/*.json')}
                    with patch.object(partial, '_execute_group', parallel_fixture.group):
                        self.assertEqual(partial.main(**options, workers=3, run_name='parallel', reuse=True), 0)
                    self.assertTrue(before)
                    for p, content in before.items(): self.assertEqual(p.read_bytes(), content)
                    self.assertIs(partial._execute_group, original)

    def test_cli_workers_both_entries_and_no_invalid_counts(self):
        for cli in (full.cli, partial.cli):
            with patch.object(partial, 'main', return_value=0) as run:
                self.assertEqual(cli(['--workers', '3']), 0)
                self.assertEqual(run.call_args.kwargs['workers'], 3)
            for count in ('0', '-1'):
                with redirect_stderr(StringIO()), self.assertRaises(SystemExit):
                    cli(['--workers', count])

    def test_serial_groups_preserve_global_scope_and_parent_only_aggregation(self):
        root = Path(__file__).resolve().parents[1] / 'workshop/artifacts/20261018_qwen_parallel/test_runs'
        root.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(dir=root) as temp, \
             patch.object(partial, 'make_openai_compatible_pipeline', side_effect=fake_pipeline), \
             patch.object(partial.attacks, 'load_attack', side_effect=fake_attack), \
             patch.object(partial.benchmark, 'benchmark_suite_with_injections', side_effect=fake_results) as native, \
             redirect_stdout(StringIO()):
            suites = list(get_suites())[:2]
            self.assertEqual(partial.main(origin=True, suites=suites, attack='typical',
                             run_name='serial', results_dir=temp, workers=1), 0)
            base = Path(temp) / f'offline-model_{get_backend().id}_serial'
            self.assertEqual(native.call_count, 6)
            self.assertEqual(json.loads((base / 'suite_manifest.json').read_text())['suites'], suites)
            manifest = json.loads((base / 'attack_manifest.json').read_text())
            self.assertEqual(manifest['execution']['planned_groups'], 6)
            self.assertEqual(manifest['execution']['workers_effective'], 1)
            self.assertEqual(len(list(base.glob('*/*/summary.json'))), 6)
