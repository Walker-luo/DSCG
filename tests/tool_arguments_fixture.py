"""Native baseline/DSCG clients with an offline malformed generation response."""
from contextlib import contextmanager
from contextvars import ContextVar
import json
from pathlib import Path
from unittest.mock import patch
import httpx
from openai import OpenAI

from dscg.model_config import ModelConfig
from test_request_compatibility import completion

CONFIG=ModelConfig('gpt-4o-2024-05-13','offline-key','https://offline.invalid/v1','custom')
_EVENT=ContextVar('fixture_event_file',default=None)
_BAD_AT=ContextVar('fixture_bad_generation',default=4)
_CLIENTS=ContextVar('fixture_clients',default=None)


def factory(origin,**options):
    from dscg.pipelines import baseline,defended
    clients=[];state={'generation':0}
    def handler(request):
        value=json.loads(request.content)
        if value.get('response_format'):
            try:packet=json.loads(value['messages'][-1]['content'])
            except (TypeError,ValueError):packet={}
            answer={'tools':list(packet['available_tools'])} if 'available_tools' in packet else {
                'decision':'allow','violations':[],'confidence':1,'reason_code':'OFFLINE'}
            response=completion(json.dumps(answer));kind='authorization_or_audit'
        else:
            kind='generation';state['generation']+=1
            calls=[{'id':'bad','type':'function','function':{'name':'DO_NOT_EXECUTE',
                   'arguments':'{"private-json-probe":'}}] if state['generation']==_BAD_AT.get() else None
            response=completion('offline',calls)
        if _EVENT.get():
            with Path(_EVENT.get()).open('a') as stream:stream.write(json.dumps({'kind':kind})+'\n')
        return httpx.Response(200,json=response,request=request)
    def client(*args,**kwargs):
        raw=OpenAI(api_key='offline-key',base_url=CONFIG.base_url,max_retries=0,
                   http_client=httpx.Client(transport=httpx.MockTransport(handler)))
        clients.append(raw)
        if _CLIENTS.get() is not None:_CLIENTS.get().append(raw)
        return raw
    with patch.object(baseline,'create_openai_client',side_effect=client),patch.object(defended,'create_openai_client',side_effect=client):
        if origin:
            result=baseline.make_openai_compatible_pipeline(model_config=CONFIG)
        else:
            allowed={'use_sandbox','use_security_checker','trace_level','audit_retries','completion_prompt',
                     'audit_router_mode','audit_router_artifact','audit_router_threshold','planning_tool_view',
                     'delegated_tasks','l1_projection_mode','prompt_profile','tool_metadata'}
            options={**options,'prompt_profile':'legacy-v34'}
            result=defended.make_defended_pipeline(model_config=CONFIG,sec_model_config=CONFIG,
                                                  **{k:v for k,v in options.items() if k in allowed})
    result[0]._fixture_clients=clients
    return result


@contextmanager
def patched():
    from experiments import run_partial_benchmark as runner
    with patch.object(runner,'resolve_model_config',return_value=CONFIG), \
         patch.object(runner,'make_openai_compatible_pipeline',side_effect=lambda *a,**k:factory(True,**k)), \
         patch.object(runner,'make_defended_pipeline',side_effect=lambda *a,**k:factory(False,**k)):
        yield


def execute(job):
    from experiments import run_partial_benchmark as runner
    path=next(p for p in job['bindings'].checked if p.name=='run_manifest.json'
              and p.parent.name==job['suite'] and p.parent.parent.name==job['attack'])
    path.parent.mkdir(parents=True,exist_ok=True)
    selection=job['bindings'].checked[path]['task_selection']
    from agentdojo.attacks.attack_registry import ATTACKS
    preflight=len(selection['injections']) if job['options']['run_attack'] and not ATTACKS[job['attack']].is_dos_attack else 0
    clients=[];client_token=_CLIENTS.set(clients)
    event_token=_EVENT.set(path.parent/'fixture_requests.jsonl')
    bad_token=_BAD_AT.set(1 if job.get('fixture_goal_error') else preflight+1)
    try:
        with patched():return runner._execute_group(job)
    finally:
        _EVENT.reset(event_token);_BAD_AT.reset(bad_token)
        for client in clients:client.close()
        _CLIENTS.reset(client_token)
