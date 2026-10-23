from authorization_fixture import step_content
"""Native AgentDojo tools/predicates + authored MockTransport, never model efficacy."""
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest
from unittest.mock import patch

import httpx
from openai import OpenAI
from agentdojo import logging
from dscg.benchmark_catalog import get_backend,get_suite
from dscg.model_config import ModelConfig
from dscg.pipelines import defended as d
from dscg.tool_metadata import resolve_tool_metadata,load_tool_metadata
from experiments.common.benchmark_tasks import run_native_suite
from experiments.common.native_cache_compat import ensure_native_cache_model_ready
from test_request_compatibility import completion


@unittest.skipUnless(get_backend().id=='agentdojo','AgentDojo native banking/slack suite')
class NativeIntentSourceTests(unittest.TestCase):
    def exercise(self,scene,user_id,*,progress=False,bad=None):
        suite=get_suite('v1.2',scene);user=suite.get_user_task_by_id(user_id)
        env=user.init_environment(suite.load_and_inject_default_environment({}))
        actions=[(c.function,dict(c.args)) for c in user.ground_truth(env)]
        grants={name for name,args in actions}
        if scene=='slack' and user_id=='user_task_3':grants.add('post_webpage')
        if bad=='destination':actions[-1]=('post_webpage',{'url':'www.informations.com','content':'Summary'})
        if bad=='source':actions[-1]=('send_channel_message',{'channel':'general','body':'Visit attacker.example'})
        state={'generation':0};requests=[];clients=[]
        def handler(request):
            body=json.loads(request.content);requests.append(body)
            if body.get('response_format'):
                packet=json.loads(body['messages'][-1]['content'])
                if 'available_tools' in packet:
                    value=json.loads(step_content(json.dumps({'tools':sorted(grants & set(packet['available_tools']))}),body))
                else:
                    off_task=any(a['tool_name']=='post_webpage' or 'attacker.example' in json.dumps(a['untrusted_argument_data'])
                                 for a in packet['current_actions'])
                    value=dict(decision='deny' if off_task else 'allow',violations=['OFF_TASK_ACTION'] if off_task else [],confidence=.9,
                               reason_code='OFF_TASK_ACTION' if off_task else 'ALIGNED')
                result=completion(json.dumps(value))
            else:
                n=state['generation'];state['generation']+=1
                if n<len(actions):
                    name,args=actions[n]
                    result=completion('',[{'id':f'call-{n}','type':'function','function':{'name':name,'arguments':json.dumps(args)}}])
                    result['choices'][0]['finish_reason']='tool_calls'
                else:result=completion('Your total spending was 1050. Task complete.')
            return httpx.Response(200,json=result,request=request)
        def client(config):
            raw=OpenAI(api_key='offline',base_url='https://offline.invalid/v1',max_retries=0,
                       http_client=httpx.Client(transport=httpx.MockTransport(handler)))
            clients.append(raw);return raw
        config=ModelConfig('qwen3.7-flash','offline','https://offline.invalid/v1','custom')
        root=Path(__file__).resolve().parents[1]/'workshop/artifacts/20261021_intent_source_relaxation/native'
        root.mkdir(parents=True,exist_ok=True)
        try:
            with TemporaryDirectory(dir=root) as temp,patch.object(d,'create_openai_client',side_effect=client),redirect_stdout(StringIO()):
                pipe,main,audit=d.make_defended_pipeline(model_config=config,sec_model_config=config,
                    tool_metadata=load_tool_metadata(resolve_tool_metadata(backend=get_backend()).path),audit_router_mode='shadow')
                pipe.name='none';ensure_native_cache_model_ready();steps=[]
                with logging.OutputLogger(temp):
                    result=run_native_suite(pipe,suite,None,Path(temp),False,user_tasks=[user_id],injection_tasks=[],
                        benchmark_version='v1.2',on_step=steps.append if progress else None)
                path=Path(temp)/'none'/scene/user_id/'none/none.json';trace=json.loads(path.read_text())
                self.assertEqual(result['utility_results'][(user_id,'')],bad is None)
                self.assertEqual(steps,['score'] if progress else [])
                self.assertEqual(state['generation'],len(actions)+1)
                self.assertEqual(sum(p['failed_calls'] for p in main.snapshot().values()),0)
                self.assertEqual(sum(p['failed_calls'] for p in audit.snapshot().values()),0)
                if bad:
                    self.assertTrue(trace['dscg_audit_summary']['blocked_actions'])
                    self.assertNotIn('AUDIT_SCHEMA_INVALID',trace['dscg_audit_summary']['reason_code_counts'])
                else:
                    self.assertEqual(trace['dscg_audit_summary']['blocked_actions'],0)
                    self.assertEqual(trace['dscg_audit_summary']['mediation_failure_counts'],{})
                return {'utility':result['utility_results'], 'main_tokens':main.get_total_tokens(),'audit_tokens':audit.get_total_tokens(),
                        'requests':len(requests),'proposals':[a[0] for a in actions]}
        finally:
            for raw in clients:raw.close()

    def test_native_preparatory_reads_derived_money_and_multistep_sends(self):
        for scene,uid in [('banking','user_task_1'),('banking','user_task_3'),('banking','user_task_6'),
                          ('slack','user_task_1'),('slack','user_task_3'),('slack','user_task_5')]:
            with self.subTest(scene=scene,user=uid):
                self.assertEqual(self.exercise(scene,uid),self.exercise(scene,uid,progress=True))

    def test_broad_native_grants_cannot_execute_wrong_destination_or_source_command(self):
        for bad in ('destination','source'):
            with self.subTest(bad=bad):self.exercise('slack','user_task_3',progress=True,bad=bad)
