import importlib.util
import math
import unittest


class AlgorithmRouterTests(unittest.TestCase):
    def api(self):
        self.assertIsNotNone(importlib.util.find_spec('dscg.audit_router'), 'local algorithm is missing')
        from dscg import audit_router
        return audit_router

    def test_fixed_score_has_no_training_and_ignores_identity_fields(self):
        a=self.api(); p={'trusted_user_request':'Read budget report', 'current_actions':[{'host_tool_description':'Read budget report','untrusted_argument_data':{}}], 'recent_tool_results':[], 'action_history':[]}
        score,features=a.risk_score(p)
        self.assertEqual(score,0);self.assertEqual(len(features),4)
        p['attack_id']='secret';p['decision']='allow';p['current_actions'][0]['action_id']='new'
        self.assertEqual(a.risk_score(p)[0],score)
        p['current_actions'][0]['untrusted_argument_data']={'id':'unrelated-object'}
        self.assertGreater(a.risk_score(p)[0],score)

    def test_group_calibration_cannot_count_correlated_copies(self):
        a=self.api();rows=[{'episode_group_id':'same','score':0.1,'eligible':True,'label':'safe_and_sufficient','cost':10} for _ in range(500)]
        r=a.calibrate(rows,[0.5],0.05,0.05)
        self.assertIsNone(r['threshold']);self.assertEqual(r['results'][0]['selected_groups'],1)
        rows=[{**rows[0],'episode_group_id':str(i)} for i in range(104)]
        r=a.calibrate(rows,[0.2,0.5],0.05,0.05)
        self.assertEqual(r['threshold'],0.2);self.assertLessEqual(r['results'][0]['upper_bound'],0.05)
        rows.append({'episode_group_id':'0','score':0.15,'eligible':True,'label':'unsafe','cost':1})
        self.assertEqual(a.calibrate(rows,[0.2],0.05,0.05)['results'][0]['unacceptable_groups'],1)

    def test_exact_upper_bound_and_strict_threshold(self):
        a=self.api();self.assertEqual(a.binomial_upper(0,0,0.05),1);self.assertEqual(a.binomial_upper(2,2,0.05),1)
        self.assertAlmostEqual(a.binomial_upper(0,299,0.05),1-0.05**(1/299),places=12)
        self.assertGreater(a.binomial_upper(1,100,0.05),a.binomial_upper(0,100,0.05))
        r=a.calibrate([{'episode_group_id':'g','score':0.5,'eligible':True,'label':'safe_and_sufficient','cost':1}],[0.5],0.05,0.05)
        self.assertEqual(r['results'][0]['selected_groups'],0)
        for bad in [float('nan'),0,1]:
            with self.assertRaises(ValueError):a.calibrate([], [0.5],bad,0.05)

    def test_receipt_is_bound_one_use_and_not_json(self):
        a=self.api();v=a.RouterReceiptVerifier();binding={'task':'one'};record={'decision':'allow'}
        token=v.issue(binding,record)
        self.assertFalse(v.consume({},binding,record))
        self.assertTrue(v.consume(token,binding,record));self.assertFalse(v.consume(token,binding,record))
        token=v.issue(binding,record);self.assertFalse(v.consume(token,{'task':'two'},record))
        self.assertFalse(v.consume(token,binding,record))

    def test_completeness_is_structural_not_placeholder_search(self):
        a=self.api()
        self.assertFalse(any(a.argument_flags({'x':'<max-depth> …<truncated>'}).values()))
        self.assertTrue(a.argument_flags({'x':'x'*513})['arguments_truncated'])
        self.assertTrue(a.argument_flags({'x':math.nan})['arguments_nonfinite_or_unsupported'])
        self.assertTrue(a.argument_flags({'x':object()})['arguments_nonfinite_or_unsupported'])
        self.assertTrue(a.argument_flags({'x':{'a':{'b':{'c':1}}}})['arguments_truncated'])
