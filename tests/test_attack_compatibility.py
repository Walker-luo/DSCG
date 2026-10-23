"""Native attack compatibility checks; no remote model requests."""

import json
import queue
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from dscg.benchmark_catalog import get_backend, get_suite
from experiments import run_partial_benchmark as partial
from experiments.common.attack_compatibility import check_attack_compatibility
import serial_fixture
from dashboard import evaluation
from dashboard.app import run_queues, runs_store, run_test_thread


ARTIFACTS = Path(__file__).resolve().parents[1] / 'workshop/artifacts/20261020_agentdyn_tool_knowledge'


@unittest.skipUnless(get_backend().id == 'agentdyn', 'AgentDyn native fixture')
class AgentDynToolKnowledgeCompatibilityTests(unittest.TestCase):
    def test_native_failure_and_exact_affected_target_set(self):
        from agentdojo.attacks.important_instructions_attacks import ToolKnowledgeAttack
        suite = get_suite('v1.2', 'dailylife')
        task = next(iter(suite.injection_tasks.values()))
        with self.assertRaises(ValueError):
            ToolKnowledgeAttack.get_tools_sequence.__wrapped__(
                type('AttackStub', (), {'task_suite': suite})(), task)
        issue = check_attack_compatibility(suite, 'tool_knowledge',
                                           list(suite.user_tasks), list(suite.injection_tasks))
        self.assertEqual(issue['reason_code'], 'missing_placeholder_args')
        self.assertEqual(issue['injection_task_ids'], list(suite.injection_tasks))
        self.assertEqual(issue['planned_pairs'], 200)
        for name in ('shopping', 'github'):
            other = get_suite('v1.2', name)
            self.assertIsNone(check_attack_compatibility(other, 'tool_knowledge',
                              list(other.user_tasks), list(other.injection_tasks)))
        self.assertIsNone(check_attack_compatibility(suite, 'important_instructions',
                          list(suite.user_tasks), list(suite.injection_tasks)))

    def test_skip_precedes_model_for_normal_progress_and_full(self):
        ARTIFACTS.mkdir(parents=True, exist_ok=True)
        for progress, task_scope in ((False, 'partial'), (True, 'partial'), (False, 'full')):
            with self.subTest(progress=progress, task_scope=task_scope), \
                    TemporaryDirectory(dir=ARTIFACTS) as temp, \
                    serial_fixture.patched(), redirect_stdout(StringIO()) as output, \
                    patch.object(partial, 'make_openai_compatible_pipeline') as model:
                status = partial.main(origin=True, suites=['dailylife'], attack='tool_knowledge',
                                      results_dir=temp, run_name='unsupported', progress=progress,
                                      task_scope=task_scope)
                self.assertEqual(status, 1)
                model.assert_not_called()
                self.assertIn('unsupported', output.getvalue())
                base = Path(temp) / 'agentdyn/offline-model_unsupported'
                execution = json.loads(next((base / 'execution').glob('*/execution.json')).read_text())
                group = execution['groups'][0]
                self.assertEqual(group['status'], 'unsupported')
                self.assertEqual(group['reason_code'], 'missing_placeholder_args')
                self.assertEqual(group['planned_pairs'], 9 if task_scope == 'partial' else 200)
                summary = (base / 'summary.md').read_text()
                self.assertIn(f"0/{group['planned_pairs']}", summary)
                self.assertIn('N/A', summary)
                self.assertFalse(list(base.glob('tool_knowledge/dailylife/*/*/*.json')))

    def test_mixed_run_completes_other_suite_and_reuse_preserves_skip(self):
        ARTIFACTS.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(dir=ARTIFACTS) as temp, serial_fixture.patched(), redirect_stdout(StringIO()):
            options = dict(origin=True, suites=['shopping', 'dailylife'], attack='tool_knowledge',
                           results_dir=temp, run_name='mixed')
            self.assertEqual(partial.main(**options), 0)
            base = Path(temp) / 'agentdyn/offline-model_mixed'
            trace = next(base.glob('tool_knowledge/shopping/*/*/*.json'))
            original = trace.read_bytes()
            self.assertEqual(partial.main(**options, reuse=True), 0)
            self.assertEqual(trace.read_bytes(), original)
            self.assertEqual(len(list((base / 'reuse').glob('*/compatibility.json'))), 1)

    def test_unexpected_reference_error_is_execution_error(self):
        ARTIFACTS.mkdir(parents=True, exist_ok=True)
        suite = get_suite('v1.2', 'dailylife')
        target = next(iter(suite.injection_tasks.values()))
        with TemporaryDirectory(dir=ARTIFACTS) as temp, serial_fixture.patched(), \
                redirect_stdout(StringIO()), \
                patch.object(type(target), 'ground_truth', side_effect=RuntimeError('secret-content')):
            self.assertEqual(partial.main(origin=True, suites=['dailylife'],
                             attack='tool_knowledge', results_dir=temp, run_name='unexpected'), 1)
            base = Path(temp) / 'agentdyn/offline-model_unexpected'
            group = json.loads(next((base / 'execution').glob('*/execution.json')).read_text())['groups'][0]
            self.assertEqual(group['status'], 'error')
            self.assertEqual(group['execution_error']['stage'], 'attack_compatibility')
            self.assertEqual(group['execution_error']['task_id'], 'injection_task_0')
            self.assertNotIn('secret-content', (base / 'failure_cases.jsonl').read_text())

    def test_dashboard_all_unsupported_is_non_success_without_model(self):
        ARTIFACTS.mkdir(parents=True, exist_ok=True)
        config = evaluation.normalize_config({'suites': ['dailylife'], 'origin': True,
                  'run_attack': True, 'attack_name': 'tool_knowledge',
                  'max_user_tasks': 1, 'max_injection_tasks': 1})
        with TemporaryDirectory(dir=ARTIFACTS) as temp, \
                patch('dashboard.app.DASHBOARD_RESULTS_DIR', Path(temp)), \
                patch('dashboard.app.make_openai_compatible_pipeline') as model, \
                patch('dashboard.app.threading.Thread'):
            run_queues['unsupported-test'] = queue.Queue()
            try:
                run_test_thread('unsupported-test', config)
                model.assert_not_called()
                saved = json.loads((Path(temp)/'unsupported-test/overall_results.json').read_text())
                self.assertEqual(saved['status'], 'unsupported')
                self.assertEqual(saved['aggregate_metrics'], {})
                self.assertEqual(saved['unsupported_suites'][0]['reason_code'], 'missing_placeholder_args')
                self.assertIn('0/1', (Path(temp)/'unsupported-test/summary.md').read_text())
                done = [item for item in list(run_queues['unsupported-test'].queue) if item['type'] == 'done']
                self.assertEqual(done[-1]['summary']['error'], 'all_selected_groups_unsupported')
            finally:
                runs_store.pop('unsupported-test', None)
                run_queues.pop('unsupported-test', None)

    def test_dashboard_mixed_aggregate_excludes_unsupported_suite(self):
        ARTIFACTS.mkdir(parents=True, exist_ok=True)
        config = evaluation.normalize_config({'suites': ['shopping', 'dailylife'], 'origin': True,
                  'run_attack': True, 'attack_name': 'tool_knowledge',
                  'max_user_tasks': 1, 'max_injection_tasks': 1})
        def native(_pipeline, _suite, _attack, _root, **options):
            key = (options['user_tasks'][0], options['injection_tasks'][0])
            return {'utility_results': {key: True}, 'security_results': {key: False}}
        with TemporaryDirectory(dir=ARTIFACTS) as temp, \
                patch('dashboard.app.DASHBOARD_RESULTS_DIR', Path(temp)), \
                patch('dashboard.app.make_openai_compatible_pipeline', side_effect=serial_fixture.baseline) as model, \
                patch('dashboard.app.attacks.load_attack', side_effect=serial_fixture.attack), \
                patch('dashboard.app.benchmark.benchmark_suite_with_injections', side_effect=native) as scored, \
                patch('dashboard.app.threading.Thread'):
            try:
                run_test_thread('mixed-dashboard-test', config)
                saved = json.loads((Path(temp)/'mixed-dashboard-test/overall_results.json').read_text())
                self.assertEqual(saved['status'], 'completed')
                self.assertEqual(saved['num_suites'], 1)
                self.assertEqual(saved['total_tasks'], 1)
                self.assertEqual(saved['unsupported_suites'][0]['suite'], 'dailylife')
                self.assertEqual(model.call_count, 1)
                self.assertEqual(scored.call_count, 1)
                self.assertIn('unsupported', (Path(temp)/'mixed-dashboard-test/summary.md').read_text())
            finally:
                runs_store.pop('mixed-dashboard-test', None)

    def test_screened_cohort_checks_only_retained_targets(self):
        from experiments import run_injection_precheck as precheck
        from experiments.common import injection_cohort as cohorts
        ARTIFACTS.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(dir=ARTIFACTS) as temp, redirect_stdout(StringIO()), \
                serial_fixture.patched(), \
                patch.object(precheck, 'resolve_model_config', return_value=serial_fixture.MAIN), \
                patch.object(precheck, 'make_openai_compatible_pipeline', side_effect=serial_fixture.baseline):
            self.assertEqual(precheck.screen(config_path=None, run_name='cohort-screen',
                             suites=['dailylife'], results_dir=temp), 0)
            cohort = Path(temp) / 'agentdyn/offline-model_cohort-screen/cohort.json'
            with patch.object(cohorts, 'resolve_model_config', side_effect=serial_fixture.resolve), \
                    patch.object(partial, 'make_openai_compatible_pipeline') as model:
                self.assertEqual(partial.main(cohort_path=cohort, suites=['dailylife'],
                                 origin=True, results_dir=temp, run_name='cohort-run',
                                 attack='tool_knowledge'), 1)
                model.assert_not_called()
            base = Path(temp) / 'agentdyn/offline-model_cohort-run'
            execution = json.loads(next((base/'execution').glob('*/execution.json')).read_text())
            self.assertEqual(execution['groups'][0]['status'], 'unsupported')
            self.assertEqual(execution['groups'][0]['planned_pairs'], 9)


if __name__ == '__main__':
    unittest.main()
