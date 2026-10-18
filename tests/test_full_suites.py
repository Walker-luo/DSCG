"""Full CLI suite subsets retain complete task catalogues; no model requests."""
from contextlib import ExitStack, redirect_stderr, redirect_stdout
from io import StringIO
import json
from pathlib import Path
from test_partial_agentdyn import TemporaryDirectory
import unittest
from unittest.mock import patch

from agentdojo.task_suite import get_suite
from experiments import run_benchmark as full
from experiments import run_partial_benchmark as runner
from test_full_benchmark import fake_pipeline, fake_attack, fake_results


class FullSuiteTests(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).resolve().parents[1] / 'workshop/artifacts/20261018_dual_benchmark/runner/test_runs'
        root.mkdir(parents=True, exist_ok=True)
        temp = TemporaryDirectory(dir=root); self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)

    def offline(self, stack):
        stack.enter_context(redirect_stdout(StringIO()))
        stack.enter_context(patch.object(runner, 'make_openai_compatible_pipeline', side_effect=fake_pipeline))
        stack.enter_context(patch.object(runner.attacks, 'load_attack', side_effect=fake_attack))
        stack.enter_context(patch.object(runner.benchmark, 'benchmark_suite_with_injections', side_effect=fake_results))
        stack.enter_context(patch.object(runner.benchmark, 'benchmark_suite_without_injections',
            side_effect=lambda *a, **kw: {'utility_results': {(u,): True for u in kw['user_tasks']}}))

    def test_selected_suites_run_all_registered_tasks_and_bind_the_whole_selection(self):
        with ExitStack() as stack:
            self.offline(stack)
            self.assertEqual(full.cli(['--baseline', '--suites', 'travel', 'banking', 'slack',
                '--attack', 'injecagent', '--name', 'subset', '--results-dir', str(self.root)]), 0)
            base = self.root / 'offline-model_agentdojo_subset'
            self.assertFalse((base / 'injecagent/workspace').exists())
            manifest = json.loads((base / 'attack_manifest.json').read_text())
            self.assertEqual(manifest['suites'], ['travel', 'banking', 'slack'])
            self.assertEqual(manifest['suite_scope'], 'selected')
            self.assertEqual(manifest['task_scope'], 'full')
            for name in ['travel', 'banking', 'slack']:
                data = json.loads((base / 'injecagent' / name / 'summary.json').read_text())
                suite = get_suite('v1.2', name)
                self.assertEqual(data['task_selection']['user_task_ids'], list(suite.user_tasks))
                self.assertEqual(data['task_selection']['injection_task_ids'], list(suite.injection_tasks))
                self.assertEqual(data['suite_scope'], 'selected')
            self.assertIn('所选场景全任务', (base / 'summary.md').read_text())
            before = {p: p.read_bytes() for p in base.rglob('*') if p.is_file()}
            self.assertEqual(full.cli(['--baseline', '--suites', 'workspace', '--force-rerun',
                '--attack', 'injecagent', '--name', 'subset', '--results-dir', str(self.root)]), 1)
            self.assertEqual({p: p.read_bytes() for p in base.rglob('*') if p.is_file()}, before)

    def test_clean_runs_all_users_in_selected_suites(self):
        with ExitStack() as stack:
            self.offline(stack)
            self.assertEqual(full.cli(['--baseline', '--clean', '--suites', 'banking',
                '--name', 'clean', '--results-dir', str(self.root)]), 0)
            base = self.root / 'offline-model_agentdojo_clean/none'
            self.assertEqual([p.name for p in base.iterdir() if p.is_dir()], ['banking'])
            summary = json.loads((base / 'banking/summary.json').read_text())
            self.assertEqual(summary['task_selection']['user_task_ids'], list(get_suite('v1.2', 'banking').user_tasks))

    def test_export_has_only_requested_suites_but_all_their_ids(self):
        with redirect_stdout(StringIO()):
            path = self.root / 'full.json'
            self.assertEqual(full.cli(['--suites', 'travel', 'banking', 'slack', '--write-task-manifest', str(path)]), 0)
            manifest = json.loads(path.read_text())
            self.assertEqual(list(manifest['suites']), ['travel', 'banking', 'slack'])
            for name, tasks in manifest['suites'].items():
                self.assertEqual(tasks['user_task_ids'], list(get_suite('v1.2', name).user_tasks))
                self.assertEqual(tasks['injection_task_ids'], list(get_suite('v1.2', name).injection_tasks))

    def test_invalid_empty_or_duplicate_suite_flags_reject_before_execution(self):
        for names in [[], ['worksapce'], ['travel', 'travel']]:
            with self.subTest(names=names), redirect_stderr(StringIO()), self.assertRaises(SystemExit):
                full.cli(['--suites', *names])


if __name__ == '__main__':
    unittest.main()


# Explicitly retain historical upstream suites as generic offline fixtures.
def setUpModule():
    global _fixture_backend
    from test_partial_agentdyn import legacy_fixture_backend
    _fixture_backend = legacy_fixture_backend(globals())


def tearDownModule():
    _fixture_backend.close()
