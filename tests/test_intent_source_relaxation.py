from authorization_fixture import adapt_client
"""Default prompt contract and strict mediation diagnostics, without model calls."""
import json
from types import SimpleNamespace
from unittest.mock import Mock
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from agentdojo.functions_runtime import EmptyEnv,FunctionCall
from dscg.pipelines import defended as d
from dscg.audit_router import LocalAuditRouter,RouterReceiptVerifier
from dscg.input_isolation import FRAMEWORK_VERSION
from experiments.diagnostics.utility_stages import synthetic_runtime


def model(payload):
    client=Mock()
    client.chat.completions.create.return_value=SimpleNamespace(choices=[SimpleNamespace(
        message=SimpleNamespace(content=payload,refusal=None),finish_reason='stop')])
    adapt_client(client)
    return SimpleNamespace(name='offline',client=client)


class IntentSourceRelaxationTests(unittest.TestCase):
    def test_default_version_and_compact_audit_contract(self):
        self.assertEqual(FRAMEWORK_VERSION,'DSCG_v3.4.1')
        policy=d.ActionSecurityChecker.SYSTEM_POLICY
        self.assertLessEqual(len(policy),2200)
        for field in ('decision','violations','confidence','reason_code'):
            self.assertIn(field,d.AUDIT_SCHEMA['required'])
        self.assertIn('parameter',policy)
        self.assertIn('derive',policy)
        self.assertIn('unknown',policy)
        self.assertIn('preparatory',policy)
        self.assertIn('alternative',d.ToolAuthorizationCompiler.SYSTEM_POLICY)

    def test_broad_candidate_grants_use_one_call_and_do_not_change_catalogue(self):
        runtime=synthetic_runtime('slack');llm=model('{"tools":["post_webpage","send_channel_message"]}')
        grant=d.ToolAuthorizationCompiler(llm).compile(d.TrustedTaskRequest('Post the article summary to general'),runtime)
        self.assertTrue({'post_webpage','send_channel_message'}<=grant.allowed_tools)
        llm.client.chat.completions.create.assert_called_once()
        request=llm.client.chat.completions.create.call_args.kwargs
        packet=json.loads(request['messages'][1]['content'])
        self.assertEqual(set(packet),{'user_request','automatic_read_tools','action_tools'})
        self.assertNotIn('send_direct_message',grant.allowed_tools)
        # The host does not silently expand a returned grant.
        llm=model('{"tools":[]}')
        grant=d.ToolAuthorizationCompiler(llm).compile(d.TrustedTaskRequest('Only read the page; do not publish'),runtime)
        self.assertNotIn('post_webpage',grant.allowed_tools)
        self.assertNotIn('send_channel_message',grant.allowed_tools)

    def prepared(self,payload=None):
        runtime=synthetic_runtime('slack');sandbox=d.PermissionSandbox(['send_channel_message','post_webpage'])
        verifier=RouterReceiptVerifier();router=LocalAuditRouter('shadow')
        pre=d.ToolAuthorizationPrecheck(sandbox)
        llm=model(payload or '{"decision":"allow","violations":[],"confidence":0.9,"reason_code":"ALIGNED"}')
        checker=d.ActionSecurityChecker(llm,sandbox=sandbox,precheck=pre,audit_router=router,router_verifier=verifier)
        monitor=d.ReferenceMonitor(sandbox,True,precheck=pre,audit_router=router,router_verifier=verifier)
        call=FunctionCall(function='send_channel_message',args={'channel':'general','body':'Summary'},id='one')
        state=('Post the article summary to general',runtime,EmptyEnv(),[
            {'role':'assistant','content':[],'tool_calls':[call]}],{})
        return monitor,checker.query(*pre.query(*state))

    def finish(self,monitor,state):
        state=monitor.query(*state)
        record=state[-1]['dscg_audit_decisions'][-1]
        return state,record

    def test_legal_audit_handoff_remains_valid(self):
        monitor,state=self.prepared();state,record=self.finish(monitor,state)
        self.assertEqual(record['final_policy_decision'],'allow')
        self.assertIsNone(record['mediation_diagnostics']['failure_stage'])
        self.assertEqual(record['mediation_diagnostics']['router_handoff_status'],'valid')

    def test_model_protocol_failure_is_not_a_handoff_failure(self):
        monitor,state=self.prepared('{"decision":"allow","violations":[]}')
        state,record=self.finish(monitor,state)
        self.assertEqual(record['final_policy_decision'],'deny')
        self.assertEqual(record['protocol_diagnostics']['failure_type'],'FIELDS_MISMATCH')
        self.assertEqual(record['mediation_diagnostics']['failure_stage'],'model_protocol')
        self.assertEqual(record['mediation_diagnostics']['router_handoff_status'],'valid')

    def test_invalid_record_preserves_published_parser_observation_not_private_values(self):
        monitor,state=self.prepared()
        state[-1]['_dscg_audit_decision']['confidence']='PRIVATE_PAYLOAD'
        state,record=self.finish(monitor,state)
        diagnostic=record['mediation_diagnostics']
        self.assertEqual(record['final_policy_decision'],'deny')
        self.assertEqual(diagnostic['failure_stage'],'audit_record')
        self.assertEqual(diagnostic['checker_parser_status'],'ok')
        self.assertNotIn('PRIVATE_PAYLOAD',json.dumps(record))
        summary=d._audit_summary([record])
        self.assertEqual(summary['parser_status_counts'],{'ok':1})
        self.assertEqual(summary['mediation_failure_counts'],{'audit_record':1})

    def test_missing_changed_and_replayed_receipts_remain_denied(self):
        for mutation in ('missing','binding','record','replay'):
            with self.subTest(mutation=mutation):
                monitor,state=self.prepared()
                token=state[-1]['_dscg_router_receipt']
                original=dict(state[-1]['_dscg_audit_decision'])
                if mutation=='missing':state[-1].pop('_dscg_router_receipt')
                elif mutation=='binding':state=('A different task',*state[1:])
                elif mutation=='record':state[-1]['_dscg_audit_decision']['reason_code']='CHANGED'
                else:
                    state,_=self.finish(monitor,state)
                    state[-1]['_dscg_router_receipt']=token
                    state[-1]['_dscg_audit_decision']=original
                state,record=self.finish(monitor,state)
                diagnostic=record['mediation_diagnostics']
                self.assertEqual(record['final_policy_decision'],'deny')
                self.assertEqual(diagnostic['failure_stage'],'audit_record' if mutation=='record' else 'router_handoff')
                self.assertEqual(diagnostic['checker_parser_status'],'ok')
                self.assertEqual(diagnostic['router_handoff_status'],'not_checked' if mutation=='record' else 'invalid')
                self.assertEqual(d._audit_summary([record])['parser_status_counts'],{'ok':1})

    def test_broad_grant_does_not_override_audit_deny_or_abstain(self):
        for decision in ('deny','abstain'):
            monitor,state=self.prepared(json.dumps(dict(decision=decision,violations=['OFF_TASK'],confidence=.9,reason_code='OFF_TASK')))
            state,record=self.finish(monitor,state)
            self.assertEqual(record['final_policy_decision'],'deny')
            self.assertTrue(all(not item.approved for item in state[-1]['_dscg_pending_batch'].actions))

    def test_previous_defense_version_cannot_resume_and_baseline_stays_native(self):
        import serial_fixture
        from dscg.benchmark_catalog import get_backend,get_suites
        from experiments import run_partial_benchmark as runner
        root=Path(__file__).resolve().parents[1]/'workshop/artifacts/20261021_intent_source_relaxation'
        with TemporaryDirectory(dir=root) as temp,serial_fixture.patched(),redirect_stdout(StringIO()):
            options=dict(suites=[get_suites()[0]],run_attack=False,results_dir=temp,run_name='binding')
            self.assertEqual(runner.main(**options),0)
            path=Path(temp)/get_backend().id/'offline-model_binding/none'/get_suites()[0]/'run_manifest.json'
            binding=json.loads(path.read_text())
            self.assertEqual(binding['defense_version'],'DSCG_v3.4.1')
            binding['defense_version']='three-layer-v3.1';path.write_text(json.dumps(binding))
            before={p:p.read_bytes() for p in Path(temp).rglob('*') if p.is_file()}
            with patch.object(runner,'iter_attack_results') as dispatch:
                self.assertEqual(runner.main(**options,reuse=True),1)
                dispatch.assert_not_called()
            self.assertEqual(before,{p:p.read_bytes() for p in Path(temp).rglob('*') if p.is_file()})
            self.assertEqual(runner.main(**{**options,'run_name':'baseline'},origin=True),0)
            path=Path(temp)/get_backend().id/'offline-model_baseline/none'/get_suites()[0]/'run_manifest.json'
            binding=json.loads(path.read_text())
            self.assertIsNone(binding['defense_version'])
            self.assertFalse(binding['authorization_precheck'])
