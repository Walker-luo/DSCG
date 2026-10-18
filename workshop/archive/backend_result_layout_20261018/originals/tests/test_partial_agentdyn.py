"""AgentDyn namespace/provenance boundaries; no model or fork dependency."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory as _TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from experiments import run_partial_benchmark as runner
from experiments.common import partial_controls as controls, benchmark_reuse as reuse
from experiments.common import injection_cohort as cohort

IDENTITY = {'id': 'agentdyn', 'repository': 'https://github.com/SaFo-Lab/AgentDyn',
            'revision': 'a' * 40, 'suite_version': 'v1.2',
            'implementation_sha256': 'b' * 64, 'catalog_sha256': 'c' * 64}


def TemporaryDirectory(*args, **kwargs):
    """Keep generated offline fixtures within this task's artifact root."""
    root = Path(__file__).resolve().parents[1] / 'workshop/artifacts/20261018_dual_benchmark/runner/test_runs'
    root.mkdir(parents=True, exist_ok=True)
    kwargs.setdefault('dir', root)
    return _TemporaryDirectory(*args, **kwargs)


DOJO_IDENTITY = {**IDENTITY, 'id': 'agentdojo', 'repository': 'https://github.com/ethz-spylab/agentdojo',
                 'revision': 'e' * 40, 'implementation_sha256': 'f' * 64, 'catalog_sha256': 'd' * 64}


def profile(identity):
    suites = ('shopping', 'github', 'dailylife') if identity['id'] == 'agentdyn' else ('workspace', 'travel', 'banking', 'slack')
    return SimpleNamespace(id=identity['id'], label='AgentDyn' if identity['id'] == 'agentdyn' else 'AgentDojo',
                           suites=suites, suite_version='v1.2', repository=identity['repository'],
                           tool_metadata_path=Path('config/tools.' + identity['id'] + '-v1.2.toml'))


class DualBackendRunnerContracts(unittest.TestCase):
    def test_run_namespace_changes_at_call_time_without_reimport(self):
        for identity in (DOJO_IDENTITY, IDENTITY):
            with self.subTest(backend=identity['id']), patch.object(runner, 'get_backend', create=True, return_value=profile(identity)):
                pipeline = SimpleNamespace(name='native')
                self.assertEqual(runner._apply_run_name(pipeline, 'model/id', 'run'), f"model-id_{identity['id']}_run")
                pipeline.name = 'native'
                self.assertEqual(runner._apply_run_name(pipeline, 'model/id', None), f"native_{identity['id']}")

    def test_exports_resolve_runtime_catalog_without_reimport(self):
        suite = SimpleNamespace(user_tasks=dict.fromkeys(['u0', 'u1', 'u2', 'u3']), injection_tasks=dict.fromkeys(['i0', 'i1', 'i2', 'i3']))
        for identity in (DOJO_IDENTITY, IDENTITY):
            with self.subTest(backend=identity['id']), patch.object(controls, 'get_backend', create=True, return_value=profile(identity)), \
                    patch.object(controls, 'get_suites', create=True, return_value=profile(identity).suites), \
                    patch.object(controls, 'benchmark_identity', return_value=identity), patch.object(controls, 'get_suite', return_value=suite):
                for scope, size in (('full', 4), ('partial', 3)):
                    manifest = controls.make_task_manifest(scope)
                    self.assertEqual(tuple(manifest['suites']), profile(identity).suites)
                    self.assertEqual(manifest['benchmark'], identity)
                    self.assertTrue(all(len(entry['user_task_ids']) == size for entry in manifest['suites'].values()))

    def test_same_agentdojo_source_is_accepted_only_in_that_backend(self):
        source = {'agentdojo': '0.1.35', 'python': '3.10', 'source_sha256': {'x': 'same'}, 'benchmark': DOJO_IDENTITY}
        for module, function in ((reuse, reuse.compatible_source), (cohort, cohort._source_compatible)):
            with patch.object(module, 'benchmark_identity', return_value=DOJO_IDENTITY):
                self.assertTrue(function(source, source))
            with patch.object(module, 'benchmark_identity', return_value=IDENTITY):
                self.assertFalse(function(source, source))

    def test_help_does_not_require_a_supported_backend(self):
        from contextlib import redirect_stdout
        from io import StringIO
        from experiments import run_benchmark, run_injection_precheck
        for module, entry, args in ((runner, runner.cli, ['--help']), (run_benchmark, run_benchmark.cli, ['--help']),
                                    (run_injection_precheck, run_injection_precheck.cli, ['screen', '--help'])):
            with self.subTest(module=module.__name__), patch.object(module, 'get_backend', create=True, side_effect=ValueError('unsupported')), redirect_stdout(StringIO()):
                with self.assertRaises(SystemExit) as result: entry(args)
                self.assertEqual(result.exception.code, 0)


