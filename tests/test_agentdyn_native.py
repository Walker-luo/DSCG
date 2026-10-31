"""Pinned real environments, real tools and native predicates; zero model requests.

Direct injection-goal scripts test the oracle plumbing, not attack generation or
defense efficacy. OTP is extracted from real tool feedback, never environment state.
"""
import json
import re
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import Mock, patch

from agentdojo.agent_pipeline import BasePipelineElement, ToolsExecutor
from agentdojo.agent_pipeline.tool_execution import tool_result_to_str
from agentdojo.functions_runtime import FunctionCall, FunctionsRuntime
from agentdojo.types import text_content_block_from_string as block
from dscg.benchmark_catalog import BenchmarkConfigurationError, get_backend, get_suites, get_suite, validate_backend
from dscg.pipelines.defended import ActionSecurityChecker, PermissionSandbox, ReferenceMonitor, TicketedToolsExecutor
from dscg.tool_metadata import ToolMetadataError, load_tool_metadata, set_tool_metadata


def call(name, **args):
    return FunctionCall(function=name, args=args)


def password_steps(password):
    yield call('update_shopping_account_password', password=password)
    feedback = yield call('get_shopping_linked_unread_emails')
    # Only use the latest returned password-update email. No hidden-state lookup.
    matches = re.findall(r'password updating OTP is: (\d{6})', feedback)
    if not matches:
        raise AssertionError('Actual OTP email missing from returned feedback')
    yield call('verify_shopping_account', otp=matches[-1])


class Script(BasePipelineElement):
    def __init__(self, steps, decision=None, permitted=None, metadata=None):
        self.steps = steps
        self.decision = decision
        self.permitted = permitted
        self.metadata = metadata
        self.messages = []
        self.audit_calls = 0

    def query(self, query, runtime, env, messages=None, extra_args=None):
        self.pre_filesystem = env.filesystem.model_dump() if hasattr(env, 'filesystem') else None
        history = [{'role': 'user', 'content': [block(query)]}]
        extra = {}
        native = ToolsExecutor()
        if self.decision is not None:
            catalog = self.metadata if self.metadata is not None else load_tool_metadata()
            set_tool_metadata(runtime, {name: value for name, value in catalog.items() if name in runtime.functions})
            sandbox = PermissionSandbox(self.permitted if self.permitted is not None else list(runtime.functions))
            llm = SimpleNamespace(name='offline-authored-decision', client=Mock())
            llm.client.chat.completions.create.return_value = SimpleNamespace(choices=[SimpleNamespace(
                message=SimpleNamespace(content=json.dumps(dict(decision=self.decision,
                    violations=[], confidence=1, reason_code='OFFLINE_FIXTURE')), refusal=None), finish_reason='stop')])
            checker = ActionSecurityChecker(llm, sandbox=sandbox)
            monitor = ReferenceMonitor(sandbox, True)
            native = TicketedToolsExecutor(monitor)
        generator = self.steps(env)
        step = next(generator, None)
        while step is not None:
            history.append({'role': 'assistant', 'content': [block('')], 'tool_calls': [step]})
            state = (query, runtime, env, history, extra)
            if self.decision is not None:
                state = checker.query(*state)
                state = monitor.query(*state)
            _, _, env, history, extra = native.query(*state)
            feedback = '\n'.join(b['content'] for b in history[-1].get('content', []) if b.get('type') == 'text')
            if self.decision is None:
                if history[-1].get('error'):
                    raise AssertionError(history[-1]['error'])
            try:
                step = generator.send(feedback)
            except StopIteration:
                step = None
        history.append({'role': 'assistant', 'content': [block('Completed scripted simulation.')], 'tool_calls': None})
        self.env, self.messages, self.extra = env, history, extra
        if self.decision is not None:
            self.audit_calls = llm.client.chat.completions.create.call_count
        return query, runtime, env, history, extra


def fixed_steps(calls):
    def steps(env):
        for item in calls(env):
            yield item
    return steps


class AgentDynNativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            if get_backend().id != 'agentdyn':
                raise unittest.SkipTest('AgentDyn-specific native tests; separate AgentDojo native tests cover this environment')
            validate_backend()
        except BenchmarkConfigurationError as exc:
            raise unittest.SkipTest(f'requires separately installed pinned ipi-agentdyn: {exc}')
        cls.suites = {name: get_suite('v1.2', name) for name in get_suites()}

    def test_real_clean_tools_and_native_utility_in_every_suite(self):
        for name, task_id in [('shopping', 'user_task_1'), ('github', 'user_task_0'), ('dailylife', 'user_task_1')]:
            with self.subTest(suite=name):
                suite = self.suites[name]
                task = suite.user_tasks[task_id]
                steps = (lambda env: password_steps('NewPassword')) if name == 'shopping' else fixed_steps(task.ground_truth)
                script = Script(steps)
                self.assertEqual(suite.run_task_with_pipeline(script, task, None, {}), (True, True))
                self.assertTrue(any(m['role'] == 'tool' for m in script.messages))

    def test_real_injection_goal_predicates_have_positive_and_negative_states(self):
        for name in get_suites():
            with self.subTest(suite=name):
                suite = self.suites[name]
                target = suite.injection_tasks['injection_task_0']
                if name == 'shopping':
                    steps = lambda env: password_steps('attacked')
                elif name == 'github':
                    steps = fixed_steps(lambda env: [call('git_star', repo_name='trustme/awesome_literature')])
                else:
                    steps = fixed_steps(target.ground_truth)
                idle = Script(fixed_steps(lambda env: []))
                self.assertEqual(suite.run_task_with_pipeline(idle, target, target, {}), (False, False))
                active = Script(steps)
                self.assertEqual(suite.run_task_with_pipeline(active, target, target, {}), (True, True))

    def test_native_injection_payload_reaches_real_tool_feedback(self):
        for name in get_suites():
            with self.subTest(suite=name):
                suite = self.suites[name]
                marker = 'DSCG_OFFLINE_INJECTION_CANARY'
                vectors = suite.get_injection_vector_defaults()
                env = suite.load_and_inject_default_environment({key: marker for key in vectors})
                runtime = FunctionsRuntime(suite.tools)
                # Native unread/received inbox API returns actual injected email content.
                tool = 'get_shopping_linked_unread_emails' if name == 'shopping' else 'get_received_emails'
                value, error = runtime.run_function(env, tool, {})
                self.assertIsNone(error)
                self.assertIn(marker, tool_result_to_str(value))

    def test_web_side_effect_is_audited_and_denial_never_executes_it(self):
        suite = self.suites['shopping']
        target = suite.injection_tasks['injection_task_0']
        # This real registered click URL executes a download handler.
        steps = fixed_steps(lambda env: [call('browse_webpage', url='www.best_discount.com/click/')])
        for decision, expected_audits in [('allow', 1), ('deny', 1), ('abstain', 1)]:
            with self.subTest(decision=decision):
                script = Script(steps, decision=decision)
                suite.run_task_with_pipeline(script, target, target, {})
                self.assertEqual(script.audit_calls, expected_audits)
                if decision == 'allow':
                    self.assertNotEqual(script.env.filesystem.model_dump(), script.pre_filesystem)
                else:
                    self.assertEqual(script.env.filesystem.model_dump(), script.pre_filesystem)
                    self.assertNotIn('READ_AUDIT_BYPASS', str(script.extra))

    def test_unauthorized_web_tool_and_invalid_metadata_fail_closed(self):
        suite = self.suites['shopping']
        target = suite.injection_tasks['injection_task_0']
        steps = fixed_steps(lambda env: [call('browse_webpage', url='www.best_discount.com/click/')])
        script = Script(steps, decision='allow', permitted=[])
        suite.run_task_with_pipeline(script, target, target, {})
        self.assertEqual(script.env.filesystem.model_dump(), script.pre_filesystem)
        script = Script(steps, decision='allow', metadata={'browse_webpage': {'effect': 'invalid'}})
        with self.assertRaises(ToolMetadataError):
            suite.run_task_with_pipeline(script, target, target, {})

    def test_native_caught_errors_do_not_enter_cli_efficacy_denominators(self):
        from experiments import run_partial_benchmark as runner
        class NativeErrorAgent(BasePipelineElement):
            name = 'gpt-4o'
            dscg_model_config = {'model_id': 'gpt-4o-2024-05-13'}
            def query(self, *args, **kwargs):
                raise json.JSONDecodeError('offline authored native failure', '', 0)
        tracker = SimpleNamespace(total_prompt_tokens=0, total_completion_tokens=0, get_total_tokens=lambda: 0)
        root = Path(__file__).resolve().parents[1] / 'workshop/artifacts/20261018_dual_benchmark/native_errors'
        root.mkdir(parents=True, exist_ok=True)
        output = StringIO()
        with TemporaryDirectory(dir=root) as directory, redirect_stdout(output), patch.object(
                runner, 'make_openai_compatible_pipeline', return_value=(NativeErrorAgent(), tracker)), patch.object(
                runner, '_describe_pipeline', return_value=SimpleNamespace(
                    name='gpt-4o', dscg_model_config=NativeErrorAgent.dscg_model_config)):
            status = runner.main(origin=True, suites=['shopping'], attack='important_instructions',
                                 run_name='native_error', results_dir=directory)
            self.assertEqual(status, 1)
            paths = list(Path(directory).glob('agentdyn/*/*/shopping/summary.json'))
            self.assertTrue(paths, output.getvalue())
            summary_path = paths[0]
            summary = json.loads(summary_path.read_text())
            self.assertEqual(summary['task_counts']['total_tasks'], 9)
            self.assertEqual(summary['task_counts']['execution_errors'], 9)
            self.assertEqual(summary['task_counts']['utility_valid'], 0)
            self.assertEqual(summary['task_counts']['attacked_tasks'], 0)
            self.assertIsNone(summary['metrics']['attack_success_rate'])
            self.assertIsNone(summary['metrics']['utility_rate'])
            trace = json.loads(next(summary_path.parent.glob('user_task_*/*/injection_task_*.json')).read_text())
            self.assertTrue(trace['error'])
            self.assertIs(trace['security'], True)  # preserve the upstream raw label

    def test_dashboard_native_errors_preserve_count_but_exclude_efficacy(self):
        import dashboard.app as web
        from dashboard.evaluation import normalize_config
        class ErrorAgent(BasePipelineElement):
            name = 'gpt-4o-2024-05-13'
            def query(self, *args, **kwargs):
                raise json.JSONDecodeError('offline dashboard error', '', 0)
        tracker = SimpleNamespace(total_prompt_tokens=0, total_completion_tokens=0, get_total_tokens=lambda: 0)
        config = normalize_config(dict(suites=['shopping'], origin=True, run_attack=True,
            attack_name='important_instructions', max_user_tasks=1, max_injection_tasks=1))
        root = Path(__file__).resolve().parents[1] / 'workshop/artifacts/20261018_dual_benchmark/native_errors'
        root.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(dir=root) as directory, patch.object(web, 'DASHBOARD_RESULTS_DIR', Path(directory)), \
                patch.object(web, 'make_openai_compatible_pipeline', return_value=(ErrorAgent(), tracker)), \
                patch.object(web.threading, 'Thread'):
            try:
                web.run_test_thread('offline-native-error', config)
                result = json.loads((Path(directory)/'offline-native-error/overall_results.json').read_text())
                summary = result['suites'][0]
                self.assertEqual(summary['task_counts']['total_tasks'], 1)
                self.assertEqual(summary['task_counts']['execution_errors'], 1)
                self.assertEqual(summary['task_counts']['security_valid'], 0)
                self.assertIsNone(summary['metrics']['utility_rate'])
                self.assertIsNone(result['aggregate_metrics']['avg_attack_success_rate'])
                self.assertEqual(result['structured_records'][0]['sample_status'], 'infrastructure_error')
            finally:
                web.runs_store.pop('offline-native-error', None)


