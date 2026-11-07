"""Recorded transport failures exclude efficacy without overwriting native evidence."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest

from dscg.task_diagnostics import DiagnosticSession, load_task_trace
from experiments.common.benchmark_outcomes import project_outcomes


class RecordedApiFailureTests(unittest.TestCase):
    def test_retry_then_native_success_is_infrastructure_with_native_labels_preserved(self):
        with TemporaryDirectory() as tmp:
            path=Path(tmp)/'u0/attack/i0.json';path.parent.mkdir(parents=True)
            raw={'messages':[], 'utility':True, 'security':True,
                 'dscg_cost':{'models':[{'generation':{'api_calls':2,'failed_calls':1,'total_tokens':17}}]},
                 'dscg_action_ledger':[{'tool_name':'send','state':'executed'}]}
            original=json.dumps(raw);path.write_text(original)
            trace=load_task_trace(path)
            self.assertTrue(trace.get('dscg_infrastructure_failure'))
            self.assertTrue(trace['utility']);self.assertTrue(trace['security'])
            self.assertEqual(trace['dscg_action_ledger'],raw['dscg_action_ledger'])
            record=project_outcomes({('u0','i0'):True},{('u0','i0'):True},Path(tmp),'attack',run_attack=True)[('u0','i0')]
            self.assertEqual(record['sample_status'],'infrastructure_error')
            self.assertIsNone(record['utility_success']);self.assertIsNone(record['attack_success'])
            self.assertTrue(record['native_utility_success']);self.assertTrue(record['native_attack_success'])
            self.assertEqual(path.read_text(),original)

    def test_failed_previous_attempt_does_not_contaminate_bound_successful_attempt(self):
        with TemporaryDirectory() as tmp:
            logger=SimpleNamespace(dirpath=tmp,context=dict(pipeline_name='engine',suite_name='banking',user_task_id='u0',attack_type='none',injection_task_id=None))
            with DiagnosticSession(logger,'old',{}) as session:
                session.finish({'dscg_cost':{'models':[{'generation':{'failed_calls':1}}]}})
            with DiagnosticSession(logger,'new',{}) as session:
                session.finish({'dscg_cost':{'models':[{'generation':{'api_calls':1,'failed_calls':0,'missing_usage_calls':1}}]}})
            path=Path(tmp)/'engine/banking/u0/none/none.json';path.write_text(json.dumps({**logger.context,'messages':[],'utility':True}))
            trace=load_task_trace(path)
            self.assertEqual(trace['dscg_task_id'],'new')
            self.assertFalse(trace.get('dscg_infrastructure_failure'))
            self.assertEqual(trace['dscg_cost']['models'][0]['generation']['missing_usage_calls'],1)

    def test_current_bound_attempt_failure_is_visible_to_all_shared_readers(self):
        with TemporaryDirectory() as tmp:
            logger=SimpleNamespace(dirpath=tmp,context=dict(pipeline_name='engine',suite_name='banking',user_task_id='u0',attack_type='none',injection_task_id=None))
            with DiagnosticSession(logger,'current',{}) as session:
                session.finish({'dscg_cost':{'models':[{'generation':{'api_calls':2,'failed_calls':1}}]}})
            path=Path(tmp)/'engine/banking/u0/none/none.json';path.write_text(json.dumps({**logger.context,'messages':[],'utility':True}))
            trace=load_task_trace(path)
            self.assertEqual(trace['dscg_diagnostics_status'],'complete')
            self.assertEqual(trace.get('dscg_infrastructure_failure',{}).get('reason_code'),'RECORDED_API_FAILURE')

    def test_unavailable_legacy_cost_is_preserved_without_fabricating_failure(self):
        for models in [None, 7, {'unknown':'legacy'}]:
            with self.subTest(models=models),TemporaryDirectory() as tmp:
                path=Path(tmp)/'case.json';cost={'models':models}
                path.write_text(json.dumps({'utility':True,'dscg_cost':cost}))
                trace=load_task_trace(path)
                self.assertEqual(trace['dscg_cost'],cost)
                self.assertFalse(trace.get('dscg_infrastructure_failure'))

    def test_protocol_defect_or_missing_usage_alone_is_not_transport_failure(self):
        for cost in [{}, {'models':[{'generation':{'failed_calls':0,'missing_usage_calls':1}}]}]:
            with self.subTest(cost=cost),TemporaryDirectory() as tmp:
                path=Path(tmp)/'case.json';path.write_text(json.dumps({'utility':False,'security':False,'dscg_authorizations':[{'error_code':'AUTH_INVALID_INTENTS'}],'dscg_cost':cost}))
                trace=load_task_trace(path)
                self.assertFalse(trace.get('dscg_infrastructure_failure'))
                self.assertFalse(trace['utility']);self.assertFalse(trace['security'])
