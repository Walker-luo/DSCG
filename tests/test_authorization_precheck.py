"""Deterministic rejection saves audits without partial execution or stale grants."""
import unittest
from types import SimpleNamespace
from agentdojo.functions_runtime import EmptyEnv, FunctionCall, FunctionsRuntime
from dscg.pipelines import defended as d
from dscg.tool_metadata import set_tool_metadata


class RecordingAuditor(d.ActionSecurityChecker):
    def __init__(self,sandbox,precheck):
        super().__init__(SimpleNamespace(name='offline-auditor',client=None),sandbox=sandbox,precheck=precheck)
        self.requests=[]
    def _request_audit(self,q,e,packet):
        self.requests.append(packet)
        return '{"decision":"allow","violations":[],"confidence":0.9,"reason_code":"ALIGNED"}'


class AuthorizationPrecheckTests(unittest.TestCase):
    def setUp(self):
        self.runtime=FunctionsRuntime();self.executed=[]
        @self.runtime.register_function
        def read_data() -> str:
            """Read public data."""
            self.executed.append('read');return 'fact'
        @self.runtime.register_function
        def write_data() -> str:
            """Write a local record."""
            self.executed.append('write');return 'done'
        self.metadata={'read_data':{'effect':'read','source':'local','sink':'none','sensitivity':'public','idempotent':True,'reversible':False},
                       'write_data':{'effect':'write','source':'local','sink':'none','sensitivity':'internal','idempotent':False,'reversible':False}}
        set_tool_metadata(self.runtime,self.metadata)
    def components(self,allowed=('read_data',)):
        cls=getattr(d,'ToolAuthorizationPrecheck',None)
        self.assertIsNotNone(cls,'The L2 pre-audit boundary is missing')
        sandbox=d.PermissionSandbox(list(allowed));precheck=cls(sandbox)
        checker=RecordingAuditor(sandbox,precheck)
        monitor=d.ReferenceMonitor(sandbox,True,precheck=precheck)
        return sandbox,precheck,checker,monitor,d.TicketedToolsExecutor(monitor)
    def state(self,*names):
        calls=[FunctionCall(function=n,args={},id=str(i)) for i,n in enumerate(names)]
        return ('Read task data',self.runtime,EmptyEnv(),[{'role':'assistant','content':[],'tool_calls':calls}],{})
    def run_chain(self,state,precheck,checker,monitor,executor):
        for e in [precheck,checker,monitor,executor]:state=e.query(*state)
        return state
    def test_denied_batch_never_calls_auditor_or_tool(self):
        _,p,c,m,e=self.components();state=self.run_chain(self.state('write_data'),p,c,m,e)
        self.assertEqual(c.requests,[]);self.assertEqual(self.executed,[])
        self.assertEqual(state[4]['dscg_action_ledger'][0]['state'],'blocked')
        self.assertEqual(state[4]['dscg_audit_decision']['semantic_attempt'],0)
    def test_mixed_batch_is_atomic_in_either_order(self):
        for names in [('read_data','write_data'),('write_data','read_data')]:
            with self.subTest(names=names):
                _,p,c,m,e=self.components();state=self.run_chain(self.state(*names),p,c,m,e)
                self.assertEqual(self.executed,[]);self.assertEqual(c.requests,[])
                self.assertEqual(len(state[4]['dscg_action_ledger']),2)
                self.assertTrue(all(x['state']=='blocked' for x in state[4]['dscg_action_ledger']))
    def test_unknown_or_missing_metadata_cannot_be_fixed_by_auditor(self):
        for name in ['ghost_tool','write_data']:
            with self.subTest(name=name):
                if name=='write_data':self.runtime._dscg_tool_metadata.pop(name)
                _,p,c,m,e=self.components(('read_data','write_data'))
                state=self.run_chain(self.state(name),p,c,m,e)
                self.assertEqual(self.executed,[]);self.assertEqual(c.requests,[])
                self.assertEqual(state[4]['dscg_action_ledger'][0]['state'],'blocked')
    def test_public_read_keeps_existing_bypass(self):
        _,p,c,m,e=self.components();state=self.run_chain(self.state('read_data'),p,c,m,e)
        self.assertEqual(self.executed,['read']);self.assertEqual(c.requests,[])
        self.assertEqual(state[4]['dscg_audit_decision']['reason_code'],'NON_SENSITIVE_READ_BYPASS')
    def test_private_read_is_still_audited_once(self):
        self.metadata['read_data']['sensitivity']='personal';set_tool_metadata(self.runtime,self.metadata)
        _,p,c,m,e=self.components();state=self.run_chain(self.state('read_data'),p,c,m,e)
        self.assertEqual(self.executed,['read']);self.assertEqual(len(c.requests),1)
        self.assertEqual(state[4]['dscg_audit_decision']['semantic_attempt'],1)
    def test_revoked_permission_after_precheck_cannot_execute(self):
        sandbox,p,c,m,e=self.components();state=c.query(*p.query(*self.state('read_data')))
        sandbox.allowed_tools=[];state=e.query(*m.query(*state))
        self.assertEqual(self.executed,[])
        self.assertEqual(state[4]['dscg_action_ledger'][0]['state'],'blocked')
    def test_changed_metadata_after_public_bypass_requires_new_boundary(self):
        _,p,c,m,e=self.components();state=c.query(*p.query(*self.state('read_data')))
        self.metadata['read_data']['sensitivity']='secret';set_tool_metadata(self.runtime,self.metadata)
        state=e.query(*m.query(*state));self.assertEqual(self.executed,[])
        self.assertEqual(state[4]['dscg_action_ledger'][0]['state'],'blocked')
    def test_rejected_read_cannot_use_read_deny_override(self):
        _,p,c,m,e=self.components(('write_data',))
        state=self.run_chain(self.state('read_data'),p,c,m,e)
        self.assertEqual(self.executed,[]);self.assertEqual(c.requests,[])
    def test_in_place_catalog_changes_invalidate_receipt(self):
        for field in ('run','parameters','dependencies','name'):
            with self.subTest(field=field):
                self.setUp()
                _,p,c,m,e=self.components();state=c.query(*p.query(*self.state('read_data')))
                spec=self.runtime.functions['read_data']
                if field=='run':
                    spec.run=lambda: self.executed.append('replacement') or 'replacement'
                elif field=='parameters':
                    from pydantic import create_model
                    spec.parameters=create_model('ChangedParameters',new_field=(str,...))
                elif field=='dependencies':
                    from agentdojo.functions_runtime import Depends
                    spec.dependencies['new_dependency']=Depends('host-field')
                else:
                    spec.name='changed-name'
                state=e.query(*m.query(*state))
                self.assertEqual(self.executed,[])
                self.assertEqual(state[4]['dscg_action_ledger'][0]['state'],'blocked')
    def test_missing_precheck_receipt_never_executes(self):
        _,p,c,m,e=self.components();state=c.query(*self.state('read_data'))
        state=e.query(*m.query(*state));self.assertEqual(self.executed,[])
    def test_changed_candidate_cannot_use_old_precheck(self):
        _,p,c,m,e=self.components(('read_data','write_data'))
        state=c.query(*p.query(*self.state('read_data')))
        state[3][-1]['tool_calls']=[FunctionCall(function='write_data',args={},id='new')]
        state=e.query(*m.query(*state));self.assertEqual(self.executed,[])
    def test_final_answer_creates_no_audit_or_rejection(self):
        _,p,c,m,e=self.components();state=self.state()
        state=self.run_chain(state,p,c,m,e)
        self.assertEqual(c.requests,[]);self.assertNotIn('dscg_action_ledger',state[4])
