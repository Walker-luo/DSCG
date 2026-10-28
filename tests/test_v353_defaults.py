"""Entry-point defaults and shared static-view boundaries; no online judgments."""
import inspect
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from dscg import prompt_profiles as profiles
from dscg import anchored_task_view as task_view
from dscg.model_config import ModelConfig
from dscg.benchmark_catalog import get_suites
from dscg.pipelines import defended as d
from dashboard.evaluation import normalize_config
from experiments import run_partial_benchmark as runner
from test_step_authorization import runtime


class CurrentStaticDefaultsTests(unittest.TestCase):
    def test_default_factory_enables_static_without_completion_retry(self):
        cfg=ModelConfig('offline','offline','https://offline.invalid','custom')
        with patch.object(d,'create_openai_client',return_value=Mock()):
            pipeline,_,_=d.make_defended_pipeline(model_config=cfg)
        self.assertEqual(pipeline.dscg_optimization_config['prompt_profile'],task_view.PROFILE)
        self.assertEqual(pipeline.dscg_optimization_config['framework_version'],'DSCG_v3.5.4')
        self.assertFalse(pipeline.dscg_optimization_config['completion_prompt'])
        self.assertEqual(pipeline.dscg_optimization_config['audit_retries'],0)
        self.assertIn(task_view.PLANNING_POLICY,pipeline.elements[0].system_message)

    def test_shared_runner_resolves_native_baseline_and_static_ablations(self):
        self.assertEqual(runner._validate_prompt_profile(False,True,True,None),task_view.PROFILE)
        self.assertEqual(runner._validate_prompt_profile(True,False,False,None),'legacy')
        for sandbox,checker in [(False,True),(True,False),(False,False)]:
            self.assertEqual(runner._validate_prompt_profile(False,sandbox,checker,task_view.PROFILE),task_view.PROFILE)
        with self.assertRaises(ValueError):runner._validate_prompt_profile(True,False,False,task_view.PROFILE)
        with self.assertRaises(ValueError):runner._validate_prompt_profile(False,False,True,'protocol-v1')
        self.assertIsNone(inspect.signature(runner.main).parameters['prompt_profile'].default)

    def test_dashboard_default_and_native_baseline_match_runner(self):
        suites=[get_suites()[0]]
        self.assertEqual(normalize_config({'suites':suites})['prompt_profile'],task_view.PROFILE)
        self.assertEqual(normalize_config({'suites':suites,'origin':True})['prompt_profile'],'legacy')
        config=normalize_config({'suites':suites,'use_security_checker':False})
        self.assertEqual(config['prompt_profile'],task_view.PROFILE)
        self.assertFalse(config['use_security_checker'])

    def test_static_audit_keeps_numbered_original_and_later_read_examples(self):
        checker=d.ActionSecurityChecker(SimpleNamespace(name='offline'),prompt_profile=task_view.PROFILE)
        request='1. Find the channel. 2. Read the contact website.'
        packet=checker._audit_packet(request,runtime(),[{'function':'discover','args':{},'id':'r1'}],{},[])
        model_view=checker._model_audit_packet(packet)
        self.assertEqual(model_view['trusted_user_request'],request)
        self.assertIn('literal_request_layout',model_view)
        self.assertEqual(packet['current_review']['decision_examples'],checker.TASK_READ_DECISION_EXAMPLES)

    def test_static_policy_identity_binds_planning_and_audit_guidance(self):
        original=profiles.profile_binding(task_view.PROFILE)
        with patch.object(task_view,'PLANNING_POLICY','different planning behavior'):
            self.assertNotEqual(original,profiles.profile_binding(task_view.PROFILE))
        with patch.object(task_view,'AUDIT_GUIDANCE','different evidence behavior'):
            self.assertNotEqual(original,profiles.profile_binding(task_view.PROFILE))


if __name__=='__main__':unittest.main()
