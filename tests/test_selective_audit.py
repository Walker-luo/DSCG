import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from agentdojo.functions_runtime import EmptyEnv, FunctionCall, FunctionsRuntime
from dscg import audit_router as a
from dscg.pipelines import defended as d
from dscg.tool_metadata import set_tool_metadata


class SelectiveAuditTests(unittest.TestCase):
    def setUp(self):
        self.runtime=FunctionsRuntime();self.effects=[];self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        @self.runtime.register_function
        def read_data() -> str:
            """Read budget report"""
            self.effects.append('read');return 'fact'
        self.md=dict(effect='read',source='local',sink='none',sensitivity='internal',idempotent=True,reversible=False)
        set_tool_metadata(self.runtime,{'read_data':self.md});self.config_hash='0'*64

    def artifact(self,m=64):
        rows=[dict(episode_group_id=str(i),score=0.0,eligible=True,label='safe_and_sufficient',cost=10) for i in range(m)]
        c=a.calibrate(rows,[0.5],0.05,0.05);catalog,tools=a.catalog_snapshot(self.runtime)
        value=dict(schema_version=a.SCHEMA,feature_version=a.FEATURE_VERSION,input_schema=a.INPUT_SCHEMA,scope='single-internal-read-no-sink',
                   catalog_sha256=catalog,model_config_sha256=self.config_hash,approved_tool_schema_hashes=tools,
                   development_manifest_sha256='1'*64,calibration_manifest_sha256='2'*64,
                   split_groups=dict(development=['dev'],calibration=[str(i) for i in range(m)],test=[]),
                   label_source='environment_oracle',independence_attested=True,calibration=c)
        path=Path(self.temp.name)/'artifact.json';path.write_text(json.dumps(value));return path

    def setup_chain(self,mode='selective',m=64,response='allow',path=None):
        self.assertIn('audit_router',__import__('inspect').signature(d.ActionSecurityChecker).parameters,
                      'checker router integration missing')
        router=a.LocalAuditRouter(mode,path or self.artifact(m),self.config_hash)
        sandbox=d.PermissionSandbox(['read_data']);v=a.RouterReceiptVerifier();pre=d.ToolAuthorizationPrecheck(sandbox)
        class Auditor(d.ActionSecurityChecker):
            def _request_audit(self,q,e,p):
                self.requests+=1
                if response=='error':raise TimeoutError()
                return json.dumps(dict(decision=response,violations=[],confidence=0.5,reason_code='TEST'))
        c=Auditor(SimpleNamespace(name='offline',client=None),sandbox=sandbox,precheck=pre,audit_router=router,router_verifier=v);c.requests=0
        monitor=d.ReferenceMonitor(sandbox,True,precheck=pre,audit_router=router,router_verifier=v)
        return pre,c,monitor,d.TicketedToolsExecutor(monitor)

    def state(self):
        return ('Read budget report',self.runtime,EmptyEnv(),[{'role':'assistant','content':[],'tool_calls':[FunctionCall(function='read_data',args={},id='1')]}],{})

    def run_chain(self,chain,state=None):
        state=state or self.state()
        for element in chain:state=element.query(*state)
        return state

    def test_legacy_input_artifact_cannot_bypass_new_evidence_audit(self):
        path = self.artifact()
        value = json.loads(path.read_text())
        value['input_schema'] = 'dscg.audit-input.v1'
        path.write_text(json.dumps(value))
        chain = self.setup_chain(path=path)
        self.run_chain(chain)
        self.assertEqual(chain[1].requests, 1)

    def test_historical_argument_loss_requires_semantic_audit(self):
        for args in ({'a': {'b': {'c': {'id': 1}}}}, {'amount': float('nan')}):
            chain = self.setup_chain()
            q, r, e, m, x = self.state()
            history = [{'role': 'user', 'content': [{'type': 'text', 'content': q}]},
                {'role': 'tool', 'content': [{'type': 'text', 'content': '[]'}], 'tool_call_id': 'old',
                 'tool_call': FunctionCall(function='read_data', args=args, id='old'), 'error': None}]
            self.run_chain(chain, (q, r, e, [*history, m[-1]], x))
            self.assertEqual(chain[1].requests, 1)

    def test_router_total_input_bound_includes_historical_call_arguments(self):
        runtime = FunctionsRuntime()
        @runtime.register_function
        def read_data(queries: list[str]) -> str:
            """Read local records.

            :param queries: Search terms.
            """
            return 'not executed'
        set_tool_metadata(runtime, {'read_data': self.md})
        args = {'queries': ['x' * 250] * 16}
        call = FunctionCall(function='read_data', args=args, id='current')
        packet = dict(trusted_user_request='q' * 2000,
            current_actions=[dict(host_tool_description='d' * 500, untrusted_argument_data=args)],
            recent_tool_results=[dict(content='c' * 256, call_arguments={'selector': 's' * 500}, error=None) for _ in range(8)])
        eligible, reason = a.eligibility(packet, {k: False for k in a.COMPLETENESS_FLAGS},
                                         runtime, [call], d.PermissionSandbox(['read_data']))
        self.assertFalse(eligible)
        self.assertEqual(reason, 'INPUT_TOO_LARGE')

    def test_selective_skips_api_but_requires_monitor_and_ticket(self):
        chain=self.setup_chain();state=self.run_chain(chain)
        self.assertEqual(self.effects,['read']);self.assertEqual(chain[1].requests,0)
        self.assertEqual(state[4]['dscg_audit_decision']['reason_code'],'SELECTIVE_READ_BYPASS')
        self.assertEqual(state[4]['dscg_audit_decision']['confidence'],0)
        event=state[4]['dscg_router_events'][0];self.assertTrue(event['actual_bypass']);self.assertEqual(event['semantic_audit_calls'],0)
        self.assertEqual(event['final_monitor_decision'],'allow');self.assertNotIn('_dscg_router_receipt',state[4])

    def test_shadow_preserves_abstain_and_deny_read_override(self):
        for response,effects in [('allow',['read']),('deny',['read']),('abstain',[]),('error',[])]:
            self.effects.clear();chain=self.setup_chain('shadow',response=response);state=self.run_chain(chain)
            self.assertEqual(self.effects,effects);self.assertEqual(chain[1].requests,1)
            event=state[4]['dscg_router_events'][0];self.assertTrue(event['would_bypass']);self.assertFalse(event['actual_bypass'])
            self.assertEqual(event['semantic_audit_calls'],1);self.assertIsNone(event['semantic_audit_tokens'])

    def test_hard_scope_cannot_be_overridden_by_score(self):
        for sensitivity,effect,sink in [('personal','read','none'),('secret','read','none'),('internal','write','none'),('internal','read','external_recipient')]:
            self.effects.clear();self.md.update(sensitivity=sensitivity,effect=effect,sink=sink);set_tool_metadata(self.runtime,{'read_data':self.md})
            chain=self.setup_chain();state=self.run_chain(chain)
            self.assertEqual(chain[1].requests,1);self.assertFalse(state[4]['dscg_router_events'][0]['actual_bypass'])

    def test_small_calibration_missing_and_corrupt_artifacts_fall_back(self):
        for kind in ('small','missing','nan'):
            path=None
            if kind=='missing':path=Path(self.temp.name)/'missing.json'
            if kind=='nan':path=Path(self.temp.name)/'nan.json';path.write_text('{"threshold":NaN}')
            chain=self.setup_chain(m=2 if kind=='small' else 64,path=path);state=self.run_chain(chain)
            self.assertEqual(chain[1].requests,1);self.assertFalse(state[4]['dscg_router_events'][0]['would_bypass'])

    def test_forged_or_stale_receipt_cannot_execute(self):
        for mutation in ('token','task','args','catalog','schema','run','artifact','decision','mode','config'):
            self.effects.clear();chain=self.setup_chain();state=chain[1].query(*chain[0].query(*self.state()))
            q,r,e,m,x=state
            if mutation=='token':x['_dscg_router_receipt']={'decision':'allow'}
            elif mutation=='task':q='Different task'
            elif mutation=='args':m[-1]['tool_calls'][0].args['new']='x'
            elif mutation=='catalog':self.md['sensitivity']='secret';set_tool_metadata(r,{'read_data':self.md})
            elif mutation=='schema':r.functions['read_data'].description='Changed description'
            elif mutation=='run':r.functions['read_data'].run=lambda **kw:'other'
            elif mutation=='artifact':chain[1].audit_router.artifact_sha256='3'*64
            elif mutation=='decision':x['_dscg_audit_decision']['confidence']=0.9
            elif mutation=='mode':chain[1].audit_router.mode='shadow'
            elif mutation=='config':chain[1].audit_router.model_config_sha256='4'*64
            state=chain[3].query(*chain[2].query(q,r,e,m,x));self.assertEqual(self.effects,[],mutation)
            # Reinitialize all host metadata/functions between mutation cases.
            self.setUp()

    def test_truncated_window_and_literal_marker_are_distinguished(self):
        chain=self.setup_chain();q,r,e,m,x=self.state()
        tools=[{'role':'tool','content':[{'type':'text','content':'<max-depth>'}],'error':None} for _ in range(9)]
        messages=[{'role':'user','content':[]},*tools,m[-1]]
        state=self.run_chain(chain,(q,r,e,messages,x));self.assertEqual(chain[1].requests,1)
        self.assertTrue(state[4]['dscg_router_events'][0]['completeness_flags']['tool_results_window_truncated'])

    def test_route_marker_removal_and_changed_history_cannot_downgrade_handoff(self):
        for mutation in ('downgrade','history'):
            self.effects.clear();chain=self.setup_chain();q,r,e,m,x=chain[1].query(*chain[0].query(*self.state()))
            if mutation=='downgrade':
                x.pop('_dscg_router_receipt');x['_dscg_audit_decision'].pop('route_source')
                x['_dscg_audit_decision']['reason_code']='TEST_ALLOW';q='Different task'
            else:x['dscg_action_ledger']=[{'state':'blocked'}]
            self.run_chain(chain[2:],(q,r,e,m,x));self.assertEqual(self.effects,[],mutation)

    def test_shadow_also_authenticates_ordinary_audit_handoff(self):
        chain=self.setup_chain('shadow');q,r,e,m,x=chain[1].query(*chain[0].query(*self.state()))
        x['_dscg_audit_decision']['reason_code']='FORGED'
        self.run_chain(chain[2:],(q,r,e,m,x));self.assertEqual(self.effects,[])

    def test_changed_action_history_revokes_selective_receipt(self):
        chain=self.setup_chain();q,r,e,m,x=chain[1].query(*chain[0].query(*self.state()))
        x['dscg_action_ledger']=[{'state':'blocked'}]
        self.run_chain(chain[2:],(q,r,e,m,x));self.assertEqual(self.effects,[])

    def test_artifact_denominator_inconsistency_is_not_loadable(self):
        path=self.artifact();value=json.loads(path.read_text());c=value['calibration']
        c['valid_groups']=1;c['results'][0]['selected_actions']=1;c['results'][0]['unacceptable_actions']=9
        path.write_text(json.dumps(value));router=a.LocalAuditRouter('selective',path,self.config_hash)
        self.assertIsNone(router.artifact)
