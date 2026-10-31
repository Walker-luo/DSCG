"""Strict exclusion-file and standalone screen regressions; no model calls."""
import copy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from experiments.common import injection_filter as fliter


class InjectionFilterTests(unittest.TestCase):
    def setUp(self):
        self.identity = {'id': 'agentdojo', 'suite_version': 'v1.2', 'revision': 'pypi:agentdojo==0.1.35'}
        self.data = {'schema_version': 'dscg.fliter.v1', 'benchmark': self.identity,
                     'excluded': {'banking': ['injection_task_1', 'injection_task_0']}}
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'fliter.json'
        for name, value in [('benchmark_identity', {**self.identity, 'repository': 'unused'}),
                            ('get_backend', SimpleNamespace(suites=('banking', 'slack')))]:
            p = patch.object(fliter, name, return_value=value)
            p.start()
            self.addCleanup(p.stop)
        p = patch.object(fliter, 'get_suite', return_value=SimpleNamespace(
            injection_tasks={'injection_task_0': object(), 'injection_task_1': object()}))
        p.start()
        self.addCleanup(p.stop)

    def load(self, value=None):
        self.path.write_text(json.dumps(self.data if value is None else value))
        return fliter.load_fliter(self.path)

    def test_minimal_header_canonical_digest_and_omitted_suite(self):
        data = self.load()
        self.assertEqual(data['benchmark'], self.identity)
        self.assertEqual(fliter.benchmark_header(), self.identity)
        self.assertEqual(fliter.excluded_ids(data, 'slack'), [])
        reordered = copy.deepcopy(data)
        reordered['excluded']['banking'].reverse()
        self.assertEqual(fliter.filter_digest(data), fliter.filter_digest(reordered))

    def test_invalid_shapes_identities_and_ids_rejected(self):
        mutations = [lambda d: d.update(schema_version='dscg.injection-screen.v2'),
                     lambda d: d.update(binding={}),
                     lambda d: d['benchmark'].update(id='agentdyn'),
                     lambda d: d['benchmark'].update(suite_version='v1.1'),
                     lambda d: d['benchmark'].update(revision='other'),
                     lambda d: d['excluded'].update(unknown=[]),
                     lambda d: d['excluded'].update(banking=['injection_task_99']),
                     lambda d: d['excluded'].update(banking=['injection_task_0'] * 2),
                     lambda d: d['excluded'].update(banking='injection_task_0'),
                     lambda d: d['excluded'].update(banking=[None])]
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                data = copy.deepcopy(self.data)
                mutate(data)
                with self.assertRaises(ValueError):
                    self.load(data)

    def test_duplicate_json_keys_rejected(self):
        self.path.write_text('{"schema_version":"dscg.fliter.v1","schema_version":"dscg.fliter.v1"}')
        with self.assertRaises(ValueError):
            fliter.load_fliter(self.path)

    def test_read_once(self):
        self.load()
        original = Path.read_text
        reads = []
        def read(path, *args, **kwargs):
            reads.append(path)
            return original(path, *args, **kwargs)
        with patch.object(Path, 'read_text', read):
            fliter.load_fliter(self.path)
        self.assertEqual(reads, [self.path])


class StandaloneScreenTests(unittest.TestCase):
    def test_removed_benchmark_compatibility_entrypoint(self):
        from experiments import run_injection_precheck as screen
        with self.assertRaises(SystemExit):
            screen.cli(['benchmark', '--cohort', 'old.json'])

    def test_non_qwen_config_rejected_before_baseline_factory(self):
        from experiments import run_injection_precheck as screen
        suite_name = screen.get_backend().suites[0]
        with tempfile.TemporaryDirectory() as temporary, \
                patch.object(screen, 'resolve_model_config', return_value=SimpleNamespace(model_id='other', provider='openai')), \
                patch.object(screen, 'make_openai_compatible_pipeline') as factory:
            with self.assertRaisesRegex(ValueError, 'qwen3.7-flash'):
                screen.screen(config_path=None, run_name='invalid', suites=[suite_name], results_dir=temporary)
            factory.assert_not_called()

    def test_minimal_output_fail_error_separate_resume_no_retry(self):
        from experiments import run_injection_precheck as screen
        from experiments.common import injection_cohort as helpers
        from dscg.model_config import ModelConfig
        identity = fliter.benchmark_header()
        from dscg.benchmark_catalog import get_backend
        suite_name = get_backend().suites[0]
        tasks = {f'injection_task_{i}': SimpleNamespace(ID=f'injection_task_{i}', GOAL=f'goal {i}') for i in range(3)}
        suite = SimpleNamespace(name=suite_name, injection_tasks=tasks, user_tasks={}, get_injection_task_by_id=tasks.__getitem__)
        config = ModelConfig('qwen3.7-flash', 'fake', 'https://example.invalid', 'dashscope', 'TEST_KEY')
        def attempt(directory, suite, task, config, binding):
            status = ['pass', 'fail', 'error'][int(task.ID[-1])]
            record = {'status': status, 'native_utility': {'pass': True, 'fail': False, 'error': None}[status],
                      'origin': 'offline-regression', 'total_tokens': None}
            helpers._write_new(directory / 'attempt.json', record)
            return record
        with tempfile.TemporaryDirectory() as temporary, \
                patch.object(screen, 'resolve_model_config', return_value=config), \
                patch.object(screen, 'get_suite', return_value=suite), \
                patch.object(helpers, 'get_suite', return_value=suite), \
                patch.object(screen, '_native_attempt', side_effect=attempt) as native:
            self.assertEqual(screen.screen(config_path=None, run_name='screen', suites=[suite_name], results_dir=temporary), 1)
            root = Path(temporary) / identity['id'] / 'qwen3.7-flash_screen'
            output = json.loads((root / 'fliter.json').read_text())
            self.assertEqual(set(output), {'schema_version', 'benchmark', 'excluded'})
            self.assertEqual(output['benchmark'], identity)
            self.assertEqual(output['excluded'][suite_name], ['injection_task_1', 'injection_task_2'])
            self.assertFalse((root / 'cohort.json').exists())
            self.assertIn('injection_task_2', (root / 'summary.md').read_text())
            self.assertEqual(screen.screen(config_path=None, run_name='screen', suites=[suite_name], results_dir=temporary), 1)
            self.assertEqual(native.call_count, 3)


if __name__ == '__main__':
    unittest.main()
