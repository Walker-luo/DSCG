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
import serial_fixture


class SerialRunnerTests(unittest.TestCase):
    def test_progress_group_error_records_safe_location_and_task(self):
        root = Path(__file__).resolve().parents[1] / 'workshop/artifacts/20261020_deepseek_agentdyn_typeerror/test_runs'
        root.mkdir(parents=True, exist_ok=True)
        def fail_second_goal(suite, pipeline, task, injection_task=None, injections=None):
            if task.ID == 'injection_task_1' and injection_task is None:
                raise TypeError('sensitive-prompt-text')
            return serial_fixture.execute(suite, pipeline, task, injection_task, injections)
        with TemporaryDirectory(dir=root) as temp, serial_fixture.patched(execute_fn=fail_second_goal), redirect_stdout(StringIO()):
            self.assertEqual(partial.main(origin=True, progress=True, suites=list(get_suites())[:1],
                attack='ignore_previous', results_dir=temp, run_name='diagnostic'), 1)
            base = Path(temp) / get_backend().id / 'offline-model_diagnostic'
            execution = json.loads(next((base / 'execution').glob('*/execution.json')).read_text())
            error = execution['groups'][0]['execution_error']
            self.assertEqual(error['stage'], 'goal_preflight')
            self.assertEqual(error['task_id'], 'injection_task_1')
            self.assertTrue(error['frames'])
            case = json.loads((base / 'failure_cases.jsonl').read_text().splitlines()[0])
            self.assertEqual(case['execution_error'], error)
            self.assertNotIn('sensitive-prompt-text', (base / 'failure_cases.jsonl').read_text())

    def test_later_group_binding_conflict_precedes_factory_and_preserves_outputs(self):
        root = Path(__file__).resolve().parents[1] / 'workshop/artifacts/20261018_serial_lightweight/test_runs'
        root.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(dir=root) as temp, serial_fixture.patched(), redirect_stdout(StringIO()):
            options = dict(origin=True, suites=list(get_suites())[:2], attack='tool_knowledge',
                           results_dir=temp, run_name='conflict')
            self.assertEqual(partial.main(**options), 0)
            base = Path(temp) / f'{get_backend().id}/offline-model_conflict'
            path = sorted(base.glob('*/*/run_manifest.json'))[-1]
            binding = json.loads(path.read_text()); binding['profile'] = 'changed'
            path.write_text(json.dumps(binding))
            before = {p: p.read_bytes() for p in base.rglob('*') if p.is_file()}
            for reuse in (False, True):
                with patch.object(partial, 'make_openai_compatible_pipeline') as dispatch:
                    self.assertEqual(partial.main(**options, reuse=reuse), 1)
                dispatch.assert_not_called()
                self.assertEqual(before, {p: p.read_bytes() for p in base.rglob('*') if p.is_file()})

    def test_full_serial_retains_all_ids_in_selected_suites(self):
        from dscg.benchmark_catalog import get_suite
        root = Path(__file__).resolve().parents[1] / 'workshop/artifacts/20261018_serial_lightweight/test_runs'
        root.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(dir=root) as temp, serial_fixture.patched(), redirect_stdout(StringIO()):
            suites = list(get_suites())[-2:]
            self.assertEqual(full.main(suites=suites, attack='tool_knowledge',
                results_dir=temp, run_name='full'), 0)
            base = Path(temp) / f'{get_backend().id}/offline-model_full'
            for name in suites:
                native = get_suite('v1.2', name)
                binding = json.loads((base / 'tool_knowledge' / name / 'run_manifest.json').read_text())
                self.assertEqual(binding['task_selection']['users'], list(native.user_tasks))
                self.assertEqual(binding['task_selection']['injections'], list(native.injection_tasks))
                summary_path = base / 'tool_knowledge' / name / 'summary.json'
                if get_backend().id == 'agentdyn' and name == 'dailylife':
                    self.assertFalse(summary_path.exists())
                else:
                    summary = json.loads(summary_path.read_text())
                    self.assertEqual(summary['task_selection']['user_task_ids'], list(native.user_tasks))
                    self.assertEqual(summary['task_selection']['injection_task_ids'], list(native.injection_tasks))

    def test_frozen_cohort_serial_skips_empty_scene_without_backfilling_prefix(self):
        from experiments import run_injection_precheck as precheck
        from experiments.common import injection_cohort as cohorts
        from dscg.benchmark_catalog import get_suite
        root = Path(__file__).resolve().parents[1] / 'workshop/artifacts/20261018_serial_lightweight/test_runs'
        root.mkdir(parents=True, exist_ok=True)
        output = StringIO()
        with TemporaryDirectory(dir=root) as temp, redirect_stdout(output):
            names = list(get_suites())[:3]
            excluded = {name: next(iter(get_suite('v1.2', name).injection_tasks)) for name in names}
            def screen_goal(suite, pipeline, task, injection_task=None, injections=None):
                serial_fixture.execute(suite, pipeline, task, injection_task, injections)
                return suite.name != names[-1] and task.ID != excluded[suite.name], False
            with serial_fixture.patched(execute_fn=screen_goal), \
                 patch.object(precheck, 'resolve_model_config', return_value=serial_fixture.MAIN), \
                 patch.object(precheck, 'make_openai_compatible_pipeline', side_effect=serial_fixture.baseline):
                status = precheck.screen(config_path=None, run_name='screen', suites=names, results_dir=temp)
                attempts = [json.loads(p.read_text()) for p in Path(temp).glob('*/*/attempts/*/*/*/attempt.json')]
                self.assertTrue(attempts)
                self.assertEqual(status, 0, [(a.get('error_type'), a.get('trace_path')) for a in attempts if a['status'] == 'error'])
            cohort = Path(temp) / f'{get_backend().id}/offline-model_screen/cohort.json'
            with serial_fixture.patched(), patch.object(cohorts, 'resolve_model_config', side_effect=serial_fixture.resolve):
                self.assertEqual(partial.main(cohort_path=cohort, suites=names, origin=True,
                    results_dir=temp, run_name='screened', attack='tool_knowledge'), 0)
            base = Path(temp) / f'{get_backend().id}/offline-model_screened'
            attached = json.loads((base / 'screened_cohort.json').read_text())
            self.assertEqual(attached['skipped_suites'], names[-1:])
            for name in names[:-1]:
                native = get_suite('v1.2', name)
                summary = json.loads((base / 'tool_knowledge' / name / 'summary.json').read_text())
                self.assertEqual(summary['task_selection']['user_task_ids'], list(native.user_tasks)[:3])
                self.assertEqual(summary['task_selection']['injection_task_ids'], list(native.injection_tasks)[1:3])
            with serial_fixture.patched(), patch.object(cohorts, 'resolve_model_config', side_effect=serial_fixture.resolve):
                status = partial.main(cohort_path=cohort, suites=names, origin=True,
                    results_dir=temp, run_name='screened', attack='tool_knowledge', reuse=True)
                self.assertEqual(status, 0, '\n'.join(output.getvalue().splitlines()[-15:]))

    def test_native_cache_preserves_scores_costs_and_preflights(self):
        root = Path(__file__).resolve().parents[1] / 'workshop/artifacts/20261018_serial_lightweight/test_runs'
        root.mkdir(parents=True, exist_ok=True)
        for origin in (True, False):
            for clean in (True, False):
                calls = []
                def execute(*args, **kwargs):
                    calls.append((args[0].name, args[2].ID))
                    return serial_fixture.execute(*args, **kwargs)
                with self.subTest(origin=origin, clean=clean), TemporaryDirectory(dir=root) as temp, \
                     serial_fixture.patched(execute_fn=execute), redirect_stdout(StringIO()):
                    options = dict(origin=origin, run_attack=not clean, suites=list(get_suites())[:2],
                                   results_dir=temp, attack='tool_knowledge', run_name='serial')
                    self.assertEqual(partial.main(**options), 0)
                    before_calls = len(calls)
                    self.assertEqual(before_calls, 6 if clean else 24)
                    base = Path(temp) / f'{get_backend().id}/offline-model_serial'
                    traces = {p: p.read_bytes() for p in base.glob('*/*/*/*/*.json')}
                    self.assertEqual(partial.main(**options, reuse=True), 0)
                    self.assertEqual(len(calls), before_calls)
                    for p, content in traces.items(): self.assertEqual(p.read_bytes(), content)

    def test_old_hash_bearing_run_resumes_without_rewriting_bindings(self):
        root = Path(__file__).resolve().parents[1] / 'workshop/artifacts/20261018_serial_lightweight/test_runs'
        root.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(dir=root) as temp, serial_fixture.patched(), redirect_stdout(StringIO()):
            options = dict(origin=True, suites=list(get_suites())[:1], attack='tool_knowledge',
                           results_dir=temp, run_name='old_hashes')
            self.assertEqual(partial.main(**options), 0)
            base = Path(temp) / f'{get_backend().id}/offline-model_old_hashes'
            paths = [*base.glob('*/*/run_manifest.json'), base/'benchmark_plan.json', base/'suite_manifest.json', base/'attack_manifest.json']
            for path in paths:
                value = json.loads(path.read_text())
                value['benchmark'].update(implementation_sha256='old-runtime', runtime_variant='official-release')
                if 'source' in value:
                    value['source'].update(source_sha256={'unknown_old.py':'any'}, python='3.10.19', commit='old')
                path.write_text(json.dumps(value))
            originals = {p: p.read_bytes() for p in base.glob('*/*/run_manifest.json')}
            from dscg.benchmark_catalog import get_suite
            with patch.object(type(get_suite('v1.2', get_suites()[0])), 'run_task_with_pipeline',
                              side_effect=AssertionError('cached task executed')):
                self.assertEqual(partial.main(**options, reuse=True), 0)
            for p, data in originals.items(): self.assertEqual(p.read_bytes(), data)
            record = json.loads(next((base/'reuse').glob('*/compatibility.json')).read_text())
            self.assertFalse(record['source_equivalence_verified'])
            self.assertEqual(record['verification_mode'], 'configuration_only')

    def test_workers_removed_from_both_cli_and_python_api(self):
        import inspect
        for cli in (full.cli, partial.cli):
            with redirect_stderr(StringIO()), self.assertRaises(SystemExit) as result:
                cli(['--workers', '3'])
            self.assertEqual(result.exception.code, 2)
        for entry in (full.main, partial.main):
            self.assertNotIn('workers', inspect.signature(entry).parameters)
            with self.assertRaises(TypeError):
                entry(workers=1)

    def test_interrupt_keeps_completed_group_for_resume(self):
        root = Path(__file__).resolve().parents[1] / 'workshop/artifacts/20261018_serial_lightweight/test_runs'
        root.mkdir(parents=True, exist_ok=True)
        calls = []
        def execute(*args, **kwargs):
            calls.append((args[0].name, args[2].ID))
            return serial_fixture.execute(*args, **kwargs)
        with TemporaryDirectory(dir=root) as temp, serial_fixture.patched(execute_fn=execute), redirect_stdout(StringIO()):
            names = list(get_suites())[:2]
            options = dict(origin=True, suites=names, run_name='interrupt', results_dir=temp, attack='tool_knowledge')
            original = partial._execute_group
            def group(job):
                if job['suite'] == names[1]: raise KeyboardInterrupt
                return original(job)
            with patch.object(partial, '_execute_group', side_effect=group):
                self.assertEqual(partial.main(**options), 130)
            first_calls = len(calls)
            self.assertEqual(first_calls, 12)
            stored = Path(temp)/get_backend().id/'offline-model_interrupt'
            self.assertTrue((stored/'summary.md').exists())
            self.assertTrue((stored/'l3_router_summary.json').exists())
            self.assertEqual(partial.main(**options, reuse=True), 0)
            self.assertEqual(sum(name == names[0] for name, _ in calls), first_calls)
            self.assertEqual(len(calls), 24)

    def test_preparation_creates_no_pipeline_and_emits_no_scene_blocks(self):
        root = Path(__file__).resolve().parents[1] / 'workshop/artifacts/20261018_serial_lightweight/test_runs'
        root.mkdir(parents=True, exist_ok=True)
        output = StringIO()
        with TemporaryDirectory(dir=root) as temp, serial_fixture.patched(), redirect_stdout(output):
            original = partial._execute_group
            def group(job):
                self.assertNotIn('正在测试套件', output.getvalue())
                self.assertNotIn('套件统计', output.getvalue())
                with patch.object(partial, '_describe_pipeline', side_effect=AssertionError('second preparation')):
                    return original(job)
            with patch.object(partial, '_execute_group', side_effect=group), \
                 patch.object(partial, 'make_openai_compatible_pipeline', side_effect=serial_fixture.baseline) as factory:
                self.assertEqual(partial.main(origin=True, suites=list(get_suites())[:2],
                    results_dir=temp, run_name='quiet', attack='tool_knowledge'), 0)
                self.assertEqual(factory.call_count, 2)
            self.assertEqual(output.getvalue().count('模型: offline-model；后端:'), 1)

    def test_mocked_groups_preserve_global_scope_and_parent_only_aggregation(self):
        from experiments.common.attack_execution import iter_serial_results
        root = Path(__file__).resolve().parents[1] / 'workshop/artifacts/20261018_serial_lightweight/test_runs'
        root.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(dir=root) as temp, \
             patch.object(partial, 'make_openai_compatible_pipeline', side_effect=serial_fixture.baseline), \
             patch.object(partial, 'resolve_model_config', side_effect=serial_fixture.resolve), \
             patch.object(partial.attacks, 'load_attack', side_effect=fake_attack), \
             patch.object(partial.benchmark, 'benchmark_suite_with_injections', side_effect=fake_results) as native, \
             patch.object(partial, 'iter_attack_results', side_effect=iter_serial_results), \
             redirect_stdout(StringIO()):
            suites = list(get_suites())[:2]
            self.assertEqual(partial.main(origin=True, suites=suites, attack='typical',
                             run_name='serial', results_dir=temp), 0)
            base = Path(temp) / f'{get_backend().id}/offline-model_serial'
            self.assertEqual(native.call_count, 6)
            self.assertEqual(json.loads((base / 'suite_manifest.json').read_text())['suites'], suites)
            manifest = json.loads((base / 'attack_manifest.json').read_text())
            self.assertEqual(manifest['execution']['planned_groups'], 6)
            self.assertEqual(manifest['execution']['mode'], 'parallel_attacks')
            self.assertEqual(len(list(base.glob('*/*/summary.json'))), 6)
