"""Effective L2 controls must reach runtime and identify independent run caches."""
import json
from pathlib import Path
from tests import test_partial_agentdyn as tempfile
import unittest
from unittest.mock import Mock, patch

from dscg.l2_authorization import ToolAuthorizationProfile
from dscg.model_config import ModelConfig
from dscg.benchmark_catalog import get_backend
from dscg.pipelines import defended as d
from experiments import run_partial_benchmark as partial
from dashboard.evaluation import normalize_config, trace_stats


class L2ControlTests(unittest.TestCase):
    def pipeline(self, **flags):
        config = ModelConfig(provider='custom', model_id='offline', api_key='fixture', base_url='http://offline')
        with patch('dscg.pipelines.defended.create_openai_client', return_value=Mock()):
            return d.make_defended_pipeline(model_config=config, sec_model_config=config, **flags)[0]

    def test_default_and_legacy_views_have_distinct_effective_config_and_name(self):
        current = self.pipeline()
        control = self.pipeline(planning_tool_view=False, delegated_tasks=False)
        self.assertTrue(current.task_executor.planning_tool_view)
        self.assertTrue(current.task_executor.delegated_tasks)
        self.assertTrue(current.dscg_optimization_config['planning_tool_view'])
        self.assertFalse(control.task_executor.planning_tool_view)
        self.assertFalse(control.task_executor.delegated_tasks)
        self.assertNotEqual(current.name, control.name)
        self.assertNotEqual(current.dscg_optimization_config['framework_version'], 'three-layer-v1')

    def test_without_l2_no_view_or_delegate_authority_can_be_created(self):
        pipeline = self.pipeline(use_sandbox=False)
        self.assertFalse(pipeline.task_executor.planning_tool_view)
        self.assertFalse(pipeline.task_executor.delegated_tasks)
        self.assertFalse(pipeline.dscg_optimization_config['planning_tool_view'])
        self.assertFalse(pipeline.dscg_optimization_config['delegated_tasks'])

    def test_profile_is_host_api_input_and_hash_bound_not_a_request_string_in_config(self):
        profile = ToolAuthorizationProfile('host-read', ('Read facts',), frozenset({'read_data'}))
        pipeline = self.pipeline(authorization_profile=profile)
        self.assertIs(pipeline.task_executor.authorization_compiler.authorization_profile, profile)
        self.assertEqual(pipeline.dscg_optimization_config['authorization_profile_sha256'], profile.identity())
        self.assertNotIn('Read facts', str(pipeline.dscg_optimization_config))
        with self.assertRaises(ValueError):
            self.pipeline(use_sandbox=False, authorization_profile=profile)

    def test_partial_api_and_cli_forward_controls_for_every_attack(self):
        import serial_fixture
        with tempfile.TemporaryDirectory() as output, serial_fixture.patched(), \
             patch.object(partial, 'make_defended_pipeline', side_effect=serial_fixture.defended) as run:
            partial.main(run_attack=False, results_dir=output, planning_tool_view=False, delegated_tasks=False)
            self.assertFalse(run.call_args.kwargs['planning_tool_view'])
            self.assertFalse(run.call_args.kwargs['delegated_tasks'])
        with patch.object(partial, 'main', return_value=0) as run:
            self.assertEqual(partial.cli(['--clean', '--no-tool-view', '--no-delegated-tasks']), 0)
            self.assertFalse(run.call_args.kwargs['planning_tool_view'])
            self.assertFalse(run.call_args.kwargs['delegated_tasks'])

    def test_web_controls_are_validated_and_disabled_with_native_or_no_l2(self):
        default = normalize_config({'suites': [get_backend().suites[0]]})
        self.assertTrue(default['planning_tool_view'])
        self.assertTrue(default['delegated_tasks'])
        for flags in ({'origin': True}, {'use_sandbox': False}):
            effective = normalize_config({'suites': [get_backend().suites[0]], **flags})
            self.assertFalse(effective['planning_tool_view'])
            self.assertFalse(effective['delegated_tasks'])
        with self.assertRaises(ValueError):
            normalize_config({'suites': [get_backend().suites[0]], 'delegated_tasks': 'true'})

    def test_l2_trace_totals_cover_scored_records_only_and_old_records_stay_missing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for user, stats in [('u1', {'planning_requests': 2, 'visible_tools_total': 3}),
                                ('preflight', {'planning_requests': 99}), ('u2', None)]:
                path = root / 'pipeline/workspace' / user / 'attack/i1.json'
                path.parent.mkdir(parents=True)
                path.write_text(json.dumps({'dscg_l2': stats} if stats else {}))
            counts = trace_stats(root, 'pipeline', 'workspace', 'attack', [('u1', 'i1'), ('u2', 'i1')])
            self.assertEqual(counts['trace_records'], 2)
            self.assertEqual(counts['l2_records'], 1)
            self.assertEqual(counts['l2']['planning_requests'], 2)
            self.assertEqual(counts['l2']['visible_tools_total'], 3)
