# Frozen v3.4 controls; intent-flow defaults are tested in test_intent_flow*.py.
"""Factory wiring must apply the view and reject candidates before audit."""
from copy import deepcopy
import unittest
from unittest.mock import Mock, patch
from agentdojo.functions_runtime import FunctionsRuntime, FunctionCall
from baseintent.model_config import ModelConfig
from baseintent.input_isolation import FRAMEWORK_VERSION
from baseintent.pipelines.defended import make_defended_pipeline


class Planner:
    def __init__(self,call):self.views=[];self.call=call
    def query(self,q,r,e,m,a):
        self.views.append(deepcopy(m))
        response={'role':'assistant','content':[],'tool_calls':[self.call]} if len(self.views)==1 else {
            'role':'assistant','content':[{'type':'text','content':'final facts'}],'tool_calls':[]}
        return q,r,e,[*m,response],a


class ThreeLayerPipelineTests(unittest.TestCase):
    def build(self,call,**flags):
        self.config=ModelConfig(provider='custom',model_id='offline',api_key='fixture',base_url='http://offline')
        self.client=Mock()
        self.client.chat.completions.create.return_value=type('Response',(),{'choices':[
            type('Choice',(),{'message':type('Message',(),{'content':'{"tools": []}','refusal':None})(),'finish_reason':'stop'})()]})()
        with patch('baseintent.pipelines.defended.create_openai_client',return_value=self.client):
            pipeline,_,_=make_defended_pipeline(model_config=self.config,sec_model_config=self.config,**flags, prompt_profile='legacy-v34')
        planner=Planner(call);pipeline.task_executor.llm=planner
        return pipeline,planner
    def runtime(self):
        runtime=FunctionsRuntime();self.effects=[]
        @runtime.register_function
        def read_data() -> str:
            """Read task data."""
            self.effects.append('read');return '姓名张三 ID42 $3.40'
        return runtime
    def test_default_loop_exposes_marked_view_but_returns_raw_history(self):
        runtime=self.runtime()
        metadata={'read_data':dict(effect='read',source='local',sink='none',sensitivity='public',idempotent=True,reversible=False)}
        pipeline,planner=self.build(FunctionCall(function='read_data',args={},id='1'),tool_metadata=metadata)
        state=pipeline.query('Read the data',runtime)
        self.assertEqual(self.effects,['read']);self.assertEqual(len(planner.views),2)
        raw=next(m for m in state[3] if m['role']=='tool')
        shown=next(m for m in planner.views[1] if m['role']=='tool')
        self.assertEqual(raw['content'][0]['content'],'姓名张三 ID42 $3.40')
        self.assertIn('trust=untrusted',shown['content'][0]['content'])
        self.assertTrue(state[4]['baseintent_framework']['input_isolation'])
        self.assertTrue(state[4]['baseintent_framework']['authorization_precheck'])
        self.assertEqual(state[4]['baseintent_layer_routing']['public_read_bypass_batches'],1)
        self.assertEqual(state[4]['baseintent_audit_decision']['semantic_attempt'],0)
    def test_missing_metadata_candidate_reaches_gate_and_skips_real_auditor(self):
        runtime=self.runtime();pipeline,planner=self.build(FunctionCall(function='read_data',args={},id='1'))
        state=pipeline.query('Read the data',runtime)
        self.assertEqual(self.effects,[])
        self.assertEqual(state[4]['baseintent_layer_routing']['precheck_rejected_batches'],1)
        self.assertEqual(state[4]['baseintent_audit_decision']['semantic_attempt'],0)
        self.assertEqual(state[4]['baseintent_action_ledger'][0]['state'],'blocked')
    def test_v2_api_control_executes_with_original_view(self):
        runtime=self.runtime();metadata={'read_data':dict(effect='read',source='local',sink='none',sensitivity='public',idempotent=True,reversible=False)}
        pipeline,planner=self.build(FunctionCall(function='read_data',args={},id='1'),tool_metadata=metadata,
                                    input_isolation=False,authorization_precheck=False)
        state=pipeline.query('Read the data',runtime)
        self.assertEqual(self.effects,['read'])
        shown=next(m for m in planner.views[1] if m['role']=='tool')
        self.assertEqual(shown['content'][0]['content'],'姓名张三 ID42 $3.40')
        self.assertFalse(state[4]['baseintent_framework']['input_isolation'])
        self.assertFalse(state[4]['baseintent_framework']['authorization_precheck'])
    def test_all_old_switches_off_leave_no_input_layer(self):
        runtime=self.runtime();pipeline,planner=self.build(FunctionCall(function='read_data',args={},id='1'),
                                                          use_sandbox=False,use_security_checker=False)
        state=pipeline.query('Read the data',runtime)
        self.assertEqual(self.effects,['read'])
        self.assertNotIn('baseintent_input_isolation',state[4])
        self.assertEqual(next(m for m in planner.views[1] if m['role']=='tool')['content'][0]['content'],'姓名张三 ID42 $3.40')
    def test_default_cache_identity_binds_version_and_actual_layer_flags(self):
        call=FunctionCall(function='read_data',args={},id='1')
        names=[]
        for l1,l2 in ((True,True),(False,True),(True,False),(False,False)):
            pipeline,_=self.build(call,input_isolation=l1,authorization_precheck=l2)
            names.append(pipeline.name)
            self.assertIn('BaseIntent-legacy-v34', pipeline.name)
        self.assertEqual(len(set(names)),4)
        self.assertNotEqual(names[0],'offline-newFrame-OursFull')

    def test_router_modes_are_bound_to_pipeline_identity_and_configuration(self):
        names=[]
        for mode in ('off','shadow','selective'):
            pipeline,_=self.build(FunctionCall(function='read_data',args={},id='1'),audit_router_mode=mode)
            names.append(pipeline.name)
            self.assertEqual(pipeline.baseintent_optimization_config['audit_router_mode'],mode)
        self.assertEqual(len(set(names)),3)
        for flags in ({'use_sandbox':False},{'use_security_checker':False}):
            with self.assertRaises(ValueError):self.build(FunctionCall(function='read_data',args={},id='1'),audit_router_mode='selective',**flags)

    def test_calibration_configuration_binds_execution_switches(self):
        hashes=[]
        for flags in ({},{'input_isolation':False},{'authorization_precheck':False},{'audit_retries':1},{'completion_prompt':True}):
            p,_=self.build(FunctionCall(function='read_data',args={},id='1'),audit_router_mode='shadow',**flags)
            hashes.append(p.baseintent_optimization_config['audit_router_config_sha256'])
        self.assertEqual(len(set(hashes)),len(hashes))
