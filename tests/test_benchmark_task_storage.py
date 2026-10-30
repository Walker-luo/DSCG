"""Scored execution writes flat native traces without implicit GOAL work."""
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest

from agentdojo import logging
from experiments.common.native_cache_compat import ensure_native_cache_model_ready
from experiments.common.benchmark_tasks import run_native_suite


class ScoredTaskStorageTests(unittest.TestCase):
    def setUp(self):
        ensure_native_cache_model_ready()
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.calls = []
        self.users = {'user_task_0': SimpleNamespace(ID='user_task_0')}
        self.targets = {'injection_task_0': SimpleNamespace(ID='injection_task_0')}
        self.suite = SimpleNamespace(name='banking', injection_tasks=self.targets,
            get_user_task_by_id=self.users.__getitem__, get_injection_task_by_id=self.targets.__getitem__,
            run_task_with_pipeline=self.run_task)
        self.pipeline = SimpleNamespace(name='important_instructions')
        self.attack = SimpleNamespace(name='important_instructions', is_dos_attack=False,
            attack=lambda user, injection: {'file': 'fixture'})

    def run_task(self, pipeline, task, injection_task=None, injections=None):
        self.calls.append((task.ID, injection_task.ID if injection_task else None))
        logging.Logger.get().log([
            {'role': 'user', 'content': [{'type': 'text', 'content': 'fixture'}]},
            {'role': 'assistant', 'tool_calls': None, 'content': [{'type': 'text', 'content': 'fixture'}]}])
        return True, False

    def execute(self, attack=True):
        steps = []
        with logging.OutputLogger(self.root):
            result = run_native_suite(self.pipeline, self.suite, self.attack if attack else None,
                self.root, False, user_tasks=list(self.users), injection_tasks=list(self.targets),
                benchmark_version='v1.2', on_step=steps.append)
        return result, steps

    def test_default_scored_execution_never_runs_goal_and_reuses_flat_cache(self):
        result, steps = self.execute()
        self.assertEqual(self.calls, [('user_task_0', 'injection_task_0')])
        self.assertEqual(steps, ['score'])
        self.assertEqual(result['injection_tasks_utility_results'], {})
        self.assertEqual(result['utility_results'], {('user_task_0', 'injection_task_0'): True})
        path = self.root/'important_instructions/banking/user_task_0/injection_task_0.json'
        self.assertTrue(path.is_file())
        before = path.read_bytes()
        self.assertEqual(self.execute(), (result, steps))
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(list(path.parent.parent.glob('injection_task_*')), [])

    def test_clean_execution_uses_flat_none_path_and_cache(self):
        self.pipeline.name = 'none'
        result, steps = self.execute(attack=False)
        self.assertEqual(self.calls, [('user_task_0', None)])
        self.assertEqual(steps, ['score'])
        self.assertEqual(result['utility_results'], {('user_task_0', ''): True})
        self.assertTrue((self.root/'none/banking/user_task_0/none.json').is_file())
        self.assertEqual(self.execute(attack=False), (result, steps))
        self.assertEqual(len(self.calls), 1)

    def test_dos_keeps_one_native_target_and_scoring(self):
        self.attack.is_dos_attack = True
        self.targets['injection_task_1'] = SimpleNamespace(ID='injection_task_1')
        result, steps = self.execute()
        self.assertEqual(self.calls, [('user_task_0', 'injection_task_0')])
        self.assertEqual(steps, ['score'])
        self.assertEqual(result['security_results'], {('user_task_0', 'injection_task_0'): False})
        self.assertEqual(result['injection_tasks_utility_results'], {})


if __name__ == '__main__':
    unittest.main()