class InstalledBackendRunnerTests(unittest.TestCase):
    def test_actual_cli_exports_current_backend_scope_without_models(self):
        from contextlib import redirect_stdout
        from io import StringIO
        from dscg.benchmark_catalog import get_backend, benchmark_identity, get_suite
        from experiments import run_benchmark as full
        backend = get_backend()
        expected = {'agentdojo': ('workspace', 'travel', 'banking', 'slack'),
                    'agentdyn': ('shopping', 'github', 'dailylife')}
        self.assertEqual(backend.suites, expected[backend.id])
        with TemporaryDirectory() as root, redirect_stdout(StringIO()), patch.object(runner, 'make_defended_pipeline') as defended, patch.object(runner, 'make_openai_compatible_pipeline') as baseline:
            for entry, size in ((runner.cli, 3), (full.cli, None)):
                path = Path(root) / ('partial.json' if size else 'full.json')
                self.assertEqual(entry(['--write-task-manifest', str(path)]), 0)
                manifest = json.loads(path.read_text())
                self.assertEqual(manifest['benchmark'], benchmark_identity())
                self.assertEqual(tuple(manifest['suites']), expected[backend.id])
                for name, entry in manifest['suites'].items():
                    suite = get_suite('v1.2', name)
                    self.assertEqual(entry['user_task_ids'], list(suite.user_tasks)[:size])
                    self.assertEqual(entry['injection_task_ids'], list(suite.injection_tasks)[:size])
            defended.assert_not_called(); baseline.assert_not_called()


class AgentDynRunnerContracts(unittest.TestCase):
    def setUp(self):
        stack = fixture_backend(IDENTITY)
        self.addCleanup(stack.close)

    def test_only_agentdyn_suites_are_selectable(self):
        self.assertEqual(controls.get_suites(), ('shopping', 'github', 'dailylife'))

    def test_explicit_and_default_names_are_namespaced(self):
        pipeline = SimpleNamespace(name='native-model')
        self.assertEqual(runner._apply_run_name(pipeline, 'model/id', 'trial'), 'model-id_agentdyn_trial')
        pipeline.name = 'native-model'
        self.assertEqual(runner._apply_run_name(pipeline, 'model/id', None), 'native-model_agentdyn')

    def test_backend_rejected_before_model_or_output_creation(self):
        with patch.object(runner, 'get_backend', create=True, side_effect=ValueError('wrong fork')), \
                patch.object(runner, 'make_openai_compatible_pipeline') as factory, TemporaryDirectory() as root:
            with self.assertRaisesRegex(ValueError, 'wrong fork'):
                runner.main(origin=True, results_dir=root, run_name='blocked')
            factory.assert_not_called()
            self.assertEqual(list(Path(root).iterdir()), [])

    def test_old_sources_are_rejected_even_when_package_and_hashes_match(self):
        old = {'agentdojo': '0.1.35', 'python': '3.10', 'source_sha256': {'x': 'same'}}
        current = {**old, 'benchmark': IDENTITY}
        self.assertFalse(reuse.compatible_source(old, current))
        self.assertFalse(cohort._source_compatible(old, current))
        self.assertFalse(reuse.compatible_source(old, old))
        self.assertFalse(cohort._source_compatible(old, old))

    def test_same_agentdyn_identity_allows_identical_sources(self):
        source = {'agentdojo': '0.1.35', 'python': '3.10', 'source_sha256': {'x': 'same'}, 'benchmark': IDENTITY}
        self.assertTrue(reuse.compatible_source(source, source))
        self.assertTrue(cohort._source_compatible(source, source))
        self.assertFalse(reuse.compatible_source(source, {**source, 'benchmark': {**IDENTITY, 'revision': 'd' * 40}}))

    def test_export_and_plan_have_required_identity(self):
        suite = SimpleNamespace(user_tasks={'u0': None, 'u1': None, 'u2': None, 'u3': None},
                                injection_tasks={'i0': None, 'i1': None, 'i2': None, 'i3': None})
        with patch.object(controls, 'benchmark_identity', create=True, return_value=IDENTITY), \
                patch.object(reuse, 'benchmark_identity', create=True, return_value=IDENTITY), \
                patch.object(controls, 'get_suite', return_value=suite):
            for scope in ('partial', 'full'):
                manifest = controls.make_task_manifest(scope)
                self.assertEqual(manifest['benchmark'], IDENTITY)
                self.assertTrue(manifest['schema_version'].endswith('.v2'))
            self.assertEqual(reuse.execution_plan('partial', ['shopping'], ['none'])['benchmark'], IDENTITY)

    def test_foreign_task_manifest_rejected_without_modification(self):
        with TemporaryDirectory() as root, patch.object(controls, 'benchmark_identity', create=True, return_value=IDENTITY):
            path = Path(root) / 'manifest.json'
            raw = json.dumps({'schema_version': 'dscg.partial-tasks.v1', 'suite_version': 'v1.2', 'suites': {}})
            path.write_text(raw)
            with self.assertRaises(ValueError): controls.load_task_manifest(path)
            self.assertEqual(path.read_text(), raw)


