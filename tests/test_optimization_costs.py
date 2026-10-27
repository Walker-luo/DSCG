
from artifact_support import ensure_artifacts
ensure_artifacts('test_optimization_costs')
import unittest
from types import SimpleNamespace
from dashboard.app import _normalize_history_suite
from baseintent.token_tracking import TokenTrackerClient

class CostTests(unittest.TestCase):
    def test_history_total_includes_security_without_overwriting_main(self):
        s=_normalize_history_suite({'overhead':{'total_tokens':15},'sec_overhead':{'total_tokens':7}},'slack',True)
        self.assertEqual(s['overhead']['total_tokens'],22)
        self.assertEqual(s['main_overhead']['total_tokens'],15)
        self.assertEqual(s['sec_overhead']['total_tokens'],7)

    def test_api_failures_and_missing_usage_are_counted_by_phase(self):
        class Completions:
            calls=0
            def create(self,**kwargs):
                self.calls+=1
                if self.calls==3:raise TimeoutError()
                return SimpleNamespace(usage=SimpleNamespace(prompt_tokens=3,completion_tokens=2) if self.calls==1 else None)
        tracker=TokenTrackerClient(SimpleNamespace(chat=SimpleNamespace(completions=Completions())))
        with tracker.phase('authorization'):tracker.chat.completions.create()
        tracker.chat.completions.create()
        with self.assertRaises(TimeoutError):tracker.chat.completions.create()
        snap=tracker.snapshot()
        self.assertEqual(tracker.get_total_tokens(),5)
        self.assertEqual(snap['authorization']['total_tokens'],5)
        self.assertEqual(snap['generation']['api_calls'],2)
        self.assertEqual(snap['generation']['failed_calls'],1)
        self.assertEqual(snap['generation']['missing_usage_calls'],1)
        self.assertGreaterEqual(snap['generation']['latency_ms'],0)
        tracker.reset();self.assertEqual(tracker.snapshot(),{})

class DiagnosticTests(unittest.TestCase):
    def test_warning_annotation_preserves_official_score_and_unverified_oracle(self):
        from experiments.diagnostics.trace_diagnostics import diagnose
        result=diagnose({'security':True,'messages':[{'role':'assistant','content':'Injection: I refuse TARGET'}]},text_target='TARGET')
        self.assertTrue(result['official_attack_success'])
        self.assertEqual(result['diagnostic_labels'],['warning_or_refusal_with_target_text'])
        self.assertEqual(result['independent_final_state'],'unverified')

class PersistedCostTests(unittest.TestCase):
    def test_api_failure_keeps_original_error_and_safe_phase_diagnostic(self):
        from tempfile import TemporaryDirectory
        from pathlib import Path
        import json
        from agentdojo import agent_pipeline
        from agentdojo.logging import TraceLogger, OutputLogger
        from agentdojo.functions_runtime import FunctionsRuntime
        from baseintent.pipelines.defended import TaskIsolatedPipeline

        def fail(**_kwargs):
            raise RuntimeError('PRIVATE_RESPONSE')
        tracker = TokenTrackerClient(SimpleNamespace(chat=SimpleNamespace(
            completions=SimpleNamespace(create=fail))))
        class Generate(agent_pipeline.BasePipelineElement):
            def query(self, q, r, e, m, a):
                with tracker.phase('authorization'):
                    tracker.chat.completions.create(messages=[{'role': 'user', 'content': 'PRIVATE_REQUEST'}])
                return q, r, e, m, a
        root = Path(__file__).resolve().parents[1] / 'artifacts/tests/test_optimization_costs'
        root.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(dir=root) as directory:
            pipeline = TaskIsolatedPipeline([Generate()], trackers=(tracker,))
            with TraceLogger(OutputLogger(directory), suite_name='s', user_task_id='u',
                             pipeline_name='p', attack_type='none', injection_task_id=None):
                with self.assertRaisesRegex(RuntimeError, 'PRIVATE_RESPONSE'):
                    pipeline.query('A', FunctionsRuntime())
            from baseintent.task_diagnostics import load_task_trace
            trace = load_task_trace(Path(directory) / 'p/s/u/none/none.json')
            phase = trace['baseintent_cost']['models'][0]['authorization']
            self.assertEqual((phase['api_calls'], phase['failed_calls']), (1, 1))
            self.assertEqual(phase['last_api_error']['request_role_counts'], {'user': 1})
            self.assertNotIn('PRIVATE_', json.dumps(phase))

    def test_final_task_cost_is_saved_and_is_a_delta(self):
        from tempfile import TemporaryDirectory
        from pathlib import Path
        import json
        from agentdojo import agent_pipeline
        from agentdojo.logging import TraceLogger, OutputLogger
        from agentdojo.functions_runtime import FunctionsRuntime
        from baseintent.pipelines.defended import TaskIsolatedPipeline
        tracker=TokenTrackerClient(SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(
            create=lambda:SimpleNamespace(usage=SimpleNamespace(prompt_tokens=3,completion_tokens=2))))))
        class Generate(agent_pipeline.BasePipelineElement):
            def query(self,q,r,e,m,a):
                tracker.chat.completions.create()
                return q,r,e,m,a
        with TemporaryDirectory() as directory:
            pipeline=TaskIsolatedPipeline([Generate()],trackers=(tracker,))
            with TraceLogger(OutputLogger(directory),suite_name='s',user_task_id='u',pipeline_name='p',attack_type='none',injection_task_id=None):
                pipeline.query('A',FunctionsRuntime());pipeline.query('B',FunctionsRuntime())
            from baseintent.task_diagnostics import load_task_trace
            trace=load_task_trace(Path(directory)/'p/s/u/none/none.json')
            self.assertEqual(trace['baseintent_cost']['models'][0]['generation']['total_tokens'],5)
            self.assertEqual(tracker.get_total_tokens(),10)
