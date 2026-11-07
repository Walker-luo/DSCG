"""Compact persisted traces; all model replies are local fixtures."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
import importlib.util

HAS_INTENT_FLOW = importlib.util.find_spec('dscg.intent_flow') is not None


class TaskDiagnosticsTests(unittest.TestCase):
    def responses(self, side):
        path=side.with_name(side.name.replace('.dscg.jsonl','.dscg.responses.jsonl'))
        return [json.loads(line) for line in path.read_text().splitlines()]

    def logger(self, root):
        return SimpleNamespace(dirpath=str(root), context=dict(pipeline_name='engine',
            suite_name='banking', user_task_id='injection_task_3', attack_type='none', injection_task_id=None))

    def test_native_trace_only_references_diagnostics_and_roundtrips_metadata(self):
        from dscg.task_diagnostics import DiagnosticSession, load_task_trace, sync_context, record_event
        with TemporaryDirectory() as tmp:
            logger = self.logger(tmp)
            with DiagnosticSession(logger, 'attempt-1', {'framework': {'framework_version': 'DSCG_v3.5'}}) as session:
                record_event('authorization', {'allowed_tools': ['read_file'], 'authorization_steps': [{'intent':'Read'}]})
                sync_context({'dscg_framework': {'framework_version':'DSCG_v3.5'},
                    'dscg_audit_summary': {'total_decisions':0}, 'dscg_intent_flow': {'steps':[], 'observations':[]}})
                session.finish({'dscg_cost': {'models':[]}})
            self.assertEqual(set(k for k in logger.context if k.startswith('dscg_')), {'dscg_diagnostics'})
            trace = Path(tmp)/'engine/banking/injection_task_3/none/none.json'
            trace.write_text(json.dumps({**logger.context, 'messages':[], 'utility':True}))
            restored = load_task_trace(trace)
            self.assertEqual(restored['dscg_diagnostics_status'], 'complete')
            self.assertEqual(restored['dscg_authorizations'][0]['allowed_tools'], ['read_file'])
            self.assertEqual(restored['dscg_framework']['framework_version'], 'DSCG_v3.5')
            self.assertEqual(restored['dscg_cost'], {'models':[]})
            self.assertFalse(list(Path(tmp).rglob('*.gz')))

    def test_raw_response_survives_validation_failure_without_prompts_or_reasoning(self):
        from dscg.task_diagnostics import DiagnosticSession, record_response, record_validation
        with TemporaryDirectory() as tmp:
            logger = self.logger(tmp)
            with DiagnosticSession(logger, 'one', {}) as session:
                response = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(
                    content='{"status": broken', refusal=None, reasoning_content='HIDDEN'), finish_reason='stop')],
                    usage=SimpleNamespace(prompt_tokens=2, completion_tokens=3, total_tokens=5))
                record_response('intent_progress', response, elapsed_ms=1, intent_id='intent_1')
                record_validation('intent_progress', 'failed', diagnostics={'code':'INVALID_JSON'})
                session.finish({})
            path = Path(tmp)/'engine/banking/injection_task_3/none/none.dscg.jsonl'
            text = path.read_text(); rows=[json.loads(l) for l in text.splitlines()]
            raw = self.responses(path)[0]
            self.assertEqual(raw['record']['content'], '{"status": broken')
            self.assertEqual(raw['record']['usage']['total_tokens'],5)
            self.assertNotIn('HIDDEN',text+json.dumps(raw))
            self.assertLess([x['event'] for x in rows].index('response'), [x['event'] for x in rows].index('validation'))

    def test_new_attempt_does_not_mix_prior_records_even_after_partial_line(self):
        from dscg.task_diagnostics import DiagnosticSession, load_task_trace, record_event
        with TemporaryDirectory() as tmp:
            logger=self.logger(tmp)
            with DiagnosticSession(logger,'old',{}) as session:
                record_event('authorization',{'allowed_tools':['old']});session.finish({})
            side=Path(tmp)/'engine/banking/injection_task_3/none/none.dscg.jsonl'
            with side.open('a') as stream:stream.write('{"interrupted":')
            old=side.read_bytes()
            with DiagnosticSession(logger,'new',{}) as session:
                record_event('authorization',{'allowed_tools':['new']});session.finish({})
            trace=side.with_name('none.json');trace.write_text(json.dumps({**logger.context,'messages':[]}))
            self.assertTrue(side.read_bytes().startswith(old))
            data=load_task_trace(trace)
            self.assertEqual(data['dscg_authorizations'],[{'allowed_tools':['new']}])

    def test_missing_corrupt_and_traversal_sidecars_are_explicit_not_zero_audits(self):
        from dscg.task_diagnostics import load_task_trace
        with TemporaryDirectory() as tmp:
            trace=Path(tmp)/'case.json'
            for path,contents in [('case.dscg.jsonl',None),('case.dscg.jsonl','broken'),('../outside.jsonl',None)]:
                side=Path(tmp)/'case.dscg.jsonl'
                if side.exists():side.unlink()
                if contents:side.write_text(contents)
                trace.write_text(json.dumps({'messages':[], 'dscg_diagnostics':{'path':path,'attempt_id':'one','offset':0}}))
                data=load_task_trace(trace)
                self.assertIn(data['dscg_diagnostics_status'],('missing','corrupt','invalid_reference'))
                self.assertNotIn('dscg_audit_summary',data)

    def test_old_inline_trace_is_read_without_modification(self):
        from dscg.task_diagnostics import load_task_trace
        with TemporaryDirectory() as tmp:
            p=Path(tmp)/'old.json';original=json.dumps({'messages':[], 'dscg_audit_summary':{'total_decisions':3}})
            p.write_text(original)
            self.assertEqual(load_task_trace(p)['dscg_audit_summary']['total_decisions'],3)
            self.assertEqual(p.read_text(),original)

    def test_duplicate_sync_does_not_repeat_config_or_history(self):
        from dscg.task_diagnostics import DiagnosticSession, sync_context
        with TemporaryDirectory() as tmp:
            logger=self.logger(tmp)
            with DiagnosticSession(logger,'one',{'framework':{'framework_version':'v'}}) as session:
                for _ in range(10):sync_context({'dscg_framework':{'framework_version':'v'},'dscg_l2':{'planning_requests':1}})
                session.finish({})
            side=Path(tmp)/'engine/banking/injection_task_3/none/none.dscg.jsonl'
            rows=[json.loads(l) for l in side.read_text().splitlines()]
            self.assertEqual([x['event'] for x in rows],['task_start','task_end'])
            self.assertNotIn('framework_version',side.read_text())

    @unittest.skipUnless(HAS_INTENT_FLOW, 'Requires unselected 4a54827 intent-flow subsystem')
    def test_progress_rule_failure_keeps_code_and_adds_precise_rule(self):
        from dscg.intent_flow import IntentFlow, IntentFlowError
        value=dict(intent_id='intent_1', status='in_progress', completion_kind='facts',
            evidence_ids=[],next_intent_id='intent_1',skipped_intents=[],reason='not finished')
        with self.assertRaises(IntentFlowError) as caught:IntentFlow(('Read',),'Read').apply(value,{})
        self.assertEqual(caught.exception.reason_code,'INTENT_INVALID_PROGRESS')
        self.assertEqual(caught.exception.diagnostics['code'],'NONCOMPLETED_KIND')

    @unittest.skipUnless(HAS_INTENT_FLOW, 'Requires unselected 4a54827 intent-flow native fixture')
    def test_native_pipeline_persists_replies_in_sidecar_without_new_requests(self):
        from agentdojo import logging
        from dscg.task_diagnostics import load_task_trace
        from test_intent_flow_native import IntentFlowPipelineTests
        with TemporaryDirectory() as tmp:
            with logging.TraceLogger(logging.OutputLogger(tmp), pipeline_name='engine',suite_name='banking',
                    user_task_id='user_task_0',injection_task_id=None,attack_type='none'):
                result=IntentFlowPipelineTests().exercise()
            p=Path(tmp)/'engine/banking/user_task_0/none/none.json';raw=json.loads(p.read_text())
            self.assertEqual(set(k for k in raw if k.startswith('dscg_')),{'dscg_diagnostics'})
            restored=load_task_trace(p)
            self.assertEqual(len(result['requests']),8)
            self.assertEqual(restored['dscg_audit_summary']['total_decisions'],2)
            side=p.with_suffix('.dscg.jsonl');events=[json.loads(l) for l in side.read_text().splitlines()]
            replies=self.responses(side)
            self.assertEqual([x['record']['phase'] for x in replies].count('intent_progress'),2)
            self.assertEqual([x['record']['phase'] for x in replies].count('audit'),1)
            self.assertNotIn('authorization_intents',[x['record']['phase'] for x in replies])

    def test_audit_allow_deny_abstain_malformed_refusal_and_length_are_saved_before_parse(self):
        from unittest.mock import Mock
        from dscg.pipelines.defended import ActionSecurityChecker, AuditSchemaError
        from dscg.task_diagnostics import DiagnosticSession
        for content,refusal,finish in [('allow',None,'stop'),('deny',None,'stop'),
                ('abstain',None,'stop'),('{broken',None,'stop'),('partial','refused','stop'),('partial',None,'length')]:
            with self.subTest(content=content),TemporaryDirectory() as tmp:
                client=Mock();client.chat.completions.create.return_value=SimpleNamespace(
                    choices=[SimpleNamespace(message=SimpleNamespace(content=content,refusal=refusal),finish_reason=finish)])
                checker=ActionSecurityChecker(SimpleNamespace(name='offline',client=client))
                with DiagnosticSession(self.logger(tmp),'one',{}) as session:
                    if refusal or finish!='stop':
                        with self.assertRaises(AuditSchemaError):checker._request_audit('Task',None,{'current_actions':[]})
                    else:self.assertEqual(checker._request_audit('Task',None,{'current_actions':[]}),content)
                    session.finish({})
                side=Path(tmp)/'engine/banking/injection_task_3/none/none.dscg.jsonl'
                row=self.responses(side)[0]
                self.assertEqual(row['record']['content'],content)
                self.assertEqual(row['record']['finish_reason'],finish)
                self.assertEqual(client.chat.completions.create.call_count,1)

    @unittest.skipUnless(HAS_INTENT_FLOW, 'Requires unselected 4a54827 intent-flow subsystem')
    def test_progress_model_reply_and_exact_rule_survive_task_failure(self):
        from unittest.mock import Mock
        from dscg.intent_flow import IntentFlow,IntentFlowError
        from dscg.task_diagnostics import DiagnosticSession
        payload=dict(intent_id='intent_1',status='in_progress',completion_kind='facts',
            evidence_ids=[],next_intent_id='intent_1',skipped_intents=[],reason='Still reading')
        client=Mock();client.chat.completions.create.return_value=SimpleNamespace(choices=[SimpleNamespace(
            message=SimpleNamespace(content=json.dumps(payload),refusal=None),finish_reason='stop')])
        with TemporaryDirectory() as tmp:
            with DiagnosticSession(self.logger(tmp),'one',{}):
                with self.assertRaises(IntentFlowError):IntentFlow(('Read',),'Read').observe(
                    SimpleNamespace(name='offline',client=client),[],[])
            side=Path(tmp)/'engine/banking/injection_task_3/none/none.dscg.jsonl'
            rows=list(map(json.loads,side.read_text().splitlines()))
            self.assertEqual(self.responses(side)[0]['record']['content'],json.dumps(payload))
            self.assertEqual(next(x for x in rows if x['event']=='validation')['record']['diagnostics']['code'],'NONCOMPLETED_KIND')

    def test_routing_and_dashboard_aggregates_match_old_inline_and_missing_is_unknown(self):
        from test_routing_reports import RoutingReportTests,event,trace
        from experiments.common.routing_reports import collect_routing_summary
        from dashboard.evaluation import trace_stats
        from dscg.task_diagnostics import DiagnosticSession,sync_context,record_event
        fixture=RoutingReportTests();fixture.setUp()
        try:
            row=trace([event()],dscg_layer_routing={'semantic_audit_calls':1},
                dscg_cost={'models':[{'audit':{'total_tokens':100}}]})
            fixture.fixture({'u0':row});old=collect_routing_summary(fixture.root)
            logger=SimpleNamespace(dirpath=str(fixture.root),context=dict(pipeline_name='attack',suite_name='sample',
                user_task_id='u0',attack_type='attack',injection_task_id='i0'))
            with DiagnosticSession(logger,'new',{'framework':row['dscg_framework']}) as session:
                record_event('audit_router',event());sync_context(row);session.finish(row)
            native={k:v for k,v in row.items() if not k.startswith('dscg_')};native.update(logger.context)
            path=fixture.put('attack/sample/u0/attack/i0.json',native)
            fresh=collect_routing_summary(fixture.root)
            self.assertEqual(old['totals'],fresh['totals'])
            stats=trace_stats(fixture.root,'attack','sample','attack',[('u0','i0')])
            self.assertEqual(stats['routing']['semantic_audit_calls'],1)
            self.assertEqual(stats['diagnostic_errors'],0)
            path.with_suffix('.dscg.jsonl').unlink()
            missing=collect_routing_summary(fixture.root)
            self.assertGreater(missing['totals']['unknown_audit_call_records'],0)
            self.assertEqual(trace_stats(fixture.root,'attack','sample','attack',[('u0','i0')])['diagnostic_errors'],1)
        finally:fixture.doCleanups()

    def test_legacy_gzip_reader_and_write_failure(self):
        import gzip
        from unittest.mock import patch
        from dscg.task_diagnostics import DiagnosticSession,DiagnosticWriteError,load_diagnostic_events
        with TemporaryDirectory() as tmp:
            p=Path(tmp)/'old.dscg_trace.jsonl.gz'
            with gzip.open(p,'wt') as stream:stream.write('{"event":"authorization","record":{}}\n')
            self.assertEqual(list(load_diagnostic_events(p))[0]['event'],'authorization')
            with patch.object(DiagnosticSession,'emit',side_effect=DiagnosticWriteError('DIAGNOSTIC_WRITE_FAILED')):
                with self.assertRaises(DiagnosticWriteError):
                    with DiagnosticSession(self.logger(tmp),'one',{}):pass

    def test_monitor_router_updates_and_duplicate_audit_attempts_are_not_lost(self):
        from dscg.task_diagnostics import DiagnosticSession,record_event,sync_context,load_task_trace
        with TemporaryDirectory() as tmp:
            logger=self.logger(tmp)
            with DiagnosticSession(logger,'one',{}) as session:
                event={'mode':'shadow','final_monitor_decision':None}
                record_event('audit_router',event)
                sync_context({'dscg_router_events':[dict(event,final_monitor_decision='deny',mediation_failure_stage='audit_record')]})
                first={'batch_fingerprint':'same','decision':'abstain','semantic_attempt':1}
                last={'batch_fingerprint':'same','decision':'allow','semantic_attempt':2}
                record_event('audit_decision',first,history_index=0,history_length=1)
                record_event('audit_decision',last,history_index=1,history_length=2)
                record_event('audit_decision_final',dict(last,final_policy_decision='allow'),history_index=1,history_length=2)
                session.finish({})
            p=Path(tmp)/'engine/banking/injection_task_3/none/none.json';p.write_text(json.dumps(logger.context))
            data=load_task_trace(p)
            with self.subTest(kind='router'):
                self.assertEqual(data['dscg_router_events'][0]['final_monitor_decision'],'deny')
                self.assertEqual(data['dscg_router_events'][0]['mediation_failure_stage'],'audit_record')
            with self.subTest(kind='audit'):
                self.assertEqual([x['decision'] for x in data['dscg_audit_decisions']],['abstain','allow'])

    def test_suite_summary_uses_the_shared_reader(self):
        from test_routing_reports import event,trace
        from experiments.run_partial_benchmark import _router_trace_summary
        from dscg.task_diagnostics import DiagnosticSession,record_event,sync_context
        with TemporaryDirectory() as tmp:
            logger=self.logger(tmp);logger.context.update(user_task_id='user_task_0',attack_type='attack',injection_task_id='i0')
            p=Path(tmp)/'engine/banking/user_task_0/attack/i0.json';p.parent.mkdir(parents=True)
            p.write_text(json.dumps(trace([event()])))
            old=_router_trace_summary(p.parent.parent.parent,[('user_task_0','i0')],'attack',True)
            with DiagnosticSession(logger,'one',{}) as session:
                record_event('audit_router',event());session.finish({})
            p.write_text(json.dumps(logger.context))
            self.assertEqual(_router_trace_summary(p.parent.parent.parent,[('user_task_0','i0')],'attack',True),old)

    def test_selective_write_error_never_falls_through_to_model_request(self):
        from unittest.mock import patch
        from test_selective_audit import SelectiveAuditTests
        from dscg.task_diagnostics import DiagnosticWriteError
        from dscg.pipelines import defended
        fixture=SelectiveAuditTests();fixture.setUp()
        try:
            chain=fixture.setup_chain();state=chain[0].query(*fixture.state())
            with patch.object(defended,'_publish_audit_record',side_effect=DiagnosticWriteError('DIAGNOSTIC_WRITE_FAILED')):
                with self.assertRaises(DiagnosticWriteError):chain[1].query(*state)
            self.assertEqual(chain[1].requests,0)
        finally:fixture.doCleanups()

    def test_incomplete_diagnostic_observations_are_unknown_and_router_has_no_model_reply(self):
        from dscg.task_diagnostics import DiagnosticSession,record_response,record_event,load_task_trace
        from experiments.diagnostics.utility_stages import trace_signals
        with TemporaryDirectory() as tmp:
            logger=self.logger(tmp)
            with DiagnosticSession(logger,'one',{}) as session:
                record_response('audit',{'choices':[{'message':{'content':'old'}}]})
                record_event('audit_decision',{'batch_fingerprint':'b','model_version':'local-router:read-purpose-v2','parser_status':'deterministic_bypass'})
                session.finish({})
            side=Path(tmp)/'engine/banking/injection_task_3/none/none.dscg.jsonl'
            rows=list(map(json.loads,side.read_text().splitlines()))
            with self.subTest(kind='no_reply'):
                self.assertIsNone(next(x for x in rows if x['event']=='audit_decision_final').get('response_id'))
            side.write_text('\n'.join(side.read_text().splitlines()[:-1])+'\n')
            p=side.with_name('none.json');p.write_text(json.dumps({**logger.context,'messages':[],'utility':True,'security':False}))
            signals=trace_signals(load_task_trace(p))
            for key in ('protocol_failure_seen','audit_deny_seen','audit_abstain_seen'):
                with self.subTest(kind=key):self.assertIsNone(signals[key])

    def test_reuse_snapshot_retains_new_sidecar_and_public_config(self):
        from dscg.benchmark_catalog import get_backend
        if get_backend().id!='agentdojo':self.skipTest('AgentDojo original resume fixture')
        import test_benchmark_reuse as fixture_module
        fixture_module.setUpModule()
        from test_benchmark_reuse import ReuseIntegrationTests
        from dscg.task_diagnostics import DiagnosticSession
        fixture=ReuseIntegrationTests();fixture.setUp()
        try:
            self.assertEqual(fixture.run_benchmark(),0)
            p=next(fixture.base.glob('tool_knowledge/workspace/user_task_*/*.json'))
            value=json.loads(p.read_text());value.pop('utility')
            logger=SimpleNamespace(dirpath=str(fixture.base),context=dict(pipeline_name='tool_knowledge',suite_name='workspace',
                user_task_id=value['user_task_id'],attack_type='tool_knowledge',injection_task_id=value['injection_task_id']),
                group_directory=lambda: p.parent.parent, task_directory=lambda: p.parent, task_stem=lambda: p.stem)
            with DiagnosticSession(logger,'one',{}) as session:session.finish({})
            value.update(logger.context);p.write_text(json.dumps(value))
            side=p.with_suffix('.dscg.jsonl');cfg=next((fixture.base/'tool_knowledge/workspace').glob('dscg_config.*.json'))
            before={q:q.read_bytes() for q in (p,side,cfg)}
            binding=fixture.base/'run_manifest.json'; original_binding=binding.read_bytes()
            self.assertEqual(fixture.run_benchmark(reuse=True),0)
            self.assertEqual(binding.read_bytes(), original_binding)
            snap=next((fixture.base/'reuse').glob('*/snapshot'))
            for q,data in before.items():self.assertEqual((snap/q.relative_to(fixture.base)).read_bytes(),data)
        finally:
            fixture.doCleanups()
            fixture_module.tearDownModule()

    def test_audit_failure_before_request_cannot_reference_an_earlier_reply(self):
        from dscg.pipelines.defended import ActionSecurityChecker,AuditSchemaError
        from dscg.task_diagnostics import DiagnosticSession,record_response,record_validation
        with TemporaryDirectory() as tmp:
            with DiagnosticSession(self.logger(tmp),'one',{}) as session:
                record_response('audit',{'choices':[{'message':{'content':'earlier'}}]})
                checker=ActionSecurityChecker(SimpleNamespace(name='offline',client=None))
                checker.SYSTEM_POLICY='Missing output instruction'
                with self.assertRaises(AuditSchemaError):checker._request_audit('Task',None,{})
                record_validation('audit','failed')
                session.finish({})
            rows=map(json.loads,(Path(tmp)/'engine/banking/injection_task_3/none/none.dscg.jsonl').read_text().splitlines())
            self.assertIsNone(next(x for x in rows if x['event']=='validation')['record']['response_id'])
