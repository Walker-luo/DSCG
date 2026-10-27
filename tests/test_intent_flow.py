"""Intent-flow production contracts with offline native tools, never SDK/network."""
import importlib.util
import json
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from agentdojo.functions_runtime import FunctionsRuntime, FunctionCall, EmptyEnv
from baseintent.pipelines import defended as d
from baseintent.tool_metadata import set_tool_metadata


def expectations(count):
    return {f"intent_{i+1}":dict(prepare_tools=[],completion_groups=[]) for i in range(count)}


def reply(payload):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(
        content=json.dumps(payload), refusal=None), finish_reason='stop')])


def tools():
    runtime, effects = FunctionsRuntime(), []
    @runtime.register_function
    def get_webpage(url: str) -> str:
        """Read a public website.

        Args:
            url: Address to read.
        """
        effects.append(('read', url)); return 'hiking'
    @runtime.register_function
    def get_private() -> str:
        """Read personal account data."""
        effects.append(('private',)); return 'private'
    @runtime.register_function
    def send_message(body: str) -> None:
        """Send the requested message.

        Args:
            body: Message content.
        """
        effects.append(('send', body))
    set_tool_metadata(runtime, {
        'get_webpage': dict(effect='read', source='web', sink='external_recipient',
            sensitivity='public', idempotent=True, reversible=True),
        'get_private': dict(effect='read', source='local', sink='none',
            sensitivity='personal', idempotent=True, reversible=True),
        'send_message': dict(effect='external_send', source='local', sink='public_output',
            sensitivity='internal', idempotent=False, reversible=False)})
    return runtime, effects


