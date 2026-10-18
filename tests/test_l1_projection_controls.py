"""Effective planner view, run identity and configuration controls, without a model call."""
from copy import deepcopy
from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
from tests.test_partial_agentdyn import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch
from tests import test_l1_projection as fixture_module
from tests import test_partial_attacks as partial_fixture
from tests.test_l1_projection import REQUEST, ATTACK
from dscg.model_config import ModelConfig
from dscg.benchmark_catalog import get_backend
from dscg.pipelines.defended import OurFrameExecutor, make_defended_pipeline
from dscg.l1_projection import PROFILE_SHA256
from dashboard.evaluation import normalize_config
from experiments import run_partial_benchmark as runner


class Recorder:
    def query(self,q,r,e,m,a):
        self.view=deepcopy(m)
        return q,r,e,[*m,dict(role='assistant',content=[],tool_calls=[])],a


class ProjectionControlTests(unittest.TestCase):
    def factory(self,**flags):
        config=ModelConfig(provider='custom',model_id='offline',api_key='fixture',base_url='http://offline')
        with patch('dscg.pipelines.defended.create_openai_client',return_value=Mock()):
            return make_defended_pipeline(model_config=config,sec_model_config=config,**flags)[0]

    def test_default_executor_changes_effective_payload_but_returns_original_history(self):
        fixture=fixture_module.L1ProjectionTests();fixture.setUp();raw=fixture.history();before=deepcopy(raw)
        llm=Recorder();executor=OurFrameExecutor(llm)
        state=executor.query(REQUEST,fixture.runtime,{},raw,{})
        self.assertNotIn(ATTACK,str(llm.view))
        self.assertEqual(state[3][:-1],before)
        self.assertEqual(state[4]['dscg_l1_projection']['projected_returns'],1)
        self.assertEqual(state[4]['dscg_l1_projection']['profile_sha256'],PROFILE_SHA256)

    def test_modes_bind_pipeline_name_framework_and_router_configuration(self):
        names=[];hashes=[]
        for mode in ('off','shadow','projected'):
            pipeline=self.factory(l1_projection_mode=mode,audit_router_mode='shadow')
            config=pipeline.dscg_optimization_config
            self.assertEqual(config['l1_projection_mode'],mode)
            self.assertEqual(config['l1_projection_profile_sha256'],PROFILE_SHA256)
            names.append(pipeline.name);hashes.append(config['audit_router_config_sha256'])
        self.assertEqual(len(set(names)),3);self.assertEqual(len(set(hashes)),3)
        self.assertEqual(self.factory(input_isolation=False).dscg_optimization_config['l1_projection_mode'],'off')
        with self.assertRaises(ValueError):self.factory(l1_projection_mode='guess')

    def test_dashboard_effective_mode_defaults_and_disabled_input(self):
        self.assertEqual(normalize_config({'suites':[get_backend().suites[0]]})['l1_projection_mode'],'projected')
        for flags in ({'origin':True},{'input_isolation':False}):
            self.assertEqual(normalize_config({'suites':[get_backend().suites[0]],**flags})['l1_projection_mode'],'off')
        with self.assertRaises(ValueError):normalize_config({'suites':[get_backend().suites[0]],'l1_projection_mode':'guess'})

    def test_partial_cli_forwards_mode_and_baseline_resolves_off(self):
        with patch.object(runner,'main',return_value=0) as main:
            self.assertEqual(runner.cli(['--l1-projection-mode','shadow','--clean']),0)
            self.assertEqual(main.call_args.kwargs['l1_projection_mode'],'shadow')
            self.assertEqual(runner.cli(['--baseline','--clean']),0)
            self.assertEqual(main.call_args.kwargs['l1_projection_mode'],'off')

    def test_partial_python_rejects_invalid_mode_before_model_resolution(self):
        with self.assertRaises(ValueError):runner.main(l1_projection_mode='guess')

    def test_manifest_binds_mode_and_refuses_named_cache_from_another_mode(self):
        def factory(*args,**kwargs):
            pipeline,tracker=partial_fixture.fake_pipeline()
            pipeline.dscg_optimization_config={'l1_projection_mode':kwargs['l1_projection_mode'],
                                               'l1_projection_profile_sha256':PROFILE_SHA256}
            return pipeline,tracker,None
        with TemporaryDirectory() as directory, redirect_stdout(StringIO()), patch.object(
            runner,'make_defended_pipeline',side_effect=factory
        ) as build, patch.object(runner.attacks,'load_attack',side_effect=partial_fixture.fake_attack), patch.object(
            runner.benchmark,'benchmark_suite_with_injections',side_effect=partial_fixture.fake_results
        ):
            args=dict(suites=[get_backend().suites[0]],results_dir=directory,run_name='bound',attack='tool_knowledge',
                      tool_metadata_path=get_backend().tool_metadata_path)
            self.assertEqual(runner.main(**args,l1_projection_mode='shadow'),0)
            manifest=json.loads((Path(directory)/f'offline-model_{get_backend().id}_bound/tool_knowledge/{get_backend().suites[0]}/run_manifest.json').read_text())
            self.assertIn('shadow',str(manifest));self.assertIn(PROFILE_SHA256,str(manifest))
            self.assertEqual(build.call_args.kwargs['l1_projection_mode'],'shadow')
            self.assertEqual(runner.main(**args,l1_projection_mode='projected',force_rerun=True),1)

    def test_invalid_unhashable_mode_has_clear_configuration_error(self):
        with self.assertRaises(ValueError):self.factory(l1_projection_mode=[])
        with self.assertRaises(ValueError):normalize_config({'suites':[get_backend().suites[0]],'l1_projection_mode':[]})

    def test_existing_positional_factory_and_executor_arguments_keep_their_meaning(self):
        config=ModelConfig(provider='custom',model_id='offline',api_key='fixture',base_url='http://offline')
        with patch('dscg.pipelines.defended.create_openai_client',return_value=Mock()):
            pipeline=make_defended_pipeline(None,None,True,True,'summary',None,0,False,True,False,
                                           model_config=config,sec_model_config=config)[0]
        self.assertFalse(pipeline.dscg_optimization_config['authorization_precheck'])
        executor=OurFrameExecutor(Recorder(),None,'summary',None,True,False)
        self.assertFalse(executor.planning_tool_view)
        self.assertEqual(executor.l1_projection_mode,'projected')

    def test_followup_user_turn_overrides_stale_query_for_projection(self):
        fixture=fixture_module.L1ProjectionTests();fixture.setUp();raw=fixture.history()
        raw.append(dict(role='user',content=[dict(type='text',content='Now quote the subjects of those transactions.')]))
        llm=Recorder();executor=OurFrameExecutor(llm)
        state=executor.query(REQUEST,fixture.runtime,{},raw,{})
        self.assertIn(ATTACK,str(llm.view))
        self.assertEqual(state[4]['dscg_l1_projection']['projected_returns'],0)

    def test_missing_blank_or_mixed_actual_user_does_not_match_supplied_query(self):
        for kind in ('missing','blank','mixed'):
            fixture=fixture_module.L1ProjectionTests();fixture.setUp();raw=fixture.history()
            if kind=='missing':raw=raw[1:]
            if kind=='blank':raw[0]['content']=[]
            if kind=='mixed':raw[0]['content'].append(dict(type='image',content='uninterpreted'))
            llm=Recorder();state=OurFrameExecutor(llm).query(REQUEST,fixture.runtime,{},raw,{})
            with self.subTest(kind=kind):
                self.assertIn(ATTACK,str(llm.view))
                self.assertEqual(state[4]['dscg_l1_projection']['projected_returns'],0)
