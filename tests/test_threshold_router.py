"""Direct-threshold routing preserves authorization and mediated execution."""
import json
import math
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from agentdojo.functions_runtime import EmptyEnv, FunctionCall, FunctionsRuntime
from dscg import audit_router as a
from dscg.pipelines import defended as d
from dscg.tool_metadata import set_tool_metadata


class ThresholdRouterTests(unittest.TestCase):
    def setUp(self):
        self.runtime = FunctionsRuntime()
        self.effects = []

        @self.runtime.register_function
        def read_data() -> str:
            """Read budget report"""
            self.effects.append('read')
            return 'fact'

        self.metadata = dict(effect='read', source='local', sink='none',
                             sensitivity='internal', idempotent=True, reversible=True)
        set_tool_metadata(self.runtime, {'read_data': self.metadata})
        self.sandbox = d.PermissionSandbox(['read_data'])
        self.call = FunctionCall(function='read_data', args={}, id='one')
        self.packet = dict(trusted_user_request='Read budget report', current_actions=[
            dict(tool_name='read_data', host_tool_description='Read budget report', untrusted_argument_data={})],
            recent_tool_results=[], action_history=[])
        self.flags = {key: False for key in a.COMPLETENESS_FLAGS}

    def assess(self, router):
        return router.assess(self.packet, self.flags, self.runtime, [self.call], self.sandbox)

    def test_ordinary_read_needs_no_artifact(self):
        row = self.assess(a.LocalAuditRouter('shadow'))
        self.assertTrue(row['eligible'])
        self.assertTrue(row['would_bypass'])
        self.assertEqual(row['threshold'], .70)
        self.assertEqual(row['score'], 0)
        self.assertFalse(row['actual_bypass'])

    def test_threshold_and_nonfinite_scores_are_diagnostic(self):
        router = a.LocalAuditRouter('selective', threshold=.70)
        for score, expected in ((.69, True), (.70, True), (.71, True), (math.nan, True), (math.inf, True)):
            with self.subTest(score=score), patch.object(a, 'risk_score', return_value=(score, {})):
                self.assertEqual(self.assess(router)['would_bypass'], expected)

    def test_invalid_threshold_and_old_artifact_are_rejected(self):
        for threshold in (True, False, '0.7', None, -.1, 1.1, math.nan, math.inf):
            with self.subTest(threshold=threshold), self.assertRaises(ValueError):
                a.LocalAuditRouter('shadow', threshold=threshold)
        with self.assertRaisesRegex(ValueError, 'threshold'):
            a.LocalAuditRouter('selective', artifact_path='old.json')
        self.assertTrue(self.assess(a.LocalAuditRouter('selective', threshold=0))['would_bypass'])
        self.assertTrue(self.assess(a.LocalAuditRouter('selective', threshold=1))['would_bypass'])

    def test_scope_and_incomplete_inputs_still_audit(self):
        for field, value in (('sensitivity', 'secret'), ('sink', 'external_recipient'),
                             ('effect', 'write'), ('idempotent', False)):
            with self.subTest(field=field):
                set_tool_metadata(self.runtime, {'read_data': {**self.metadata, field: value}})
                self.assertFalse(self.assess(a.LocalAuditRouter('selective'))['would_bypass'])
        set_tool_metadata(self.runtime, {'read_data': self.metadata})
        self.flags['arguments_truncated'] = True
        self.assertFalse(self.assess(a.LocalAuditRouter('selective'))['would_bypass'])

    def test_unauthorized_missing_metadata_cannot_bypass_and_read_batch_can(self):
        router = a.LocalAuditRouter('selective')
        self.assertFalse(router.assess(self.packet, self.flags, self.runtime, [self.call],
                                      d.PermissionSandbox([]))['would_bypass'])
        self.assertTrue(router.assess(self.packet, self.flags, self.runtime,
                                      [self.call, self.call], self.sandbox)['would_bypass'])
        set_tool_metadata(self.runtime, {})
        self.assertFalse(self.assess(router)['would_bypass'])

    def test_selective_skips_auditor_but_shadow_preserves_protocol_block(self):
        for mode, requests, effects in (('selective', 0, ['read']), ('shadow', 1, [])):
            self.effects.clear()
            router = a.LocalAuditRouter(mode)
            sandbox = d.PermissionSandbox(['read_data'])
            pre = d.ToolAuthorizationPrecheck(sandbox)
            verifier = a.RouterReceiptVerifier()

            class Auditor(d.ActionSecurityChecker):
                def _request_audit(self, query, extra, packet):
                    self.requests += 1
                    return json.dumps(dict(decision='allow', violations=[], confidence=.9, reason_code='invalid code'))

            checker = Auditor(SimpleNamespace(name='offline', client=None), sandbox=sandbox,
                precheck=pre, audit_router=router, router_verifier=verifier)
            checker.requests = 0
            monitor = d.ReferenceMonitor(sandbox, True, precheck=pre, audit_router=router, router_verifier=verifier)
            state = ('Read budget report', self.runtime, EmptyEnv(), [dict(role='assistant', content=[],
                tool_calls=[FunctionCall(function='read_data', args={}, id=mode)])], {})
            for element in (pre, checker, monitor, d.TicketedToolsExecutor(monitor)):
                state = element.query(*state)
            self.assertEqual(checker.requests, requests)
            self.assertEqual(self.effects, effects)
            event = state[4]['dscg_router_events'][0]
            self.assertEqual(event['actual_bypass'], mode == 'selective')
            if mode == 'shadow':
                self.assertTrue(event['would_bypass'])
                self.assertEqual(event['audit_parser_status'], 'failure')


if __name__ == '__main__':
    unittest.main()