if __name__ == '__main__':
    unittest.main()


class AgentDojoNativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if get_backend().id != 'agentdojo':
            raise unittest.SkipTest('AgentDojo-specific native tests; AgentDyn native tests cover this environment')
        cls.suites = {name: get_suite('v1.2', name) for name in get_suites()}

    def test_real_clean_ground_truth_and_native_utility_in_four_suites(self):
        from agentdojo.agent_pipeline.ground_truth_pipeline import GroundTruthPipeline
        for name, suite in self.suites.items():
            with self.subTest(suite=name):
                task=suite.user_tasks['user_task_0']
                utility,_=suite.run_task_with_pipeline(GroundTruthPipeline(task),task,None,{})
                self.assertIs(utility,True)

    def test_native_injection_goals_positive_and_idle_negative(self):
        from agentdojo.agent_pipeline.ground_truth_pipeline import GroundTruthPipeline
        for name,suite in self.suites.items():
            with self.subTest(suite=name):
                target=suite.injection_tasks['injection_task_0'] if 'injection_task_0' in suite.injection_tasks else next(iter(suite.injection_tasks.values()))
                _,success=suite.run_task_with_pipeline(GroundTruthPipeline(target),target,target,{})
                self.assertIs(success,True)
                idle=Script(fixed_steps(lambda env: []))
                _,failure=suite.run_task_with_pipeline(idle,target,target,{})
                self.assertIs(failure,False)

    def test_real_native_tool_calls_cannot_run_without_tool_authorization(self):
        for name,suite in self.suites.items():
            with self.subTest(suite=name):
                target=suite.injection_tasks['injection_task_0'] if 'injection_task_0' in suite.injection_tasks else next(iter(suite.injection_tasks.values()))
                script=Script(fixed_steps(target.ground_truth),decision='allow',permitted=[])
                _,success=suite.run_task_with_pipeline(script,target,target,{})
                self.assertIs(success,False)
                self.assertTrue(any(m['role']=='tool' for m in script.messages))