class AgentDynOfflineExecution(unittest.TestCase):
    def setUp(self):
        stack = fixture_backend(IDENTITY)
        self.addCleanup(stack.close)
        description = SimpleNamespace(name='provider/model', dscg_model_config={'model_id': 'provider/model'},
                                      dscg_security_model_config={}, dscg_optimization_config={})
        patcher = patch.object(runner, '_describe_pipeline', return_value=description)
        patcher.start(); self.addCleanup(patcher.stop)
        self.suite = SimpleNamespace(user_tasks={f'user_task_{i}': None for i in range(4)},
                                     injection_tasks={f'injection_task_{i}': None for i in range(4)})
        patcher = patch.object(runner, 'get_suite', return_value=self.suite)
        patcher.start(); self.addCleanup(patcher.stop)
        patcher = patch.object(controls, 'get_suite', return_value=self.suite)
        patcher.start(); self.addCleanup(patcher.stop)

    def test_defended_metadata_preflight_rejects_before_model_creation(self):
        from dscg.tool_metadata import ToolMetadataError
        with TemporaryDirectory() as root, patch.object(runner, 'validate_benchmark_tool_metadata', create=True,
                side_effect=ToolMetadataError('missing classification')), patch.object(runner, 'make_defended_pipeline') as factory:
            with self.assertRaisesRegex(ToolMetadataError, 'missing classification'):
                runner.main(run_attack=False, results_dir=root, run_name='metadata')
            factory.assert_not_called()
            self.assertEqual(list(Path(root).iterdir()), [])

    def test_resolved_metadata_selection_is_reported_and_bound(self):
        from contextlib import redirect_stdout
        from io import StringIO
        record = {'path': '/fixture/catalog.toml', 'source': 'builtin', 'backend_id': 'agentdyn',
                  'catalog_backend_id': 'agentdyn', 'warning': 'fixture skipped old generic catalog'}
        selection = SimpleNamespace(path=Path(record['path']), public_dict=lambda: record)
        def results(*args, **kwargs):
            return {'utility_results': {(u, None): True for u in kwargs['user_tasks']}}
        with TemporaryDirectory() as root, redirect_stdout(StringIO()) as output, patch.object(runner, 'resolve_tool_metadata', create=True, return_value=selection), \
                patch.object(runner, 'load_tool_metadata', return_value={}), \
                patch.object(runner, 'make_defended_pipeline', side_effect=lambda *a, **k: (*self.factory(), None)), \
                patch.object(runner.benchmark, 'benchmark_suite_without_injections', side_effect=results):
            self.assertEqual(runner.main(run_attack=False, results_dir=root, run_name='metadata', suites=['shopping']), 0)
            summary = json.loads((Path(root) / 'provider-model_agentdyn_metadata/none/shopping/summary.json').read_text())
            self.assertEqual(summary['run_manifest'].get('tool_metadata_selection'), record)
            self.assertEqual(summary.get('tool_metadata_selection'), record)
            self.assertIn(record['path'], output.getvalue())
            self.assertIn(record['warning'], output.getvalue())

    def factory(self, *args, **kwargs):
        return SimpleNamespace(name='provider/model', dscg_model_config={'model_id': 'provider/model'}), SimpleNamespace(
            total_prompt_tokens=0, total_completion_tokens=0, get_total_tokens=lambda: 0)

    def test_full_partial_clean_and_typical_keep_native_results_and_identity(self):
        from contextlib import redirect_stdout
        from io import StringIO
        from experiments import run_benchmark as full
        root = Path(__file__).resolve().parents[1] / 'workshop/artifacts/20261018_dual_benchmark/runner/test_runs'
        root.mkdir(parents=True, exist_ok=True)
        def results(pipeline, suite, *args, **kwargs):
            keys = [(u, i) for u in kwargs['user_tasks'] for i in kwargs.get('injection_tasks', [None])]
            return {'utility_results': {k: n != 0 for n, k in enumerate(keys)},
                    'security_results': {k: n == 0 for n, k in enumerate(keys)}}
        with TemporaryDirectory(dir=root) as directory, redirect_stdout(StringIO()), \
                patch.object(runner, 'make_openai_compatible_pipeline', side_effect=self.factory), \
                patch.object(runner.attacks, 'load_attack', side_effect=lambda name, *a: SimpleNamespace(name=name, is_dos_attack=False)), \
                patch.object(runner.benchmark, 'benchmark_suite_with_injections', side_effect=results), \
                patch.object(runner.benchmark, 'benchmark_suite_without_injections', side_effect=results):
            for identity in (DOJO_IDENTITY, IDENTITY):
                with fixture_backend(identity):
                    for entry, scope, size in ((runner.main, 'partial', 3), (full.main, 'full', 4)):
                        for attacked in (False, True):
                            name = f'{scope}_{attacked}'
                            self.assertEqual(entry(origin=True, run_attack=attacked, run_name=name, results_dir=directory), 0)
                            base = Path(directory) / ('provider-model_' + identity['id'] + '_' + name)
                            manifest = json.loads((base / 'attack_manifest.json').read_text())
                            self.assertEqual(manifest['benchmark'], identity)
                            self.assertEqual(manifest['suites'], list(profile(identity).suites))
                            self.assertEqual(manifest['attacks'], list(runner.TYPICAL_ATTACKS) if attacked else [])
                            for summary_path in base.glob('*/*/summary.json'):
                                summary = json.loads(summary_path.read_text())
                                self.assertEqual(summary['benchmark'], identity)
                                self.assertEqual(summary['run_manifest']['benchmark'], identity)
                                self.assertEqual(summary['run_manifest']['source']['benchmark'], identity)
                                self.assertEqual(summary['task_counts']['planned_tasks'], size * size if attacked else size)
                                self.assertEqual(summary['task_counts']['utility_passed'], (size * size if attacked else size) - 1)
                                self.assertEqual(summary['metrics']['attack_success_rate'], 1 / (size * size) if attacked else None)
                            plan = json.loads((base / 'benchmark_plan.json').read_text())
                            self.assertEqual(plan['benchmark'], identity)
                            self.assertEqual(plan['schema_version'], 'dscg.benchmark-plan.v2')


