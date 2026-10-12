import inspect
import unittest
import tempfile
from unittest.mock import patch
from experiments import run_partial_benchmark as p


class PartialRouterTests(unittest.TestCase):
    def test_modes_reach_every_attack_and_baseline_rejects(self):
        self.assertIn('audit_router_mode',inspect.signature(p.main).parameters,'runner routing controls missing')
        with tempfile.TemporaryDirectory() as out,patch.object(p,'_run_single_attack',return_value=None) as run:
            self.assertEqual(p.main(run_attack=False,results_dir=out,audit_router_mode='shadow',audit_router_artifact='/tmp/router.json'),0)
            self.assertEqual(run.call_args.kwargs['audit_router_mode'],'shadow')
            self.assertEqual(run.call_args.kwargs['audit_router_artifact'],'/tmp/router.json')
        for flags in ({'origin':True},{'use_security_checker':False}):
            with self.assertRaises(ValueError):p.main(audit_router_mode='selective',**flags)

    def test_cli_exposes_modes_without_starting_models(self):
        with patch.object(p,'main',return_value=0) as run:
            self.assertEqual(p.cli(['--clean','--audit-router-mode','shadow','--audit-router-artifact','/tmp/router.json']),0)
            self.assertEqual(run.call_args.kwargs['audit_router_mode'],'shadow')

    def test_summary_separates_potential_from_actual_savings(self):
        from dscg import audit_router as a
        self.assertTrue(hasattr(a,'summarize_events'),'router cost summary missing')
        events=[dict(route_reason='READ_AUDIT_BYPASS',original_public_bypass=True,actual_bypass=False,eligible=False),
                dict(mode='shadow',route_reason='BELOW_CALIBRATED_THRESHOLD',original_public_bypass=False,eligible=True,
                     would_bypass=True,actual_bypass=False,semantic_audit_calls=1,semantic_audit_tokens=100),
                dict(mode='selective',route_reason='BELOW_CALIBRATED_THRESHOLD',original_public_bypass=False,eligible=True,
                     would_bypass=True,actual_bypass=True,semantic_audit_calls=0,semantic_audit_tokens=0)]
        r=a.summarize_events(events)
        self.assertEqual(r['previously_audited_batches'],2);self.assertEqual(r['new_bypass_rate'],0.5)
        self.assertEqual(r['shadow_would_save_tokens'],100);self.assertIsNone(r['actual_total_tokens_saved'])
        events[1]['semantic_audit_tokens']=None
        self.assertIsNone(a.summarize_events(events)['shadow_would_save_tokens'])
