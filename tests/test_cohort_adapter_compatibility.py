"""A recorded capability cohort survives a verified no-op transport marker."""
import json
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from dscg.model_config import ModelConfig
from experiments.common import injection_cohort as cohort
from test_partial_agentdyn import TemporaryDirectory, DOJO_IDENTITY
from test_injection_precheck import FakeSuite


class CohortAdapterCompatibilityTests(unittest.TestCase):
    def setUp(self):
        artifacts = Path(__file__).resolve().parents[1] / 'workshop/artifacts/20261021_cohort_adapter_noop/tests'
        artifacts.mkdir(parents=True, exist_ok=True)
        temp = TemporaryDirectory(dir=artifacts)
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.config = ModelConfig('qwen3.7-flash', 'offline-key', 'https://example.invalid', 'dashscope', 'TEST_KEY')
        self.suite = FakeSuite()
        for item in [patch.object(cohort, 'get_suite', return_value=self.suite),
                     patch.object(cohort, 'benchmark_identity', return_value=DOJO_IDENTITY)]:
            item.start(); self.addCleanup(item.stop)
        binding = cohort._binding(self.config, ['workspace'])
        binding['main_model'].pop('chat_request_adapter')
        decisions = {}
        for task in self.suite.injection_tasks.values():
            path = self.root / (task.ID + '.json')
            trace = {'suite_name': 'workspace', 'user_task_id': task.ID, 'injection_task_id': None,
                     'attack_type': None, 'injections': {}, 'agentdojo_package_version': binding['source']['agentdojo'],
                     'messages': [{'role': 'system', 'content': [{'type': 'text', 'content': 'Trusted system instruction.'}]},
                                  {'role': 'user', 'content': [{'type': 'text', 'content': task.GOAL}]},
                                  {'role': 'assistant', 'content': [{'type': 'text', 'content': 'done'}], 'tool_calls': None}],
                     'error': None, 'utility': True}
            path.write_text(json.dumps(trace))
            decisions[task.ID] = {'status': 'kept', 'attempts': [
                {'status': 'pass', 'trace_path': str(path), 'trace_sha256': cohort._file_hash(path)}]}
        self.value = {'schema_version': cohort.SCHEMA, 'benchmark': DOJO_IDENTITY, 'suite_version': 'v1.2',
                      'selection_rule': cohort.RULE, 'binding': binding,
                      'decisions': {'workspace': decisions}, 'suites': {'workspace': {
                          'user_task_ids': list(self.suite.user_tasks),
                          'injection_task_ids': list(self.suite.injection_tasks)}}}
        self.path = self.root / 'cohort.json'
        self.save()

    def save(self):
        self.value['cohort_sha256'] = cohort._digest({k: v for k, v in self.value.items() if k != 'cohort_sha256'})
        self.path.write_text(json.dumps(self.value))

    def validate(self):
        # Exercise the serializer used by current AgentDojo, independently of the active test backend.
        def system_serializer(message, model):
            return {'role': message['role'], 'content': message['content']}
        with patch('agentdojo.agent_pipeline.llms.openai_llm._message_to_openai', side_effect=system_serializer):
            return cohort._validate_cohort(self.path, self.config)

    def test_old_missing_dashscope_marker_accepts_noop_without_changing_frozen_bytes(self):
        originals = {p: p.read_bytes() for p in self.root.iterdir() if p.is_file()}
        with self.assertWarnsRegex(UserWarning, 'no-op'):
            result = self.validate()
        self.assertEqual(result, self.value)
        self.assertEqual(originals, {p: p.read_bytes() for p in originals})

    def test_current_serializer_producing_developer_is_not_a_noop(self):
        with patch('agentdojo.agent_pipeline.llms.openai_llm._message_to_openai',
                   return_value={'role': 'developer', 'content': 'system'}):
            with self.assertRaisesRegex(ValueError, 'adapter.*changes'):
                cohort._validate_cohort(self.path, self.config)

    def test_explicit_developer_trace_still_requires_new_screen(self):
        attempt = self.value['decisions']['workspace']['injection_task_0']['attempts'][0]
        path = Path(attempt['trace_path'])
        trace = json.loads(path.read_text()); trace['messages'][0]['role'] = 'developer'
        path.write_text(json.dumps(trace)); attempt['trace_sha256'] = cohort._file_hash(path); self.save()
        with self.assertRaisesRegex(ValueError, 'adapter.*changes'):
            self.validate()

    def test_model_request_settings_and_unknown_adapter_changes_still_reject(self):
        original = deepcopy(self.value)
        for key, value in [('model_id', 'different-model'), ('base_url', 'https://other.invalid'),
                           ('provider', 'openai'), ('reasoning_effort', 'high'),
                           ('chat_request_adapter', 'unknown-adapter')]:
            with self.subTest(key=key):
                self.value = deepcopy(original); self.value['binding']['main_model'][key] = value; self.save()
                with self.assertRaisesRegex(ValueError, 'configuration changed'):
                    self.validate()

    def test_tampered_evidence_is_not_accepted_as_noop(self):
        attempt = self.value['decisions']['workspace']['injection_task_0']['attempts'][0]
        Path(attempt['trace_path']).write_text('{}')
        with self.assertRaisesRegex(ValueError, 'evidence changed'):
            self.validate()

    def test_full_and_partial_keep_frozen_cohort_and_record_noop_provenance(self):
        original = self.path.read_bytes()
        backend = SimpleNamespace(id='agentdojo', suites=('workspace', 'travel', 'banking', 'slack'))
        def execute(**options):
            options['_reuse_plan'].commit()
            return 0
        for scope, users in [('screened', 4), ('partial_screened', 3)]:
            with self.subTest(scope=scope), patch.object(cohort, 'get_backend', return_value=backend), \
                 patch.object(cohort, 'resolve_model_config', return_value=self.config), \
                 patch('experiments.common.partial_controls.benchmark_identity', return_value=DOJO_IDENTITY), \
                 patch('agentdojo.agent_pipeline.llms.openai_llm._message_to_openai',
                       side_effect=lambda message, model: message), \
                 patch.object(cohort.shared, 'main', side_effect=execute) as runner, \
                 self.assertWarnsRegex(UserWarning, 'no-op'):
                self.assertEqual(cohort.run_screened(self.path, task_scope=scope,
                    run_name=scope, results_dir=self.root / 'runs', suites=['workspace'],
                    origin=True, attack='ignore_previous'), 0)
                self.assertEqual(runner.call_args.kwargs['cohort_sha256'], self.value['cohort_sha256'])
            run = self.root / 'runs' / 'agentdojo' / f'qwen3.7-flash_{scope}'
            attachment = json.loads((run / 'screened_cohort.json').read_text())
            self.assertEqual(attachment['cohort'], self.value)
            self.assertEqual(len(attachment['selected_tasks']['workspace']['user_task_ids']), users)
            self.assertEqual(attachment['request_adapter_compatibility']['policy'], 'agentdojo-dashscope-noop-v1')
            self.assertEqual(self.path.read_bytes(), original)


if __name__ == '__main__':
    unittest.main()
