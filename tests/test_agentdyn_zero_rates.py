import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.diagnostics import agentdyn_zero_rates as diag


class _Call:
    def __init__(self, tool):
        self.function = tool


class _Task:
    def ground_truth(self, environment):
        return [_Call('required_tool')]


class _Suite:
    user_tasks = {'user_task_0': _Task()}

    def load_and_inject_default_environment(self, injections):
        return object()


class DiagnosisTests(unittest.TestCase):
    def test_missing_trace_error_and_authorization_gap_are_distinct(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'attack_manifest.json').write_text(json.dumps({
                'benchmark': {'id': 'agentdyn'}, 'model_id': 'example',
                'attacks': ['ignore_previous'], 'suites': ['shopping']}))
            group = root / 'ignore_previous' / 'shopping'
            group.mkdir(parents=True)
            (group / 'summary.json').write_text(json.dumps({'task_selection': {
                'user_task_ids': ['user_task_0'],
                'injection_task_ids': ['injection_task_0', 'injection_task_1']}}))
            p = group / 'user_task_0' / 'ignore_previous'
            p.mkdir(parents=True)
            (p / 'injection_task_0.json').write_text(json.dumps({
                'utility': False, 'security': False, 'error': None,
                'injections': {'x': 'payload-marker'},
                'messages': [{'role': 'tool', 'content': 'payload-marker',
                              'error': None}, {'role': 'tool', 'content': 'DSCG_BLOCKED',
                                               'error': 'DSCG_BLOCKED'}],
                'dscg_authorizations': [{'allowed_tools': ['other_tool']}],
                'dscg_cost': {'models': [{'generation': {'total_tokens': 10}}]},
            }))
            with patch.object(diag, 'get_suite', return_value=_Suite()):
                report = diag.analyze_run(root)
            self.assertEqual(report['counts']['planned'], 2)
            self.assertEqual(report['counts']['valid'], 1)
            self.assertEqual(report['counts']['missing'], 1)
            self.assertEqual(report['counts']['reference_gap'], 1)
            self.assertEqual(report['counts']['payload_visible_exact'], 1)
            self.assertEqual(report['tasks'][0]['reference_tools_missing'], ['required_tool'])
            self.assertFalse(report['tasks'][0]['security'])

    def test_payload_absent_and_api_error_not_scored(self):
        result = diag.inspect_trace({
            'utility': None, 'security': None, 'error': {'type': 'APIError'},
            'injections': {'x': 'payload-marker'},
            'messages': [{'role': 'tool', 'content': 'different content'}],
            'dscg_authorizations': []}, ['required_tool'])
        self.assertEqual(result['status'], 'error')
        self.assertFalse(result['payload_visible_exact'])
        self.assertIsNone(result['reference_tools_missing'])
        self.assertIsNone(result['total_tokens'])

    def test_last_authorization_is_used_without_unioning_old_permissions(self):
        result = diag.inspect_trace({
            'utility': False, 'security': False, 'error': None,
            'dscg_authorizations': [{'allowed_tools': ['required_tool']},
                                    {'allowed_tools': ['other_tool']}]}, ['required_tool'])
        self.assertEqual(result['reference_tools_missing'], ['required_tool'])

    def test_group_without_summary_is_not_scored_as_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'attack_manifest.json').write_text(json.dumps({
                'benchmark': {'id': 'agentdyn'}, 'model_id': 'example',
                'attacks': ['tool_knowledge'], 'suites': ['dailylife'],
                'execution': {'groups': [{'attack': 'tool_knowledge', 'suite': 'dailylife',
                                          'status': 'error'}]}}))
            report = diag.analyze_run(root)
            self.assertEqual(report['counts']['planned'], 0)
            self.assertEqual(report['counts']['valid'], 0)
            self.assertEqual(report['issues'][0]['recorded_group_status'], 'error')

    def test_corrupt_native_trace_is_not_a_false_label(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'attack_manifest.json').write_text(json.dumps({
                'benchmark': {'id': 'agentdyn'}, 'model_id': 'example',
                'attacks': ['ignore_previous'], 'suites': ['shopping']}))
            group = root / 'ignore_previous' / 'shopping'
            group.mkdir(parents=True)
            (group / 'summary.json').write_text(json.dumps({'task_selection': {
                'user_task_ids': ['user_task_0'],
                'injection_task_ids': ['injection_task_0']}}))
            p = group / 'user_task_0' / 'ignore_previous'
            p.mkdir(parents=True)
            (p / 'injection_task_0.json').write_text('{invalid')
            with patch.object(diag, 'get_suite', return_value=_Suite()):
                report = diag.analyze_run(root)
            self.assertEqual(report['counts']['valid'], 0)
            self.assertEqual(report['counts']['corrupt'], 1)

    def test_failed_group_uses_declared_binding_and_keeps_preflight(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'attack_manifest.json').write_text(json.dumps({
                'benchmark': {'id': 'agentdyn'}, 'model_id': 'example',
                'attacks': ['tool_knowledge'], 'suites': ['shopping']}))
            group = root / 'tool_knowledge' / 'shopping'
            preflight = group / 'injection_task_0' / 'none'
            preflight.mkdir(parents=True)
            (group / 'run_manifest.json').write_text(json.dumps({'task_selection': {
                'users': ['user_task_0'], 'injections': ['injection_task_0']}}))
            (preflight / 'none.json').write_text(json.dumps({'utility': True, 'error': None}))
            with patch.object(diag, 'get_suite', return_value=_Suite()):
                report = diag.analyze_run(root)
            self.assertEqual(report['counts']['planned'], 1)
            self.assertEqual(report['counts']['missing'], 1)
            self.assertEqual(report['counts']['valid'], 0)
            self.assertEqual(report['preflight_counts']['valid'], 1)


if __name__ == '__main__':
    unittest.main()