class IntentAuthorizationTests(unittest.TestCase):
    def test_default_compiles_intents_then_global_tools_with_progress_only_mapping(self):
        runtime, _ = tools(); client = Mock()
        client.chat.completions.create.side_effect = [
            reply({'authorization_steps': [{'intent': 'Read the article', 'goal_kind': 'facts'}, {'intent': 'Send its summary', 'goal_kind': 'effect'}]}),
            reply({'tools': ['send_message'], 'step_tool_expectations':expectations(1)})]
        llm = SimpleNamespace(name='offline', client=client)
        grant = d.ToolAuthorizationCompiler(llm).compile(d.TrustedTaskRequest(
            'Read the article Alice mentioned, then send its summary.'), runtime)
        self.assertEqual(client.chat.completions.create.call_count, 2)
        self.assertEqual(grant.public_dict()['authorization_steps'],
            [{'intent': 'Read the article; Send its summary', 'goal_kind': 'effect'}])
        self.assertEqual(grant.allowed_tools, frozenset(runtime.functions))
        second = json.loads(client.chat.completions.create.call_args.kwargs['messages'][1]['content'])
        self.assertEqual(len(second['authorization_steps']), 1)
        self.assertIn('send_message', second['available_tools'])

    def test_invalid_intent_does_not_call_tool_selector_or_grant(self):
        runtime, _ = tools(); client = Mock()
        client.chat.completions.create.return_value = reply({
            'authorization_steps': [{'intent': 'send', 'tools': ['send_message']}]})
        with self.assertRaises(d.AuthorizationCompilationError):
            d.ToolAuthorizationCompiler(SimpleNamespace(name='offline', client=client)).compile(
                d.TrustedTaskRequest('Send it'), runtime)
        self.assertEqual(client.chat.completions.create.call_count, 1)

    def test_legacy_v34_is_an_explicit_frozen_one_call_control(self):
        runtime, _ = tools(); client = Mock()
        client.chat.completions.create.return_value = reply({'steps': [
            {'intent': 'send', 'tools': ['send_message']}]})
        grant = d.ToolAuthorizationCompiler(SimpleNamespace(name='offline', client=client),
            prompt_profile='legacy-v34').compile(d.TrustedTaskRequest('Send it'), runtime)
        self.assertIn('send_message', grant.allowed_tools)
        self.assertEqual(client.chat.completions.create.call_count, 1)

    def test_selector_failure_never_installs_partial_read_permissions(self):
        runtime, _ = tools(); client = Mock()
        client.chat.completions.create.side_effect = [
            reply({'authorization_steps': [{'intent': 'Send a summary', 'goal_kind': 'effect'}]}), reply({'tools': ['unknown']})]
        sandbox = d.PermissionSandbox(['send_message'])
        llm = SimpleNamespace(name='offline', client=client, query=Mock())
        from baseintent.intent_flow import IntentFlowError
        with self.assertRaises(IntentFlowError):
            d.OurFrameExecutor(llm, sandbox=sandbox).query('Send a summary', runtime, EmptyEnv(),
                [dict(role='user', content=[dict(type='text', content='Send a summary')])], {})
        self.assertEqual(sandbox.allowed_tools, [])
        llm.query.assert_not_called()

    def test_read_only_request_still_has_intents_and_no_action_grant(self):
        runtime, _ = tools(); client = Mock()
        client.chat.completions.create.side_effect = [
            reply({'authorization_steps': [{'intent': 'Read the article, do not send anything', 'goal_kind': 'facts'}]}),
            reply({'tools': [], 'step_tool_expectations':expectations(1)})]
        grant = d.ToolAuthorizationCompiler(SimpleNamespace(name='offline', client=client)).compile(
            d.TrustedTaskRequest('Read the article, do not send anything'), runtime)
        self.assertNotIn('send_message', grant.allowed_tools)
        self.assertEqual(len(grant.authorization_intents), 1)

    def test_unmatched_host_profile_preserves_compliant_single_tools_fallback(self):
        from baseintent.l2_authorization import ToolAuthorizationProfile
        runtime, _ = tools(); client = Mock()
        def compliant_reply(**kwargs):
            policy = kwargs['messages'][0]['content']
            return reply({'authorization_steps':[{'intent':'Send greeting','goal_kind':'effect'}]} if 'authorization_steps' in policy
                         else {'tools':['send_message']})
        client.chat.completions.create.side_effect = compliant_reply
        profile = ToolAuthorizationProfile('fixed', ('Only this request',), frozenset({'send_message'}))
        for prompt_profile in ('legacy', 'intent-evidence-v35'):
            client.chat.completions.create.reset_mock()
            with self.subTest(profile=prompt_profile):
                grant = d.ToolAuthorizationCompiler(SimpleNamespace(name='offline', client=client),
                    authorization_profile=profile, prompt_profile=prompt_profile).compile(
                        d.TrustedTaskRequest('A different greeting request'), runtime)
                self.assertEqual(grant.profile_status, 'unsupported_task_fallback')
                self.assertIn('send_message', grant.allowed_tools)
                self.assertEqual(client.chat.completions.create.call_count, 1)
                self.assertEqual(grant.authorization_intents, ())

    def test_bounded_fallback_identity_binds_its_actual_tools_policy(self):
        from baseintent.model_config import ModelConfig
        from unittest.mock import patch
        config = ModelConfig('offline','offline','https://offline.invalid','custom')
        def binding():
            return d.router_configuration_hash(config, config, input_isolation=True,
                authorization_precheck=True, l1_projection_mode='projected', planning_tool_view=True,
                delegated_tasks=True, profile_hash='host-profile', prompt_profile='legacy')
        before = binding()
        with patch.object(d.ToolAuthorizationCompiler,'CLASSIC_POLICY','Changed fallback tools policy'):
            self.assertNotEqual(before,binding())


