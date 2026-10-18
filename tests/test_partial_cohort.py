"""Partial cohort integration with real frozen evidence and no model requests."""
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import json
from pathlib import Path
from test_partial_agentdyn import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from dscg.model_config import ModelConfig
from experiments.common import injection_cohort as cohort
from experiments import run_injection_precheck as precheck
from experiments import run_partial_benchmark as runner
from test_injection_precheck import FakeSuite


class PartialCohortTests(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).resolve().parents[1] / 'workshop/artifacts/20261018_dual_benchmark/runner/test_runs'
        root.mkdir(parents=True, exist_ok=True)
        temp = TemporaryDirectory(dir=root); self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.config = ModelConfig('offline', 'test', 'https://example.invalid', 'openai', 'TEST_KEY')
        self.suites = {}
        for name in ['workspace', 'travel', 'banking', 'slack']:
            suite = FakeSuite(); suite.name = name
            suite.injection_tasks = {f'injection_task_{i}': SimpleNamespace(ID=f'injection_task_{i}', GOAL=f'goal {i}') for i in range(5)}
            suite.outcomes = {0: [False, False], 1: [True], 2: [False, False], 3: [True], 4: [True]}
            self.suites[name] = suite
        lookup = lambda version, name: self.suites[name]
        tracker = SimpleNamespace(snapshot=lambda: {}, total_prompt_tokens=0,
                                  total_completion_tokens=0, get_total_tokens=lambda: 0)
        factory = lambda *a, **kw: (SimpleNamespace(name='offline', dscg_model_config=self.config.public_dict()), tracker)
        self.factory = factory
        patches = [patch.object(module, 'get_suite', side_effect=lookup) for module in [runner, cohort, precheck]]
        patches += [patch.object(module, 'resolve_model_config', return_value=self.config) for module in [cohort, precheck, runner]]
        patches += [patch.object(module, 'make_openai_compatible_pipeline', side_effect=factory) for module in [runner, precheck]]
        patches += [patch.object(runner, '_describe_pipeline', side_effect=lambda *a, **kw: factory()[0])]
        patches += [patch.object(runner.attacks, 'load_attack', return_value=SimpleNamespace(is_dos_attack=False)),
                    patch.object(runner.benchmark, 'benchmark_suite_with_injections', side_effect=self.scored_results),
                    redirect_stdout(StringIO())]
        for item in patches:
            item.start() if hasattr(item, 'start') else item.__enter__()
            self.addCleanup(item.stop if hasattr(item, 'stop') else lambda item=item: item.__exit__(None, None, None))

    @staticmethod
    def scored_results(*args, **kwargs):
        keys = [(u, i) for u in kwargs['user_tasks'] for i in kwargs['injection_tasks']]
        return {'utility_results': dict.fromkeys(keys, True), 'security_results': dict.fromkeys(keys, False)}

    def screen(self, names=None):
        self.assertEqual(precheck.screen(config_path=None, run_name='cohort', suites=names or list(self.suites),
                                         results_dir=self.root / 'screens'), 0)
        return self.root / 'screens/agentdojo/offline_cohort/cohort.json'

    def test_cli_filters_original_injection_prefix_without_replacing_or_expanding_users(self):
        path = self.screen(); original = path.read_bytes()
        self.assertEqual(runner.cli(['--cohort', str(path), '--baseline', '--name', 'partial',
            '--suites', 'travel', 'banking', 'slack', '--results-dir', str(self.root / 'runs')]), 0)
        base = self.root / 'runs/agentdojo/offline_partial'
        manifest = json.loads((base / 'attack_manifest.json').read_text())
        self.assertEqual(manifest['task_scope'], 'partial_screened')
        self.assertEqual(manifest['suites'], ['travel', 'banking', 'slack'])
        total = 0
        for attack in ['ignore_previous', 'important_instructions', 'tool_knowledge']:
            self.assertFalse((base / attack / 'workspace').exists())
            for name in ['travel', 'banking', 'slack']:
                data = json.loads((base / attack / name / 'summary.json').read_text())
                self.assertEqual(data['task_selection']['user_task_ids'], ['user_task_0', 'user_task_1', 'user_task_2'])
                self.assertEqual(data['task_selection']['injection_task_ids'], ['injection_task_1'])
                total += data['task_counts']['total_tasks']
        self.assertEqual(total, 27)
        attachment = json.loads((base / 'screened_cohort.json').read_text())
        self.assertEqual(attachment['counts']['travel']['planned_per_targeted_attack'], 3)
        self.assertEqual(attachment['counts']['travel']['prefix_targets'], 3)
        self.assertEqual(json.loads((base / 'preflight_report.json').read_text())['planned_preflight_samples'], 9)
        self.assertEqual(path.read_bytes(), original)
        self.assertIn('前 3', (base / 'summary.md').read_text())

    def test_python_api_can_select_one_suite_and_empty_prefix_is_skipped(self):
        self.suites['travel'].outcomes[1] = [False, False]
        path = self.screen()
        options = dict(origin=True, suites=['travel', 'banking'], attack='injecagent',
                       cohort_path=path, results_dir=self.root / 'runs', run_name='mixed')
        self.assertEqual(runner.main(**options), 0)
        base = self.root / 'runs/agentdojo/offline_mixed'
        attachment = json.loads((base / 'screened_cohort.json').read_text())
        self.assertEqual(attachment['skipped_suites'], ['travel'])
        self.assertEqual(attachment['counts']['travel']['planned_per_targeted_attack'], 0)
        self.assertFalse((base / 'injecagent/travel').exists())
        before = {p: p.read_bytes() for p in base.rglob('*') if p.is_file()}
        with self.assertRaises(ValueError):
            runner.main(**{**options, 'suites': ['banking'], 'force_rerun': True})
        self.assertEqual({p: p.read_bytes() for p in base.rglob('*') if p.is_file()}, before)
        with self.assertRaises(ValueError):
            runner.main(**{**options, 'suites': ['travel'], 'run_name': 'empty'})

    def test_conflicts_missing_suites_and_corrupt_evidence_are_rejected(self):
        path = self.screen()
        for args in [['--clean'], ['--task-manifest', 'tasks.json'], ['--write-task-manifest', 'out.json']]:
            with self.subTest(args=args), redirect_stderr(StringIO()), self.assertRaises(SystemExit):
                runner.cli(['--cohort', str(path), '--name', 'invalid', *args])
        with self.assertRaises(ValueError):
            runner.main(cohort_path=path, origin=True, run_name='dos', attack='dos', results_dir=self.root / 'runs')
        data = json.loads(path.read_text())
        trace = Path(data['decisions']['travel']['injection_task_1']['attempts'][0]['trace_path'])
        trace.write_text('{}')
        with self.assertRaises(ValueError):
            runner.main(cohort_path=path, origin=True, run_name='corrupt', results_dir=self.root / 'runs')

    def test_cohort_must_cover_requested_suites(self):
        path = self.screen(['travel', 'banking', 'slack'])
        with self.assertRaises(ValueError):
            runner.main(cohort_path=path, origin=True, run_name='missing', results_dir=self.root / 'runs')

    def test_full_cli_suite_subset_keeps_all_users_and_all_kept_targets(self):
        from experiments import run_benchmark as full
        path = self.screen(); original = path.read_bytes()
        self.assertEqual(full.cli(['--cohort', str(path), '--suites', 'travel', 'banking', 'slack',
            '--baseline', '--attack', 'injecagent', '--name', 'full_subset',
            '--results-dir', str(self.root / 'runs')]), 0)
        base = self.root / 'runs/agentdojo/offline_full_subset'
        self.assertFalse((base / 'injecagent/workspace').exists())
        for name in ['travel', 'banking', 'slack']:
            data = json.loads((base / 'injecagent' / name / 'summary.json').read_text())
            self.assertEqual(data['task_scope'], 'screened')
            self.assertEqual(data['task_selection']['user_task_ids'], list(self.suites[name].user_tasks))
            self.assertEqual(data['task_selection']['injection_task_ids'], ['injection_task_1', 'injection_task_3', 'injection_task_4'])
        attachment = json.loads((base / 'screened_cohort.json').read_text())
        self.assertEqual(attachment['omitted_suites'], ['workspace'])
        self.assertEqual(attachment['counts']['travel']['planned_per_targeted_attack'], 12)
        self.assertEqual(path.read_bytes(), original)

    def test_defended_shadow_controls_and_partial_default_output_are_retained(self):
        path = self.screen()
        with patch.object(cohort, 'RESULTS_DIR', self.root / 'default_results'), patch.object(
            runner, 'make_defended_pipeline', side_effect=lambda *a, **kw: (*self.factory(), None)
        ) as factory:
            self.assertEqual(runner.cli(['--cohort', str(path), '--suites', 'travel', '--name', 'shadow',
                                         '--audit-router-mode', 'shadow', '--trace-level', 'full']), 0)
        self.assertEqual(factory.call_args.kwargs['audit_router_mode'], 'shadow')
        self.assertEqual(factory.call_args.kwargs['trace_level'], 'full')
        base = self.root / 'default_results/partial_benchmark/agentdojo/offline_shadow'
        self.assertTrue((base / 'attack_manifest.json').exists())
        self.assertEqual(json.loads((base / 'attack_manifest.json').read_text())['task_scope'], 'partial_screened')

    def test_old_source_hash_sets_do_not_block_matching_cohort(self):
        mapping = json.loads(Path(cohort.__file__).with_name('injection_cohort_compatibility.json').read_text())
        current = precheck._binding(self.config, ['travel'])
        for hashes in mapping['equivalent_source_sha256']:
            recorded = json.loads(json.dumps(current))
            recorded['source']['source_sha256'] = hashes
            self.assertTrue(cohort._bindings_compatible(recorded, current))
            recorded['source']['source_sha256'] = {**hashes, 'dscg/pipelines/baseline.py': '0' * 64}
            self.assertTrue(cohort._bindings_compatible(recorded, current))

    def test_reuse_keeps_screened_scope_and_frozen_bindings_for_both_entrypoints(self):
        from experiments import run_benchmark as full
        path = self.screen(); original = path.read_bytes()
        for entry, scope in [(runner.main, 'partial_screened'), (full.main, 'screened')]:
            options = dict(cohort_path=path, origin=True, suites=['travel', 'banking'],
                           attack='injecagent', run_name=scope, results_dir=self.root / 'runs')
            self.assertEqual(entry(**options), 0)
            base = self.root / 'runs' / ('agentdojo/offline_' + scope)
            bindings = {p: p.read_bytes() for p in base.rglob('*manifest.json') if p.name != 'attack_manifest.json'}
            self.assertEqual(entry(**{**options, 'suites': None, 'attack': None}, reuse=True), 0)
            self.assertEqual(json.loads((base / 'attack_manifest.json').read_text())['task_scope'], scope)
            self.assertEqual(json.loads((base / 'attack_manifest.json').read_text())['attacks'], ['injecagent'])
            for p, content in bindings.items(): self.assertEqual(p.read_bytes(), content)
        self.assertEqual(path.read_bytes(), original)

    def test_reuse_preserves_requested_and_active_suites_when_a_scene_is_empty(self):
        from experiments import run_benchmark as full
        self.suites['travel'].outcomes[1] = [False, False]
        self.suites['travel'].outcomes[3] = [False, False]
        self.suites['travel'].outcomes[4] = [False, False]
        path = self.screen(); original = path.read_bytes()
        for entry, name in [(runner.main, 'partial_empty'), (full.main, 'full_empty')]:
            options = dict(cohort_path=path, origin=True, suites=['travel', 'banking'],
                           attack='injecagent', run_name=name, results_dir=self.root / 'runs')
            self.assertEqual(entry(**options), 0)
            self.assertEqual(entry(**{**options, 'suites': None, 'attack': None}, reuse=True), 0)
            base = self.root / 'runs' / ('agentdojo/offline_' + name)
            self.assertEqual(json.loads((base / 'screened_run_manifest.json').read_text())['requested_suites'], ['travel', 'banking'])
            self.assertEqual(json.loads((base / 'attack_manifest.json').read_text())['suites'], ['banking'])
            self.assertFalse((base / 'injecagent/travel').exists())
        self.assertEqual(path.read_bytes(), original)


if __name__ == '__main__':
    unittest.main()


# Explicitly retain historical upstream suites as generic offline fixtures.
def setUpModule():
    global _fixture_backend
    from test_partial_agentdyn import legacy_fixture_backend
    _fixture_backend = legacy_fixture_backend(globals())


def tearDownModule():
    _fixture_backend.close()
