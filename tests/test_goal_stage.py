"""Offline GOAL stage tests: native trajectories with no model/network calls."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from agentdojo import logging
from experiments.common.goal_stage import run_goal_checks


class GoalStageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.selections = {'banking': {'user_task_ids': ['user_task_0'],
                                      'injection_task_ids': ['injection_task_0', 'injection_task_1']}}
        self.calls = []
        self.factories = []
        self.effects = {}
        self.tracker = None
        self.task = lambda key: SimpleNamespace(ID=key)
        self.suite = SimpleNamespace(name='banking', get_injection_task_by_id=self.task,
                                     run_task_with_pipeline=self.trajectory)
        self.patch = patch('experiments.common.goal_stage.get_suite', return_value=self.suite)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.write_summary({'preserved': {'value': 3}, 'selection_report': {'other': 'keep'}})

    def write_summary(self, value):
        (self.base/'summary.json').write_text(json.dumps(value))

    def summary(self):
        return json.loads((self.base/'summary.json').read_text())

    def factory(self, suite):
        self.factories.append(suite)
        return SimpleNamespace(name='measurement', _goal_trackers=(self.tracker,) if self.tracker else ())

    def trajectory(self, pipeline, task, **kwargs):
        records = self.summary()['selection_report']['goal_checks']
        self.assertEqual(next(r for r in records if r['injection_task_id'] == task.ID)['status'], 'running')
        self.assertEqual(pipeline.name, 'goal')
        self.calls.append(task.ID)
        if self.tracker is not None:
            self.tracker.tokens += 17
        value = self.effects.get(task.ID, True)
        logger = logging.Logger.get()
        logger.log([{'role': 'assistant', 'content': [{'type': 'text', 'text': 'fixture'}]}])
        if isinstance(value, BaseException):
            raise value
        if isinstance(value, dict):
            for key, item in value.items():
                logger.set_contextarg(key, item)
            return True, True
        return value, True

    def execute(self, **kwargs):
        return run_goal_checks(self.base, self.selections, self.factory, **kwargs)

    def test_one_trajectory_each_and_factory_once_preserves_summary(self):
        self.selections['banking']['injection_task_ids'].append('injection_task_0')
        records = self.execute()
        self.assertEqual(self.calls, ['injection_task_0', 'injection_task_1'])
        self.assertEqual(self.factories, ['banking'])
        self.assertEqual([r['status'] for r in records], ['passed', 'passed'])
        self.assertEqual(records[0]['path'], 'goal/banking/injection_task_0.json')
        self.assertTrue((self.base/records[0]['path']).is_file())
        self.assertEqual(self.summary()['preserved'], {'value': 3})
        self.assertEqual(self.summary()['selection_report']['other'], 'keep')

    def test_failed_target_and_error_are_not_retried_on_resume(self):
        self.effects = {'injection_task_0': False, 'injection_task_1': ValueError('PRIVATE TOKEN')}
        first = self.execute()
        self.assertEqual([r['status'] for r in first], ['failed', 'error'])
        self.effects = {}
        second = self.execute(reuse=True)
        self.assertEqual(first, second)
        self.assertEqual(len(self.calls), 2)
        self.assertEqual(self.factories, ['banking'])
        self.assertNotIn('PRIVATE TOKEN', (self.base/'summary.json').read_text())

    def test_interrupted_running_target_becomes_error_without_retry(self):
        self.write_summary({'selection_report': {'goal_checks': [
            {'suite': 'banking', 'injection_task_id': 'injection_task_0', 'status': 'running',
             'path': 'goal/banking/injection_task_0.json', 'cost': None}]}})
        records = self.execute(reuse=True)
        self.assertEqual(records[0]['status'], 'error')
        self.assertEqual(records[0]['error_code'], 'GOAL_INTERRUPTED')
        self.assertEqual(self.calls, ['injection_task_1'])

    def test_keyboard_interrupt_is_saved_and_propagated(self):
        self.effects['injection_task_0'] = KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt):
            self.execute()
        record = self.summary()['selection_report']['goal_checks'][0]
        self.assertEqual(record['status'], 'error')
        self.assertEqual(record['error_code'], 'GOAL_INTERRUPTED')
        self.execute(reuse=True)
        self.assertEqual(self.calls, ['injection_task_0', 'injection_task_1'])

    def test_recorded_api_failure_overrides_native_success_and_keeps_cost(self):
        cost = {'models': [{'generation': {'api_calls': 2, 'failed_calls': 1,
                'missing_usage_calls': 0, 'total_tokens': 12}}]}
        self.effects['injection_task_0'] = {'dscg_cost': cost}
        records = self.execute()
        self.assertEqual(records[0]['status'], 'error')
        self.assertEqual(records[0]['error_code'], 'RECORDED_API_FAILURE')
        self.assertEqual(records[0]['cost'], cost)
        self.assertIsNone(records[1]['cost'])

    def test_native_error_with_false_utility_is_error(self):
        self.effects['injection_task_0'] = {'error': 'PRIVATE RESPONSE'}
        records = self.execute()
        self.assertEqual(records[0]['status'], 'error')
        self.assertNotIn('PRIVATE RESPONSE', (self.base/'summary.json').read_text())

    def test_existing_run_without_reuse_rejected_before_factory(self):
        self.execute()
        with self.assertRaises(ValueError):
            self.execute()
        self.assertEqual(len(self.calls), 2)

    def test_baseline_tracker_cost_is_per_target_and_persisted_on_errors(self):
        class Tracker:
            tokens = 0
            def snapshot(self):
                return {'generation': {'api_calls': self.tokens // 17, 'total_tokens': self.tokens}}
        self.tracker = Tracker()
        self.effects['injection_task_1'] = ValueError('private')
        records = self.execute()
        self.assertEqual([r['cost']['models'][0]['generation']['total_tokens'] for r in records], [17, 17])
        self.assertEqual(records[1]['status'], 'error')

    def test_failed_tracker_calls_override_native_success_without_diagnostics(self):
        class Tracker:
            tokens = 0
            def snapshot(self):
                return {'generation': {'failed_calls': self.tokens // 17}}
        self.tracker = Tracker()
        records = self.execute()
        self.assertEqual([r['status'] for r in records], ['error', 'error'])
        self.assertEqual(records[0]['error_code'], 'RECORDED_API_FAILURE')

    def test_malformed_cost_is_error_and_does_not_stop_next_goal(self):
        self.effects['injection_task_0'] = {'dscg_cost': ['invalid']}
        records = self.execute()
        self.assertEqual(records[0]['status'], 'error')
        self.assertEqual(records[1]['status'], 'passed')

    def test_empty_targets_do_not_construct_pipeline(self):
        self.selections['banking']['injection_task_ids'] = []
        self.assertEqual(self.execute(), [])
        self.assertEqual(self.factories, [])


if __name__ == '__main__':
    unittest.main()
