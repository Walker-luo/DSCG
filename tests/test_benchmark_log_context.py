"""Console task identity only; no model calls or judgment-quality claims."""
from contextlib import redirect_stdout
from io import StringIO
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import warnings

from agentdojo import benchmark
from dscg.pipelines.defended import AuthorizationCompilationError, PermissionSandbox
from experiments.common.benchmark_tasks import run_native_suite


class BenchmarkTaskLogTests(unittest.TestCase):
    def suite(self, targets=('injection_task_3',)):
        users = {'user_task_17': SimpleNamespace(ID='user_task_17')}
        injections = {key: SimpleNamespace(ID=key) for key in targets}
        return SimpleNamespace(name='banking', user_tasks=users, injection_tasks=injections,
            get_user_task_by_id=users.__getitem__, get_injection_task_by_id=injections.__getitem__)

    def run_suite(self, suite, attack):
        return run_native_suite(SimpleNamespace(name='pipeline'), suite, attack, None, False,
            user_tasks=['user_task_17'], injection_tasks=list(suite.injection_tasks),
            benchmark_version='v1.2')

    def test_authorization_failure_has_goal_or_scored_ids_and_safe_reason(self):
        def fail():
            PermissionSandbox().mark_error(AuthorizationCompilationError('AUTH_INVALID_JSON'))
        def goal(*_):
            fail()
            return False, True
        def scored(_suite, _pipe, user, _attack, _logdir, _force, targets, _version):
            fail()
            return {(user.ID, targets[0]): False}, {(user.ID, targets[0]): False}
        output = StringIO()
        with patch.object(benchmark, 'run_task_without_injection_tasks', side_effect=goal), \
             patch.object(benchmark, 'run_task_with_injection_tasks', side_effect=scored), \
             redirect_stdout(output), warnings.catch_warnings(record=True):
            self.run_suite(self.suite(), SimpleNamespace(name='tool_knowledge', is_dos_attack=False))
        goal_line, scored_line = output.getvalue().splitlines()
        for line in (goal_line, scored_line):
            self.assertIn('suite=banking', line)
            self.assertIn('injection_task_id=injection_task_3', line)
            self.assertIn('AuthorizationCompilationError', line)
            self.assertIn('AUTH_INVALID_JSON', line)
        self.assertIn('stage=goal_preflight', goal_line)
        self.assertIn('user_task_id=none', goal_line)
        self.assertIn('stage=scored_task', scored_line)
        self.assertIn('user_task_id=user_task_17', scored_line)

    def test_goal_warnings_identify_each_failed_or_error_target(self):
        suite = self.suite(('injection_task_2', 'injection_task_9', 'injection_task_11'))
        statuses = {'injection_task_2': False, 'injection_task_9': None, 'injection_task_11': True}
        def goal(_suite, _pipe, task, *_):
            return statuses[task.ID], True
        def scored(_suite, _pipe, user, _attack, _logdir, _force, targets, _version):
            return {(user.ID, targets[0]): True}, {(user.ID, targets[0]): False}
        with patch.object(benchmark, 'run_task_without_injection_tasks', side_effect=goal), \
             patch.object(benchmark, 'run_task_with_injection_tasks', side_effect=scored), \
             warnings.catch_warnings(record=True) as notices:
            warnings.simplefilter('always')
            result = self.run_suite(suite, SimpleNamespace(name='ignore_previous', is_dos_attack=False))
        self.assertEqual(len(notices), 2)
        failed, error = (str(row.message) for row in notices)
        self.assertIn('injection_task_id=injection_task_2', failed)
        self.assertIn('injection_task_id=injection_task_9', error)
        self.assertIn('not capability failures', error)
        for text in (failed, error):
            self.assertIn('suite=banking', text)
            self.assertIn('stage=goal_preflight', text)
            self.assertIn('user_task_id=none', text)
            self.assertNotIn('injection_task_11', text)
        self.assertEqual(result['injection_tasks_utility_results'], statuses)
        self.assertEqual(len(result['utility_results']), 3)

    def test_clean_context_does_not_leak_into_later_standalone_error(self):
        def clean(*_):
            PermissionSandbox().mark_error(ValueError('private-value'))
            return False, True
        output = StringIO()
        with patch.object(benchmark, 'run_task_without_injection_tasks', side_effect=clean), redirect_stdout(output):
            self.run_suite(self.suite(), None)
            PermissionSandbox().mark_error(ValueError('private-value'))
        clean_line, standalone = output.getvalue().splitlines()
        self.assertIn('stage=clean_task', clean_line)
        self.assertIn('user_task_id=user_task_17', clean_line)
        self.assertIn('injection_task_id=none', clean_line)
        self.assertNotIn('user_task_17', standalone)
        self.assertNotIn('private-value', output.getvalue())

    def test_native_exception_also_resets_task_context(self):
        with patch.object(benchmark, 'run_task_without_injection_tasks', side_effect=TypeError('native')):
            with self.assertRaises(TypeError) as caught:
                self.run_suite(self.suite(), None)
        self.assertEqual(caught.exception._dscg_execution_stage, 'clean_task')
        output = StringIO()
        with redirect_stdout(output):
            PermissionSandbox().mark_error(ValueError('private-value'))
        self.assertNotIn('user_task_17', output.getvalue())

    def test_direct_pipeline_uses_native_logger_context(self):
        logger = SimpleNamespace(context=dict(suite_name='travel', user_task_id='user_task_8',
            injection_task_id='injection_task_4'))
        output = StringIO()
        with patch('dscg.pipelines.defended.logging.Logger.get', return_value=logger), redirect_stdout(output):
            PermissionSandbox().mark_error(ValueError('private-value'))
        self.assertIn('suite=travel', output.getvalue())
        self.assertIn('user_task_id=user_task_8', output.getvalue())
        self.assertIn('injection_task_id=injection_task_4', output.getvalue())
