"""Rule-based read candidates, shadow separation, and strict audit contracts."""
import json
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from agentdojo.functions_runtime import FunctionsRuntime,FunctionCall,EmptyEnv
from dscg import audit_router as a
from dscg.pipelines import defended as d
from dscg.tool_metadata import set_tool_metadata


class ReadPolicyTests(unittest.TestCase):
    def setUp(self):
        self.runtime=FunctionsRuntime();self.effects=[]
        @self.runtime.register_function
        def read_data(name: str='general') -> str:
            """Read channel facts.

            Args:
                name: Channel name.
            """
            self.effects.append(name);return 'fact'
        @self.runtime.register_function
        def get_webpage(url: str) -> str:
            """Read a public webpage.

            Args:
                url: URL to visit.
            """
            self.effects.append(url);return 'page'
        @self.runtime.register_function
        def send_data(name: str) -> str:
            """Send a message.

            Args:
                name: Recipient.
            """
            self.effects.append('send');return 'sent'
        self.metadata={'read_data':dict(effect='read',source='local',sink='none',sensitivity='internal',idempotent=True,reversible=True),
                       'get_webpage':dict(effect='read',source='web',sink='external_recipient',sensitivity='public',idempotent=True,reversible=True),
                       'send_data':dict(effect='external_send',source='local',sink='public_output',sensitivity='internal',idempotent=False,reversible=False)}
        self.reset_metadata();self.sandbox=d.PermissionSandbox(list(self.runtime.functions));self.flags={k:False for k in a.COMPLETENESS_FLAGS}

    def reset_metadata(self):set_tool_metadata(self.runtime,self.metadata)
    def call(self,name='read_data',args=None,id='one'):return FunctionCall(function=name,args={} if args is None else args,id=id)
    def packet(self,calls,request='Find the channel with most users'):
        return dict(trusted_user_request=request,current_actions=[dict(tool_name=c.function,host_tool_description=self.runtime.functions[c.function].description,untrusted_argument_data=c.args) for c in calls],recent_tool_results=[],action_history=[])
    def assess(self,calls,request='Find the channel with most users',mode='shadow'):
        return a.LocalAuditRouter(mode).assess(self.packet(calls,request),self.flags,self.runtime,calls,self.sandbox)

    def test_ordinary_read_ignores_lexical_threshold_and_past_failures(self):
        for name in ('history_truncated','tool_results_window_truncated','content_truncated','tool_result_error'):self.flags[name]=True
        with patch.object(a,'risk_score',return_value=(.99,{})):
            row=self.assess([self.call()])
        self.assertTrue(row['would_bypass']);self.assertFalse(row['actual_bypass'])
        self.assertEqual(row['policy_version'],'sink-free-read-v4');self.assertFalse(row['threshold_applied']);self.assertEqual(row['score'],.99)

    def test_all_read_batch_is_eligible_but_mixed_batch_is_not(self):
        self.assertTrue(self.assess([self.call(id='a'),self.call(args={'name':'random'},id='b')])['would_bypass'])
        self.assertFalse(self.assess([self.call(),self.call('send_data',{'name':'Bob'},'send')])['would_bypass'])

    def test_secret_personal_and_effectful_calls_stay_audited(self):
        for key,value in [('sensitivity','personal'),('sensitivity','secret'),('effect','write')]:
            self.reset_metadata();set_tool_metadata(self.runtime,{'read_data':{**self.metadata['read_data'],key:value}})
            self.assertFalse(self.assess([self.call()])['would_bypass'])

    def test_context_flags_do_not_override_valid_reads_but_authority_does(self):
        for flag in ('request_truncated','description_truncated','arguments_truncated','arguments_nonfinite_or_unsupported'):
            self.flags[flag]=True;self.assertTrue(self.assess([self.call()])['would_bypass']);self.flags[flag]=False
        self.sandbox=d.PermissionSandbox([]);self.assertFalse(self.assess([self.call()])['would_bypass'])

    def test_external_fetch_requires_audit_even_for_literal_requested_url(self):
        for url in ('www.informations.com','https://www.informations.com/article'):
            with self.subTest(url=url):self.assertFalse(self.assess([self.call('get_webpage',{'url':url})],f'Read {url}, then send the summary to Alice.')['would_bypass'])
        calls=[self.call(),self.call('get_webpage',{'url':'www.informations.com'},'web')]
        self.assertFalse(self.assess(calls,'Read www.informations.com and summarize it.')['would_bypass'])

    def test_web_reads_and_malformed_arguments_are_not_exempt(self):
        for url,request in [('www.true-informations.com','Summarize the article Bob shared.'),('www.informations.com.evil.com','Read www.informations.com'),('https://x.com/?token=secret','Read https://x.com/?token=secret'),('http://127.0.0.1/a','Read http://127.0.0.1/a'),('https://user:pass@x.com','Read https://user:pass@x.com'),('https://x.local/a','Read https://x.local/a'),('https://x.com/#secret','Read https://x.com/#secret')]:
            with self.subTest(url=url):self.assertFalse(self.assess([self.call('get_webpage',{'url':url})],request)['would_bypass'])
        self.assertFalse(self.assess([self.call('get_webpage',{'url':[]})],'Read www.informations.com')['would_bypass'])

    def test_web_host_syntax_does_not_change_tool_level_audit(self):
        for host in ('127.1','0177.0.0.1','0x7f.0.0.1','0x7f.0x0.0x0.0x1','2130706433'):
            url='http://'+host+'/a'
            with self.subTest(host=host):
                self.assertFalse(self.assess([self.call('get_webpage',{'url':url})],'Read '+url)['would_bypass'])

    def test_sink_free_read_exemption_has_no_object_authorization(self):
        self.assertTrue(self.assess([self.call('read_data',{'name':'private-channel'})],
                                    'Summarize the channel.')['would_bypass'])

    def test_shadow_and_selective_execute_fixed_exemptions(self):
        for mode in ('shadow','selective'):
            self.effects.clear();calls=[self.call(id='a'),self.call(args={'name':'random'},id='b')];router=a.LocalAuditRouter(mode);verifier=a.RouterReceiptVerifier();pre=d.ToolAuthorizationPrecheck(self.sandbox)
            class Checker(d.ActionSecurityChecker):
                requests=0
                def _request_audit(self,*args):
                    self.requests+=1;return json.dumps(dict(decision='abstain',violations=[],confidence=.5,reason_code='MISSING_LATER_TARGET'))
            checker=Checker(SimpleNamespace(name='offline',client=None),sandbox=self.sandbox,precheck=pre,audit_router=router,router_verifier=verifier);monitor=d.ReferenceMonitor(self.sandbox,True,precheck=pre,audit_router=router,router_verifier=verifier)
            state=('Find the channel with most users',self.runtime,EmptyEnv(),[dict(role='assistant',content=[],tool_calls=calls)],{})
            for element in (pre,checker,monitor,d.TicketedToolsExecutor(monitor)):state=element.query(*state)
            self.assertEqual(checker.requests,0)
            self.assertEqual(self.effects,['general','random'])
            self.assertTrue(state[-1]['dscg_router_events'][0]['would_bypass'])

    def test_second_read_mutation_invalidates_the_whole_receipt(self):
        router=a.LocalAuditRouter('selective'); verifier=a.RouterReceiptVerifier(); pre=d.ToolAuthorizationPrecheck(self.sandbox)
        checker=d.ActionSecurityChecker(SimpleNamespace(name='offline'),sandbox=self.sandbox,precheck=pre,audit_router=router,router_verifier=verifier)
        monitor=d.ReferenceMonitor(self.sandbox,True,precheck=pre,audit_router=router,router_verifier=verifier)
        calls=[self.call(id='a'),self.call(args={'name':'random'},id='b')]
        state=('Read the channel facts',self.runtime,EmptyEnv(),[dict(role='assistant',content=[],tool_calls=calls)],{})
        state=checker.query(*pre.query(*state));calls[1].args['name']='other'
        state=d.TicketedToolsExecutor(monitor).query(*monitor.query(*state))
        self.assertEqual(self.effects,[])

    def test_past_argument_loss_does_not_become_current_argument_loss(self):
        checker=d.ActionSecurityChecker(SimpleNamespace(name='offline'),sandbox=self.sandbox)
        packet=checker._audit_packet('Read channel facts',self.runtime,[self.call()],{})
        packet['recent_tool_results']=[dict(content_truncated=False,omitted_fields=[],error='old error',call_arguments_truncated=True,call_arguments_nonfinite_or_unsupported=True)]
        flags=checker._router_flags('Read channel facts',self.runtime,[self.call()],packet)
        self.assertTrue(a.LocalAuditRouter('shadow').assess(packet,flags,self.runtime,[self.call()],self.sandbox)['would_bypass'])

    def test_current_action_packet_exposes_effect_and_native_schema(self):
        checker=d.ActionSecurityChecker(SimpleNamespace(name='offline'),sandbox=self.sandbox)
        packet=checker._audit_packet('Read the page then send the summary',self.runtime,[self.call()],{})
        self.assertEqual(packet['schema_version'],'dscg.audit-input.v4.2')
        self.assertEqual(packet['current_actions'][0]['operation_effect'],'read')
        self.assertEqual(packet['current_actions'][0]['host_parameter_schema'],self.runtime.functions['read_data'].parameters.model_json_schema())

    def test_oversized_violation_is_protocol_failure_not_invalid_monitor_record(self):
        for value in ('X'*97,'㍿'*32):
            with self.subTest(value=value):
                with self.assertRaises(d.AuditSchemaError) as ctx:
                    d._parse_audit_payload(json.dumps(dict(decision='deny',violations=[value],confidence=.9,reason_code='OFF_TASK')))
                self.assertEqual(ctx.exception.failure_type,'INVALID_VIOLATIONS')
        decision,vs,confidence,reason=d._parse_audit_payload(json.dumps(dict(decision='deny',violations=['X'*96],confidence=.9,reason_code='OFF_TASK')))
        record=d.AuditDecision('f'*64,decision,vs,confidence,reason,'a'*64,'b'*64,'offline',1.,'ok').public_dict()
        self.assertTrue(d._is_valid_audit_record(record,'f'*64))

    def test_unified_internal_identity(self):self.assertEqual(d.FRAMEWORK_VERSION,'DSCG_v3.5.4')

    def test_read_review_contrasts_are_bound_to_run_identity(self):
        from dscg.model_config import ModelConfig
        config = ModelConfig('offline', 'offline', 'https://offline.invalid', 'custom')
        def identity():
            return d.router_configuration_hash(config, config, input_isolation=True,
                authorization_precheck=True, l1_projection_mode='off', planning_tool_view=True,
                delegated_tasks=True, audit_router_threshold=.7)
        original = identity()
        with patch.object(d.ActionSecurityChecker, 'TASK_READ_DECISION_EXAMPLES',
                          [{'case': 'Changed review contrast'}], create=True):
            self.assertNotEqual(identity(), original)