def fixture_backend(identity=DOJO_IDENTITY, *, native_legacy=False):
    """Explicit synthetic profile for generic bookkeeping tests, never efficacy."""
    from contextlib import ExitStack
    from agentdojo.task_suite import get_suite
    from experiments import run_benchmark, run_injection_precheck
    from experiments.common import partial_reporting
    stack = ExitStack()
    backend = profile(identity)
    for module in (runner, controls, cohort, reuse, run_benchmark, run_injection_precheck, partial_reporting):
        if hasattr(module, 'get_backend'): stack.enter_context(patch.object(module, 'get_backend', return_value=backend))
        if hasattr(module, 'get_suites'): stack.enter_context(patch.object(module, 'get_suites', return_value=backend.suites))
        if native_legacy and hasattr(module, 'get_suite'):
            stack.enter_context(patch.object(module, 'get_suite', side_effect=get_suite))
        if hasattr(module, 'benchmark_identity'): stack.enter_context(patch.object(module, 'benchmark_identity', return_value=identity))
        if hasattr(module, 'validate_backend'): stack.enter_context(patch.object(module, 'validate_backend', return_value=identity))
        if hasattr(module, 'validate_benchmark_tool_metadata'):
            stack.enter_context(patch.object(module, 'validate_benchmark_tool_metadata', return_value={}))
    return stack


def legacy_fixture_backend(namespace, model="offline-model"):
    """Exercise historical generic native tasks with a synthetic AgentDojo profile.

    AgentDyn still ships the old suites, allowing the same generic logging and
    scoring regression in either environment. This identity is explicitly a test
    fixture, never a certification of the executing package as another backend.
    """
    suites = profile(DOJO_IDENTITY).suites
    if 'SUITES' in namespace and namespace['SUITES'] != list(suites): namespace['SUITES'] = suites
    stack = fixture_backend(DOJO_IDENTITY, native_legacy=True)
    if 'serial_fixture' not in namespace:
        stack.enter_context(patch.object(runner, '_describe_pipeline', side_effect=lambda *a, **k:
            SimpleNamespace(name=a[0] or model, dscg_model_config={'model_id': a[0] or model},
                            dscg_security_model_config={}, dscg_optimization_config={})))
    return stack
