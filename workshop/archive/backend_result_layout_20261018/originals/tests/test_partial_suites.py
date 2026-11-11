"""Offline suite selection: CLI scope, scored denominators, and cache identity."""
from contextlib import ExitStack, redirect_stderr, redirect_stdout
from io import StringIO
import json
from pathlib import Path
from test_partial_agentdyn import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from agentdojo.task_suite import get_suite
from experiments import run_partial_benchmark as runner


class PartialSuiteTests(unittest.TestCase):
    def setUp(self):
        self.artifacts = Path(__file__).resolve().parents[1] / 'workshop/artifacts/20261018_dual_benchmark/runner/test_runs'
        self.artifacts.mkdir(parents=True, exist_ok=True)

    def offline(self, stack):
        pipeline = lambda *a, **kw: (
            SimpleNamespace(name='offline', dscg_model_config={'model_id': 'offline'}),
            SimpleNamespace(total_prompt_tokens=0, total_completion_tokens=0, get_total_tokens=lambda: 0),
        )
        stack.enter_context(patch.object(runner, 'make_openai_compatible_pipeline', side_effect=pipeline))
        stack.enter_context(patch.object(runner.attacks, 'load_attack',
                                        return_value=SimpleNamespace(is_dos_attack=False)))
        def results(*a, **kw):
            keys = [(u, i) for u in kw['user_tasks'] for i in kw['injection_tasks']]
            return {'utility_results': dict.fromkeys(keys, True),
                    'security_results': dict.fromkeys(keys, False)}
        stack.enter_context(patch.object(runner.benchmark, 'benchmark_suite_with_injections', side_effect=results))
        stack.enter_context(patch.object(runner.benchmark, 'benchmark_suite_without_injections',
            side_effect=lambda *a, **kw: {'utility_results': dict.fromkeys(kw['user_tasks'], True)}))
        stack.enter_context(redirect_stdout(StringIO()))

    def test_three_suite_cli_scores_only_selected_prefixes_and_binds_selection(self):
        with TemporaryDirectory(dir=self.artifacts) as directory, ExitStack() as stack:
            self.offline(stack)
            options = ['--baseline', '--name', 'three', '--results-dir', directory,
                       '--suites', 'travel', 'banking', 'slack']
            self.assertEqual(runner.cli(options), 0)
            base = Path(directory) / 'offline_agentdojo_three'
            manifest = json.loads((base / 'attack_manifest.json').read_text())
            self.assertEqual(manifest['suites'], ['travel', 'banking', 'slack'])
            self.assertEqual(manifest['task_scope'], 'partial')
            total = 0
            for attack in ['ignore_previous', 'important_instructions', 'tool_knowledge']:
                self.assertFalse((base / attack / 'workspace').exists())
                for name in ['travel', 'banking', 'slack']:
                    summary = json.loads((base / attack / name / 'summary.json').read_text())
                    suite = get_suite('v1.2', name)
                    self.assertEqual(summary['task_selection']['user_task_ids'], list(suite.user_tasks)[:3])
                    self.assertEqual(summary['task_selection']['injection_task_ids'], list(suite.injection_tasks)[:3])
                    total += summary['task_counts']['total_tasks']
            self.assertEqual(total, 81)
            original = {p: p.read_bytes() for p in base.rglob('*') if p.is_file()}
            self.assertEqual(runner.cli(['--baseline', '--force-rerun', '--name', 'three',
                                        '--results-dir', directory, '--suites', 'workspace']), 1)
            self.assertEqual({p: p.read_bytes() for p in base.rglob('*') if p.is_file()}, original)

    def test_clean_uses_only_selected_users(self):
        with TemporaryDirectory(dir=self.artifacts) as directory, ExitStack() as stack:
            self.offline(stack)
            self.assertEqual(runner.cli(['--baseline', '--clean', '--suites', 'travel', 'banking', 'slack',
                                         '--name', 'clean', '--results-dir', directory]), 0)
            base = Path(directory) / 'offline_agentdojo_clean/none'
            self.assertFalse((base / 'workspace').exists())
            self.assertEqual(sum(json.loads((base / name / 'summary.json').read_text())['task_counts']['total_tasks']
                                 for name in ['travel', 'banking', 'slack']), 9)

    def test_offline_export_matches_selected_suites(self):
        with TemporaryDirectory(dir=self.artifacts) as directory, redirect_stdout(StringIO()):
            path = Path(directory) / 'tasks.json'
            self.assertEqual(runner.cli(['--suites', 'travel', 'banking', 'slack',
                                         '--write-task-manifest', str(path)]), 0)
            self.assertEqual(list(json.loads(path.read_text())['suites']), ['travel', 'banking', 'slack'])

    def test_invalid_empty_or_duplicate_suites_are_rejected(self):
        for names in [[], ['worksapce'], ['travel', 'travel']]:
            with self.subTest(names=names), TemporaryDirectory(dir=self.artifacts) as directory, redirect_stdout(StringIO()), patch.object(
                runner, '_run_single_attack', side_effect=AssertionError('invalid selection reached execution')
            ), self.assertRaises(ValueError):
                runner.main(suites=names, results_dir=directory)
        with redirect_stderr(StringIO()), self.assertRaises(SystemExit):
            runner.cli(['--suites', 'worksapce'])


if __name__ == '__main__':
    unittest.main()


# Explicitly retain historical upstream suites as generic offline fixtures.
def setUpModule():
    global _fixture_backend
    from test_partial_agentdyn import legacy_fixture_backend
    _fixture_backend = legacy_fixture_backend(globals(), model="offline")


def tearDownModule():
    _fixture_backend.close()