class IntentStateTests(unittest.TestCase):
    def test_current_return_and_final_answer_survive_a_full_old_evidence_window(self):
        from baseintent.intent_flow import IntentFlow
        messages = [dict(role='tool', content=[dict(type='text',content='x'*2048)],
            tool_call_id='old-'+str(i), error=None) for i in range(8)]
        messages.extend([dict(role='tool',content=[dict(type='text',content='Current fact: 1050')],
            tool_call_id='current',error=None),
            dict(role='assistant',content=[dict(type='text',content='The total spending is 1050.')],tool_calls=None)])
        client = Mock(); client.chat.completions.create.return_value = reply(dict(
            satisfaction='not_yet',evidence_ids=[]))
        flow = IntentFlow(('Calculate total',), 'Calculate total', goal_kinds=('answer',))
        flow.observe(SimpleNamespace(name='offline',client=client),messages,[],final=True)
        packet = json.loads(client.chat.completions.create.call_args.kwargs['messages'][1]['content'])
        self.assertEqual(packet['evidence'][-1]['content'],'The total spending is 1050.')
        self.assertEqual(packet['evidence'][-2]['content'],'Current fact: 1050')
        self.assertLessEqual(sum(len(r['content']) for r in packet['evidence']),16384)
        self.assertTrue(any(r['content_truncated'] for r in packet['evidence'][:-2]))
        self.assertTrue(packet['host_observation']['answer_emitted'])


