import json
import unittest
from types import SimpleNamespace
from unittest.mock import Mock
from agentdojo.functions_runtime import FunctionsRuntime, FunctionCall, EmptyEnv
from dscg.pipelines.defended import ActionSecurityChecker, PermissionSandbox, ReferenceMonitor
from dscg.tool_metadata import set_tool_metadata

class BoundedReauditTests(unittest.TestCase):
    def setUp(self):
        self.runtime=FunctionsRuntime()
        @self.runtime.register_function
        def read_private() -> str:
            """Read necessary private task facts."""
            return 'facts'
        set_tool_metadata(self.runtime,{'read_private':dict(effect='read',source='local',sink='none',sensitivity='secret',idempotent=True,reversible=True)})
        self.messages=[{'role':'assistant','content':[], 'tool_calls':[FunctionCall(function='read_private',args={},id='1')]}]
    def checker(self, outcomes, enabled=True):
        checker=ActionSecurityChecker(SimpleNamespace(name='fixture'), sandbox=PermissionSandbox(['read_private']), max_semantic_retries=1 if enabled else 0)
        checker._request_audit=Mock(side_effect=[json.dumps(dict(decision=o,violations=[],confidence=1.0,reason_code='FIXTURE')) if isinstance(o,str) and o in ['allow','abstain','deny'] else o for o in outcomes])
        return checker
    def test_one_semantic_abstain_can_be_clarified_without_dropping_history(self):
        checker=self.checker(['abstain','allow'])
        state=checker.query('Read task facts',self.runtime,EmptyEnv(),self.messages,{'dscg_action_ledger':[{'tool_name':'old','state':'executed'}]})
        self.assertEqual(checker._request_audit.call_count,2)
        self.assertEqual(state[-1]['_dscg_audit_decision']['decision'],'allow')
        packet=checker._request_audit.call_args.args[-1]
        self.assertEqual(len(packet['action_history']),1)
        self.assertIn('clarification',packet)
        self.assertEqual(len(state[-1]['dscg_audit_decisions']),2)
    def test_persistent_uncertainty_is_blocked_and_retry_is_bounded(self):
        checker=self.checker(['abstain','abstain','allow'])
        state=checker.query('Read facts',self.runtime,EmptyEnv(),self.messages,{})
        state=ReferenceMonitor(checker.sandbox,True).query(*state)
        self.assertEqual(checker._request_audit.call_count,2)
        self.assertEqual(state[-1]['dscg_action_ledger'][0]['state'],'blocked')
    def test_parser_timeout_denial_and_default_do_not_retry(self):
        for outcomes,enabled in [(['garbage','allow'],True),([TimeoutError(),'allow'],True),(['deny','allow'],True),(['abstain','allow'],False)]:
            checker=self.checker(outcomes,enabled)
            checker.query('Read facts',self.runtime,EmptyEnv(),self.messages,{})
            self.assertEqual(checker._request_audit.call_count,1)
    def test_reaudit_allow_cannot_authorize_ungranted_tool(self):
        checker=self.checker(['abstain','allow']);checker.sandbox.allowed_tools=[]
        state=checker.query('Read facts',self.runtime,EmptyEnv(),self.messages,{})
        state=ReferenceMonitor(checker.sandbox,True).query(*state)
        self.assertEqual(state[-1]['dscg_action_ledger'][0]['state'],'blocked')
    def test_truncated_current_history_is_not_removed_for_retry(self):
        checker=self.checker(['abstain','allow'])
        checker.query('Read facts',self.runtime,EmptyEnv(),self.messages,
                      {'dscg_action_ledger':[{'state':'executed'}]*33})
        self.assertEqual(checker._request_audit.call_count,1)
    def test_public_read_bypass_has_no_semantic_attempt_or_model_call(self):
        set_tool_metadata(self.runtime,{'read_private':dict(effect='read',source='local',sink='none',sensitivity='public',idempotent=True,reversible=True)})
        checker=self.checker(['allow'])
        state=checker.query('Read facts',self.runtime,EmptyEnv(),self.messages,{})
        checker._request_audit.assert_not_called()
        self.assertEqual(state[-1]['_dscg_audit_decision']['reason_code'],'READ_AUDIT_BYPASS')
