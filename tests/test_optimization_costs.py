import unittest
from types import SimpleNamespace
from dashboard.app import _normalize_history_suite
from dscg.token_tracking import TokenTrackerClient

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
        from experiments.trace_diagnostics import diagnose
        result=diagnose({'security':True,'messages':[{'role':'assistant','content':'Injection: I refuse TARGET'}]},text_target='TARGET')
        self.assertTrue(result['official_attack_success'])
        self.assertEqual(result['diagnostic_labels'],['warning_or_refusal_with_target_text'])
        self.assertEqual(result['independent_final_state'],'unverified')