class IntentReadBoundaryTests(unittest.TestCase):
    def run_calls(self, calls, verdict='deny', mode='off', mutate=None, active_flow=None):
        runtime, effects = tools(); sandbox = d.PermissionSandbox(list(runtime.functions))
        verifier = d.RouterReceiptVerifier()
        router = d.LocalAuditRouter(mode) if mode != 'off' else None
        packets = []
        class Checker(d.ActionSecurityChecker):
            def _request_audit(self, query, env, packet):
                packets.append(packet)
                return json.dumps(dict(decision=verdict, violations=[] if verdict == 'allow' else ['OFF_TASK_ACTION'],
                    confidence=.9, reason_code='ALIGNED' if verdict == 'allow' else 'OFF_TASK_ACTION'))
        checker = Checker(SimpleNamespace(name='offline'), sandbox=sandbox,
            router_verifier=verifier, audit_router=router, intent_flow_getter=lambda: active_flow)
        monitor = d.ReferenceMonitor(sandbox, True, router_verifier=verifier,
            audit_router=router, intent_read_policy=True, intent_flow_getter=lambda: active_flow)
        state = ('Read the blog and send its summary', runtime, EmptyEnv(),
            [dict(role='assistant', content=[], tool_calls=calls)], {})
        state = checker.query(*state)
        if mutate: mutate(state[-1])
        for element in (monitor, d.TicketedToolsExecutor(monitor)): state = element.query(*state)
        return effects, packets, state

    def test_public_blog_and_query_url_bypass_in_every_router_mode(self):
        for mode in ('off', 'shadow', 'selective'):
            for url in ('www.eve-blog.com', 'http://127.0.0.1/?value=123'):
                effects, packets, _ = self.run_calls([FunctionCall(function='get_webpage',
                    args={'url': url}, id='read')], mode=mode)
                self.assertEqual(effects, [('read', url)])
                self.assertEqual(packets, [])

    def test_private_deny_is_enforced_and_mixed_read_is_independent(self):
        effects, packets, _ = self.run_calls([FunctionCall(function='get_private', args={}, id='private')])
        self.assertEqual(effects, []); self.assertEqual(len(packets), 1)
        effects, packets, _ = self.run_calls([
            FunctionCall(function='get_webpage', args={'url': 'www.eve-blog.com'}, id='read'),
            FunctionCall(function='send_message', args={'body': 'attack'}, id='write')])
        self.assertEqual(effects, [('read', 'www.eve-blog.com')])
        self.assertEqual([a['tool_name'] for a in packets[0]['current_actions']], ['send_message'])

    def test_invalid_arguments_or_tampered_receipt_execute_nothing(self):
        effects, _, _ = self.run_calls([FunctionCall(function='get_webpage', args={}, id='read')], verdict='allow')
        self.assertEqual(effects, [])

    def test_mixed_execution_order_and_actual_intent_state_are_bound(self):
        calls = [FunctionCall(function='send_message', args={'body':'summary'}, id='write'),
                 FunctionCall(function='get_webpage', args={'url':'www.eve-blog.com'}, id='read')]
        effects, _, _ = self.run_calls(calls, verdict='allow')
        self.assertEqual(effects, [('send','summary'),('read','www.eve-blog.com')])
        from baseintent.intent_flow import IntentFlow
        flow = IntentFlow(('Read blog', 'Send summary'), 'Read and send', goal_kinds=('facts','effect'))
        effects, _, _ = self.run_calls([calls[1]], active_flow=flow,
            mutate=lambda extra: setattr(flow, 'revision', flow.revision+1))
        self.assertEqual(effects, [])

    def test_internal_private_channel_classification_is_tool_level(self):
        runtime, _ = tools()
        from baseintent.intent_flow import exempt_read
        set_tool_metadata(runtime, {'get_webpage': dict(effect='read', source='web',
            sink='external_recipient', sensitivity='internal', idempotent=False, reversible=True)})
        self.assertTrue(exempt_read(runtime, FunctionCall(function='get_webpage',
            args={'url':'http://internal/private?token=example'}, id='private-name')))
        runtime._baseintent_tool_metadata.pop('get_webpage')
        self.assertFalse(exempt_read(runtime, FunctionCall(function='get_webpage', args={'url':'x'}, id='x')))
        effects, _, _ = self.run_calls([FunctionCall(function='get_webpage', args={'url': 'x'}, id='read')],
            mutate=lambda extra: extra['_baseintent_audit_decision'].update(decision='deny'))
        self.assertEqual(effects, [])

    def test_execution_ticket_cannot_survive_an_intent_state_change(self):
        from baseintent.intent_flow import IntentFlow
        runtime, effects = tools(); sandbox = d.PermissionSandbox(list(runtime.functions))
        flow = IntentFlow(('Read the blog', 'Send its summary'), 'Read and send', goal_kinds=('facts','effect'))
        verifier = d.RouterReceiptVerifier()
        checker = d.ActionSecurityChecker(SimpleNamespace(name='offline'), sandbox=sandbox,
            router_verifier=verifier, intent_flow_getter=lambda: flow)
        monitor = d.ReferenceMonitor(sandbox, True, router_verifier=verifier,
            intent_read_policy=True, intent_flow_getter=lambda: flow)
        state = ('Read and send', runtime, EmptyEnv(), [dict(role='assistant',content=[],tool_calls=[
            FunctionCall(function='get_webpage',args={'url':'www.eve-blog.com'},id='read')])], {})
        state = monitor.query(*checker.query(*state))
        self.assertTrue(state[-1]['_baseintent_pending_batch'].actions[0].approved)
        flow.revision += 1
        state = d.TicketedToolsExecutor(monitor).query(*state)
        self.assertEqual(effects, [])
        self.assertEqual(state[3][-1]['error'], 'MONITOR_BLOCKED:INVALID_EXECUTION_TICKET')


class IntentTaskErrorTests(unittest.TestCase):
    def test_progress_failure_has_null_labels_and_next_task_runs(self):
        from baseintent.intent_flow import IntentFlowError
        from experiments.common import benchmark_tasks as adapter
        class Pipeline:
            name = 'offline'
            elements = []
            def query(self):
                raise IntentFlowError('INTENT_API_ERROR')
        suite = SimpleNamespace(name='offline', get_user_task_by_id=lambda x: SimpleNamespace(ID=x))
        def native(suite, pipeline, user, *args):
            if user.ID == 'user_task_0': pipeline.query()
            return True, None
        with unittest.mock.patch.object(adapter.benchmark, 'run_task_without_injection_tasks', side_effect=native):
            result = adapter.run_native_suite(Pipeline(), suite, None, None, False,
                user_tasks=['user_task_0', 'user_task_1'], injection_tasks=[], benchmark_version='v1.2')
        self.assertIsNone(result['utility_results'][('user_task_0', '')])
        self.assertTrue(result['utility_results'][('user_task_1', '')])
        self.assertEqual(result['task_errors'][0]['intent_stage'], 'intent_progress')
        self.assertEqual(result['task_errors'][0]['reason_code'], 'INTENT_API_ERROR')
