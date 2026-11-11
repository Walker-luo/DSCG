"""Real native suite and MockTransport: bad model JSON never executes a tool."""
from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import httpx
from openai import OpenAI
from agentdojo import agent_pipeline
from dscg.benchmark_catalog import get_backend,get_suite,get_suites
from dscg.token_tracking import TokenTrackerClient
from experiments.common.benchmark_progress import run_suite_with_progress
from experiments.common.native_cache_compat import ensure_native_cache_model_ready
from test_request_compatibility import completion


class ToolArgumentsJSONTests(unittest.TestCase):
    def setUp(self):
        root=Path(__file__).resolve().parents[1]/'workshop/artifacts/20261021_tool_arguments_json/tests'
        root.mkdir(parents=True,exist_ok=True)
        temp=TemporaryDirectory(dir=root);self.addCleanup(temp.cleanup)
        self.root=Path(temp.name);self.suite=get_suite('v1.2',get_suites()[0])
        ensure_native_cache_model_ready()

    def pipeline(self,responses):
        captured=[]
        def handler(request):
            captured.append(json.loads(request.content))
            return httpx.Response(200,json=completion(calls=responses[len(captured)-1]),request=request)
        raw=OpenAI(api_key='offline-key',base_url='https://offline.invalid/v1',max_retries=0,
                   http_client=httpx.Client(transport=httpx.MockTransport(handler)))
        self.addCleanup(raw.close)
        tracker=TokenTrackerClient(raw)
        llm=agent_pipeline.OpenAILLM(tracker,'gpt-4o-2024-05-13',temperature=0)
        pipe=agent_pipeline.AgentPipeline([agent_pipeline.SystemMessage('offline fixture'),agent_pipeline.InitQuery(),
            llm,agent_pipeline.ToolsExecutionLoop([agent_pipeline.ToolsExecutor(),llm])])
        pipe.name='ignore_previous'
        return pipe,tracker,captured

    @staticmethod
    def call(arguments,tool='DO_NOT_EXECUTE'):
        return {'id':'fixture-call','type':'function','function':{'name':tool,'arguments':arguments}}

    def clean(self,pipe,on_step=None):
        from agentdojo import logging
        with redirect_stdout(StringIO()),logging.OutputLogger(str(self.root)):
            return run_suite_with_progress(pipe,self.suite,None,self.root,False,
                user_tasks=list(self.suite.user_tasks)[:2],injection_tasks=[],benchmark_version='v1.2',on_step=on_step)

    def test_native_bad_json_is_one_null_error_and_next_task_runs_once(self):
        for invalid in ['', '{"private-value":', '{not-json']:
            with self.subTest(invalid=invalid),TemporaryDirectory(dir=self.root) as temp:
                old=self.root;self.root=Path(temp)
                try:
                    pipe,tracker,calls=self.pipeline([[self.call(invalid)],None])
                    steps=[]
                    results=self.clean(pipe,steps.append)
                    first,second=list(self.suite.user_tasks)[:2]
                    self.assertIsNone(results['utility_results'][(first,'')])
                    self.assertIsNone(results['security_results'][(first,'')])
                    self.assertIsInstance(results['utility_results'][(second,'')],bool)
                    self.assertEqual(len(calls),2)
                    self.assertEqual(steps,['score','score'])
                    self.assertEqual(tracker.get_total_tokens(),4)
                    self.assertEqual(sum(p['failed_calls'] for p in tracker.snapshot().values()),0)
                    self.assertEqual(len(results['task_errors']),1)
                    error=results['task_errors'][0]
                    self.assertEqual(error['reason_code'],'MODEL_TOOL_ARGUMENTS_INVALID_JSON')
                    self.assertEqual(error['arguments_length'],len(invalid))
                    self.assertEqual(error['response_finish_reason'],'stop')
                    self.assertEqual(error['response_completion_tokens'],1)
                    self.assertEqual(error['json_error_kind'],'empty_arguments' if not invalid else 'json_syntax')
                    self.assertNotIn('private-value',json.dumps(error))
                    records=list((self.root/'ignore_previous'/self.suite.name).glob('task_errors.jsonl'))
                    self.assertEqual(len(records),1)
                finally:self.root=old

    def test_mixed_valid_invalid_calls_execute_neither_candidate(self):
        # The native parser constructs the whole assistant message before execution.
        pipe,tracker,calls=self.pipeline([[self.call('{}'),self.call('{')],None])
        with patch.object(agent_pipeline.ToolsExecutor,'query',side_effect=AssertionError('tool executed')):
            results=self.clean(pipe)
        self.assertEqual(len(results['task_errors']),1)
        self.assertEqual(len(calls),2)

    def test_unrelated_json_error_still_escapes(self):
        class Broken:
            name='ignore_previous'
            def query(self,*a,**k):raise json.JSONDecodeError('unrelated','',0)
        # Native AgentDyn may already catch this in its own task loop; retain that behavior.
        if get_backend().id=='agentdojo':
            with self.assertRaises(json.JSONDecodeError):self.clean(Broken())

    def test_corrupt_native_cache_does_not_call_model_or_become_tool_json_error(self):
        first=list(self.suite.user_tasks)[0]
        path=self.root/'ignore_previous'/self.suite.name/first/'none.json'
        path.parent.mkdir(parents=True);path.write_text('{corrupt-cache')
        pipe,tracker,calls=self.pipeline([None,None])
        with self.assertRaises(json.JSONDecodeError):self.clean(pipe)
        self.assertEqual(calls,[])
        self.assertFalse((path.parents[1]/'task_errors.jsonl').exists())

    def test_valid_arguments_and_model_client_are_preserved(self):
        from agentdojo.functions_runtime import FunctionsRuntime
        from agentdojo.types import text_content_block_from_string as block
        from experiments.common.benchmark_tasks import _TaskPipelineProbe
        pipe,tracker,calls=self.pipeline([[self.call('{"value":1}')]])
        llm=pipe.elements[2];client=llm.client;method=llm.query
        result=_TaskPipelineProbe(llm).query('task',FunctionsRuntime([]),messages=[{'role':'user','content':[block('task')]}])
        self.assertEqual(result[3][-1]['tool_calls'][0].args,{'value':1})
        self.assertIs(llm.client,client)
        self.assertEqual(llm.query,method)
        self.assertEqual(len(calls),1)

    def test_attack_constructor_json_error_is_not_reclassified(self):
        from agentdojo import logging
        from agentdojo.agent_pipeline.llms.openai_llm import _openai_to_tool_call
        from openai.types.chat import ChatCompletionMessageFunctionToolCall
        native_call=ChatCompletionMessageFunctionToolCall(id='bad',type='function',function={'name':'bad','arguments':'{'})
        def attack_payload(*args):_openai_to_tool_call(native_call)
        attack=SimpleNamespace(name='ignore_previous',is_dos_attack=False,attack=attack_payload)
        pipe,tracker,calls=self.pipeline([None])
        with logging.OutputLogger(str(self.root)),self.assertRaises(json.JSONDecodeError):
            run_suite_with_progress(pipe,self.suite,attack,self.root,False,
                user_tasks=list(self.suite.user_tasks)[:1],injection_tasks=list(self.suite.injection_tasks)[:1],benchmark_version='v1.2')
        self.assertEqual(len(calls),0)
        self.assertFalse(list(self.root.rglob('task_errors.jsonl')))
