"""Host mediation contracts; offline auditors do not establish semantic quality."""
import json
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from agentdojo.functions_runtime import EmptyEnv, FunctionCall, FunctionsRuntime
from dscg.audit_router import LocalAuditRouter, RouterReceiptVerifier
from dscg.pipelines import defended as d
from dscg.tool_metadata import set_tool_metadata


class ReadExemptionTests(unittest.TestCase):
    def chain(self, mode='off', sensitivity='public', decision='deny', authorized=True, external=False):
        runtime = FunctionsRuntime()
        effects, packets = [], []
        @runtime.register_function
        def fetch(url: str) -> str:
            """Read reference data.

            :param url: Source URL.
            """
            effects.append('read')
            return 'facts'
        @runtime.register_function
        def send() -> str:
            """Send a message."""
            effects.append('send')
            return 'sent'
        set_tool_metadata(runtime, {
            'fetch': dict(effect='read', source='local', sink='external_recipient' if external else 'none',
                          sensitivity=sensitivity, idempotent=True, reversible=True),
            'send': dict(effect='external_send', source='local', sink='external_recipient',
                         sensitivity='internal', idempotent=False, reversible=False)})
        sandbox = d.PermissionSandbox(['fetch', 'send'] if authorized else ['fetch'])
        pre = d.ToolAuthorizationPrecheck(sandbox)
        router = LocalAuditRouter(mode)
        verifier = RouterReceiptVerifier()
        class Auditor(d.ActionSecurityChecker):
            def _request_audit(self, query, env, packet):
                packets.append(packet)
                return json.dumps(dict(decision=decision,
                    violations=['OFF_TASK_ACTION'] if decision == 'deny' else [],
                    confidence=1., reason_code='OFF_TASK_ACTION' if decision == 'deny' else 'ALIGNED'))
        checker = Auditor(SimpleNamespace(name='offline'), sandbox=sandbox, precheck=pre,
                          audit_router=router, router_verifier=verifier)
        monitor = d.ReferenceMonitor(sandbox, True, precheck=pre, audit_router=router, router_verifier=verifier)
        return runtime, effects, packets, (pre, checker, monitor, d.TicketedToolsExecutor(monitor))

    def run_case(self, mode='off', sensitivity='public', mixed=False, authorized=True, mutate=False, malformed=False):
        runtime, effects, packets, chain = self.chain(mode, sensitivity, authorized=authorized)
        calls = [FunctionCall(function='fetch', args={'url':'https://discovered.test/path?q=data'}, id='r')]
        if mixed:
            calls.append(FunctionCall(function='send', args={}, id='w'))
        if malformed:
            calls.append(FunctionCall(function='fetch', args={}, id='invalid'))
        state = ('Read the referenced article and send its summary', runtime, EmptyEnv(),
                 [{'role':'assistant','content':[], 'tool_calls':calls}], {})
        for component in chain[:2]:
            state = component.query(*state)
        if mutate:
            state[3][-1]['tool_calls'][0].args['url'] = 'https://changed.test'
        for component in chain[2:]:
            state = component.query(*state)
        return effects, packets, state

    def test_sink_free_read_bypasses_in_every_mode_without_literal_locator(self):
        for mode in ['off','shadow','selective']:
            effects, packets, _ = self.run_case(mode)
            self.assertEqual(effects, ['read'], mode)
            self.assertEqual(packets, [], mode)

    def test_mixed_batch_audits_only_effect_and_preserves_allowed_read(self):
        for mode in ['off','shadow','selective']:
            effects, packets, state = self.run_case(mode, mixed=True)
            self.assertEqual(effects, ['read'], mode)
            self.assertEqual(len(packets), 1)
            self.assertEqual([a['tool_name'] for a in packets[0]['current_actions']], ['send'])
            self.assertEqual(state[3][-1]['error'], 'L3_BLOCKED:AUDIT_DENY')

    def test_sensitive_read_deny_is_enforced(self):
        for sensitivity in ['personal','secret']:
            effects, packets, _ = self.run_case(sensitivity=sensitivity)
            self.assertEqual(effects, [])
            self.assertEqual(len(packets), 1)

    def test_unauthorized_mixed_batch_still_rejects_every_member(self):
        effects, packets, _ = self.run_case(mixed=True, authorized=False)
        self.assertEqual(effects, [])
        self.assertEqual(packets, [])

    def test_schema_invalid_batch_rejects_valid_siblings_before_audit(self):
        effects, packets, _ = self.run_case(mixed=True, malformed=True)
        self.assertEqual(effects, [])
        self.assertEqual(packets, [])

    def test_mixed_batch_receipt_binds_exempt_read_arguments(self):
        for mode in ['off','shadow','selective']:
            effects, _, _ = self.run_case(mode, mixed=True, mutate=True)
            self.assertEqual(effects, [], mode)

    def test_factory_off_mode_issues_a_consumable_handoff(self):
        from dscg.model_config import ModelConfig
        config = ModelConfig('offline', 'offline', 'https://offline.invalid', 'custom')
        with patch.object(d, 'create_openai_client', return_value=Mock()):
            pipeline, _, _ = d.make_defended_pipeline(model_config=config, sec_model_config=config)
        from experiments import run_partial_benchmark as partial
        with patch.object(partial, 'resolve_model_config', return_value=config):
            descriptor = partial._describe_pipeline('offline', None, origin=False, defense=None,
                use_sandbox=True, use_security_checker=True, l1_projection_mode='projected',
                planning_tool_view=True, delegated_tasks=True, audit_retries=0,
                completion_prompt=False, audit_router_mode='off', audit_router_threshold=.7)
        for key, value in descriptor.dscg_optimization_config.items():
            self.assertEqual(pipeline.dscg_optimization_config[key], value, key)
        monitor = pipeline.reference_monitor
        runtime, effects, _, _ = self.chain()
        monitor.sandbox.allowed_tools = ['fetch']
        checker = d.ActionSecurityChecker(SimpleNamespace(name='offline'), sandbox=monitor.sandbox,
            precheck=monitor.precheck, audit_router=monitor.audit_router, router_verifier=monitor.router_verifier)
        state = ('Read the article', runtime, EmptyEnv(), [{'role':'assistant', 'content':[],
            'tool_calls':[FunctionCall(function='fetch', args={'url':'https://article.test'}, id='read')]}], {})
        for component in (monitor.precheck, checker, monitor, d.TicketedToolsExecutor(monitor)):
            state = component.query(*state)
        self.assertEqual(effects, ['read'])


if __name__ == '__main__':
    unittest.main()
