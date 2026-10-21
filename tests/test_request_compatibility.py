"""Chat transport contracts using MockTransport; no sockets or paid models."""
from copy import deepcopy
import json
from types import SimpleNamespace
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import httpx
from openai import BadRequestError, OpenAI, UnprocessableEntityError

from dscg.model_config import ModelConfig, create_openai_client
from dscg.token_tracking import TokenTrackerClient


def completion(content='offline', calls=None):
    return {'id': 'offline', 'object': 'chat.completion', 'created': 0, 'model': 'offline',
            'choices': [{'index': 0, 'finish_reason': 'stop', 'message':
                         {'role': 'assistant', 'content': content, 'tool_calls': calls}}],
            'usage': {'prompt_tokens': 1, 'completion_tokens': 1, 'total_tokens': 2}}


class RequestCompatibilityTests(unittest.TestCase):
    def config(self, provider='dashscope', model='qwen-future-fixture'):
        return ModelConfig(model, 'offline-key', 'https://offline.invalid/v1', provider)

    def client(self, handler, provider='dashscope'):
        raw = OpenAI(api_key='offline-key', base_url='https://offline.invalid/v1',
                     http_client=httpx.Client(transport=httpx.MockTransport(handler)))
        self.addCleanup(raw.close)
        with patch('openai.OpenAI', return_value=raw):
            client = create_openai_client(self.config(provider))
        return client, raw

    def test_dashscope_copies_roles_only_preserving_every_other_field(self):
        captured = []
        def handler(request):
            value = json.loads(request.content)
            captured.append(value)
            if any(m['role'] == 'developer' for m in value['messages']):
                return httpx.Response(400, json={'error': {'code': 'InvalidParameter',
                    'param': 'messages[0].role', 'message': 'unsupported developer'}}, request=request)
            return httpx.Response(200, json=completion(), request=request)
        client, _ = self.client(handler)
        messages = [{'role': 'developer', 'content': [{'type':'text','text':'trusted'}]},
                    {'role':'system','content':'also trusted'}, {'role':'user','content':'developer is just data'},
                    {'role':'assistant','content':None,'tool_calls':[{'id':'c1','type':'function',
                     'function':{'name':'read_data','arguments':'{}'}}]},
                    {'role':'tool','content':'data','tool_call_id':'c1'}]
        tools = [{'type':'function','function':{'name':'read_data','parameters':{'type':'object','properties':{}}}}]
        original = deepcopy((messages, tools))
        client.chat.completions.create(model='qwen-future-fixture', messages=messages,
            tools=tools, tool_choice='auto', temperature=0, reasoning_effort='none')
        expected = deepcopy(messages); expected[0]['role'] = 'system'
        self.assertEqual(captured[0]['messages'], expected)
        self.assertEqual(captured[0]['tools'], tools)
        self.assertEqual((messages, tools), original)
        self.assertEqual(captured[0]['reasoning_effort'], 'none')
        self.assertEqual(len(captured), 1)

    def test_other_provider_keeps_original_client_and_developer_role(self):
        captured = []
        def handler(request):
            captured.append(json.loads(request.content))
            return httpx.Response(200, json=completion(), request=request)
        for provider in ('openai', 'ollama'):
            client, raw = self.client(handler, provider)
            self.assertIs(client, raw)
            client.chat.completions.create(model='fixture', messages=[{'role':'developer','content':'trusted'}])
            self.assertEqual(captured[-1]['messages'][0]['role'], 'developer')
            self.assertNotIn('chat_request_adapter', self.config(provider).public_dict())

    def test_deepseek_chat_adapts_agentdyn_role_without_changing_request(self):
        captured = []
        def handler(request):
            value = json.loads(request.content)
            captured.append(value)
            if any(message['role'] == 'developer' for message in value['messages']):
                return httpx.Response(422, json={'error': {'code': 'invalid_request_error',
                    'message': 'PRIVATE_RESPONSE'}}, request=request)
            if any(message['role'] == 'system' and not isinstance(message['content'], str)
                   for message in value['messages']):
                return httpx.Response(422, json={'error': {'code': 'invalid_request_error'}}, request=request)
            return httpx.Response(200, json=completion(), request=request)
        client, raw = self.client(handler, provider='deepseek')
        self.assertIsNot(client, raw)
        messages = [{'role': 'developer', 'content': [{'type': 'text', 'text': 'PRIVATE_'},
                    {'type': 'text', 'text': 'REQUEST'}]},
                    {'role': 'user', 'content': 'task'},
                    {'role': 'assistant', 'content': None, 'tool_calls': [{'id': 'c1', 'type': 'function',
                        'function': {'name': 'read_data', 'arguments': '{}'}}]},
                    {'role': 'tool', 'content': 'result', 'tool_call_id': 'c1'}]
        tools = [{'type': 'function', 'function': {'name': 'read_data',
            'parameters': {'type': 'object', 'properties': {}}}}]
        original = deepcopy((messages, tools))
        client.chat.completions.create(model='deepseek-flash', messages=messages,
            tools=tools, reasoning_effort='none')
        expected = deepcopy(messages)
        expected[0]['role'] = 'system'
        expected[0]['content'] = 'PRIVATE_REQUEST'
        self.assertEqual(captured[0]['messages'], expected)
        self.assertEqual(captured[0]['tools'], tools)
        self.assertEqual(captured[0]['reasoning_effort'], 'none')
        self.assertEqual((messages, tools), original)
        self.assertEqual(len(captured), 1)

    def test_deepseek_adapter_identity_rejects_old_run_binding(self):
        from dscg.benchmark_catalog import benchmark_identity
        from experiments.common.benchmark_reuse import _compatible_binding
        config = self.config('deepseek', 'deepseek-flash')
        current = config.public_dict()
        self.assertEqual(current['chat_request_adapter'], 'deepseek-system-text-v1')
        self.assertNotIn('offline-key', json.dumps(current))
        old = {key: value for key, value in current.items() if key != 'chat_request_adapter'}
        self.assertFalse(_compatible_binding(
            {'benchmark': benchmark_identity(), 'main_model': old},
            {'benchmark': benchmark_identity(), 'main_model': current}))

    def test_deepseek_agentdyn_native_goal_and_tool_followup_roles(self):
        from agentdojo.agent_pipeline.llms.openai_llm import OpenAILLM, _message_to_openai
        from agentdojo.functions_runtime import FunctionCall, FunctionsRuntime
        from dscg.benchmark_catalog import get_backend, get_suite
        if get_backend().id != 'agentdyn':
            self.skipTest('AgentDyn native serializer is not installed')
        suite = get_suite('v1.2', 'shopping')
        self.assertEqual(_message_to_openai({'role': 'system', 'content':
            [{'type': 'text', 'content': 'trusted'}]}, 'deepseek-flash')['role'], 'developer')
        captured = []
        def handler(request):
            value = json.loads(request.content)
            captured.append(value)
            if any(message['role'] == 'developer' for message in value['messages']):
                return httpx.Response(422, json={'error': {'code': 'invalid_request_error'}}, request=request)
            if any(message['role'] == 'system' and not isinstance(message['content'], str)
                   for message in value['messages']):
                return httpx.Response(422, json={'error': {'code': 'invalid_request_error'}}, request=request)
            return httpx.Response(200, json=completion(), request=request)
        client, _ = self.client(handler, provider='deepseek')
        llm = OpenAILLM(TokenTrackerClient(client), 'deepseek-flash', reasoning_effort='none')
        runtime = FunctionsRuntime(suite.tools)
        text = lambda value: [{'type': 'text', 'content': value}]
        messages = [{'role': 'system', 'content': text('trusted')},
                    {'role': 'user', 'content': text('task')}]
        llm.query('task', runtime, messages=messages)
        self.assertEqual([m['role'] for m in captured[-1]['messages']], ['system', 'user'])
        self.assertIsInstance(captured[-1]['messages'][0]['content'], str)
        call = FunctionCall(function=suite.tools[0].name, args={}, id='offline-call')
        messages += [{'role': 'assistant', 'content': [], 'tool_calls': [call]},
                     {'role': 'tool', 'content': text('result'), 'tool_call_id': call.id,
                      'tool_call': call, 'error': None}]
        llm.query('task', runtime, messages=messages)
        self.assertEqual([m['role'] for m in captured[-1]['messages']],
                         ['system', 'user', 'assistant', 'tool'])
        self.assertEqual(captured[-1]['messages'][-1]['tool_call_id'], call.id)
        self.assertEqual(len(captured), 2)

    def test_deepseek_baseline_and_defended_factories_share_adapter(self):
        from dscg.pipelines.baseline import make_openai_compatible_pipeline
        from dscg.pipelines.defended import make_defended_pipeline
        config = self.config('deepseek', 'deepseek-flash')
        def handler(request):
            value = json.loads(request.content)
            self.assertFalse(any(m['role'] == 'developer' for m in value['messages']))
            return httpx.Response(200, json=completion(), request=request)
        def raw_factory(**kwargs):
            raw = OpenAI(**kwargs, http_client=httpx.Client(transport=httpx.MockTransport(handler)))
            self.addCleanup(raw.close)
            return raw
        with patch('openai.OpenAI', side_effect=raw_factory):
            baseline, main = make_openai_compatible_pipeline(model_config=config)
            defended, main_defended, security = make_defended_pipeline(
                model_config=config, sec_model_config=config)
        for pipeline in (baseline, defended):
            self.assertEqual(pipeline.dscg_model_config['chat_request_adapter'], 'deepseek-system-text-v1')
        for tracker in (main, main_defended, security):
            tracker.chat.completions.create(model=config.model_id,
                messages=[{'role': 'developer', 'content': 'trusted'}])

    def test_deepseek_422_reports_effective_system_role_without_body(self):
        def handler(request):
            return httpx.Response(422, json={'error': {'code': 'invalid_request_error',
                'message': 'PRIVATE_RESPONSE'}}, request=request)
        client, _ = self.client(handler, provider='deepseek')
        tracker = TokenTrackerClient(client)
        with self.assertRaises(UnprocessableEntityError) as failure:
            tracker.chat.completions.create(model='deepseek-flash',
                messages=[{'role': 'developer', 'content': 'PRIVATE_REQUEST'},
                          {'role': 'user', 'content': 'task'}])
        from dscg.request_compatibility import api_error_diagnostics
        detail = api_error_diagnostics(failure.exception)
        self.assertEqual(detail['http_status'], 422)
        self.assertEqual(detail['request_role_counts'], {'system': 1, 'user': 1})
        self.assertNotIn('PRIVATE', json.dumps(detail))
        self.assertEqual(tracker.snapshot()['generation']['failed_calls'], 1)

    def test_deepseek_keeps_unknown_trusted_blocks_for_provider_validation(self):
        captured = []
        def handler(request):
            captured.append(json.loads(request.content))
            return httpx.Response(422, json={'error': {'code': 'invalid_request_error'}}, request=request)
        client, _ = self.client(handler, provider='deepseek')
        messages = [{'role': 'developer', 'content': [{'type': 'image_url',
            'image_url': {'url': 'https://offline.invalid/image.png'}}]}]
        original = deepcopy(messages)
        with self.assertRaises(UnprocessableEntityError):
            client.chat.completions.create(model='deepseek-flash', messages=messages)
        self.assertEqual(captured[0]['messages'][0]['role'], 'system')
        self.assertEqual(captured[0]['messages'][0]['content'], original[0]['content'])
        self.assertEqual(messages, original)
        self.assertEqual(len(captured), 1)

    def test_adapter_identity_enters_public_config_without_credentials(self):
        value = self.config().public_dict()
        self.assertEqual(value['chat_request_adapter'], 'dashscope-system-v1')
        self.assertNotIn('offline-key', json.dumps(value))

    def test_failure_records_effective_roles_and_only_safe_public_error_fields(self):
        captured = []
        def handler(request):
            captured.append(json.loads(request.content))
            return httpx.Response(400, json={'error':{'code':'InvalidParameter',
                'param':'messages[0].role', 'message':'PRIVATE_BODY offline-key',
                'secret':'PRIVATE_BODY'}}, request=request)
        adapted, _ = self.client(handler)
        tracked = TokenTrackerClient(adapted)
        with self.assertRaises(BadRequestError) as error:
            tracked.chat.completions.create(model='fixture',
                messages=[{'role':'developer','content':'PRIVATE_REQUEST'}])
        from dscg.request_compatibility import api_error_diagnostics
        detail = api_error_diagnostics(error.exception)
        self.assertEqual(detail['http_status'], 400)
        self.assertEqual(detail['provider_error_code'], 'InvalidParameter')
        self.assertEqual(detail['provider_error_param'], 'messages[0].role')
        self.assertEqual(detail['request_role_counts'], {'system': 1})
        phase = tracked.snapshot()['generation']
        self.assertEqual(phase['last_api_error'], detail)
        self.assertEqual((phase['api_calls'], phase['failed_calls']), (1, 1))
        self.assertNotIn('PRIVATE', json.dumps(detail))
        self.assertNotIn('offline-key', json.dumps(detail))
        self.assertEqual(len(captured), 1)  # no request fallback or extra retry

    def test_diagnostics_reject_free_text_and_unrecognized_roles(self):
        from dscg.request_compatibility import api_error_diagnostics
        request = httpx.Request('POST', 'https://offline.invalid/v1/chat/completions')
        error = BadRequestError('SECRET', response=httpx.Response(400, request=request),
                                body={'code':'PRIVATE TEXT', 'param':'SECRET REQUEST TEXT'})
        detail = api_error_diagnostics(error, [{'role':'SECRET', 'content':'PRIVATE'}])
        self.assertIsNone(detail['provider_error_code'])
        self.assertIsNone(detail['provider_error_param'])
        self.assertEqual(detail['request_role_counts'], {'other':1})
        self.assertNotIn('SECRET', json.dumps(detail))

    def test_native_catalog_first_and_tool_followup_requests_share_adapter(self):
        from agentdojo.agent_pipeline.llms.openai_llm import OpenAILLM
        from agentdojo.functions_runtime import FunctionsRuntime
        from dscg.benchmark_catalog import get_suites, get_suite
        captured = []
        def handler(request):
            value = json.loads(request.content); captured.append(value)
            if any(m['role']=='developer' for m in value['messages']):
                return httpx.Response(400, json={'error':{'code':'InvalidParameter','message':'unsupported role'}}, request=request)
            return httpx.Response(200, json=completion(), request=request)
        client, _ = self.client(handler)
        llm = OpenAILLM(TokenTrackerClient(client), 'qwen3.7-flash', reasoning_effort='none')
        for name in get_suites():
            with self.subTest(suite=name):
                suite = get_suite('v1.2', name)
                runtime = FunctionsRuntime(suite.tools)
                text = lambda value: [{'type':'text','content':value}]
                messages = [{'role':'system','content':text('trusted')}, {'role':'user','content':text('task')}]
                llm.query('task', runtime, messages=messages)
                first = captured[-1]
                self.assertEqual([m['role'] for m in first['messages']], ['system','user'])
                self.assertEqual(len(first['tools']), len(suite.tools))
                from agentdojo.functions_runtime import FunctionCall
                call = FunctionCall(function=suite.tools[0].name, args={}, id='offline-call')
                messages += [{'role':'assistant','content':[], 'tool_calls':[call]},
                             {'role':'tool','content':text('offline tool result'), 'tool_call_id':call.id,
                              'tool_call':call,'error':None}]
                llm.query('task', runtime, messages=messages)
                following = captured[-1]
                self.assertEqual([m['role'] for m in following['messages']], ['system','user','assistant','tool'])
                self.assertEqual(following['tools'], first['tools'])
                self.assertEqual(following['messages'][-1]['tool_call_id'], call.id)

    def test_run_failure_index_keeps_bounded_api_diagnostics(self):
        from experiments.common.partial_reporting import write_run_overview
        from dscg.benchmark_catalog import get_suites
        artifacts = Path(__file__).resolve().parents[1]/'workshop/artifacts/20261019_agentdyn_qwen_roles'
        artifacts.mkdir(parents=True, exist_ok=True)
        detail = {'schema_version':'dscg.api-error.v1', 'http_status':400,
                  'provider_error_code':'InvalidParameter','provider_error_param':'messages[0].role',
                  'request_role_counts':{'system':1,'user':1}}
        suite = get_suites()[0]
        with TemporaryDirectory(dir=artifacts) as tmp:
            root = Path(tmp)
            write_run_overview(root, ['fixture'], [suite],
                [{'attack':'fixture','failed_suite':suite,'status':'error',
                  'error_type':'BadRequestError','api_error':detail}], [], model_id='offline')
            case = json.loads((root/'failure_cases.jsonl').read_text().splitlines()[0])
            self.assertEqual(case['api_error'], detail)
            self.assertEqual(case['sample_status'], 'infrastructure_error')

    def test_group_failure_diagnostics_reach_execution_manifest_and_index(self):
        from experiments import run_partial_benchmark as runner
        from dscg.benchmark_catalog import get_backend, get_suites
        from contextlib import redirect_stdout
        from io import StringIO
        import serial_fixture
        from dscg.request_compatibility import attach_api_error
        artifacts = Path(__file__).resolve().parents[1]/'workshop/artifacts/20261019_agentdyn_qwen_roles'
        artifacts.mkdir(parents=True, exist_ok=True)
        request = httpx.Request('POST', 'https://offline.invalid/v1/chat/completions')
        error = BadRequestError('PRIVATE', response=httpx.Response(400, request=request),
                                body={'code':'InvalidParameter','param':'messages[0].role','message':'PRIVATE'})
        detail = attach_api_error(error, [{'role':'system','content':'PRIVATE'}])
        with TemporaryDirectory(dir=artifacts) as tmp, serial_fixture.patched(), redirect_stdout(StringIO()), \
                patch.object(runner, '_execute_group', side_effect=error):
            self.assertEqual(runner.main(origin=True, suites=[get_suites()[0]], attack='tool_knowledge',
                results_dir=tmp, run_name='api_error'), 1)
            base = Path(tmp)/get_backend().id/'offline-model_api_error'
            manifest = json.loads((base/'attack_manifest.json').read_text())
            self.assertEqual(manifest['execution']['groups'][0]['api_error'], detail)
            self.assertEqual(manifest['runs'][0]['api_error'], detail)
            case = json.loads((base/'failure_cases.jsonl').read_text().splitlines()[0])
            self.assertEqual(case['api_error'], detail)
            self.assertNotIn('PRIVATE', json.dumps(manifest))

    def test_both_factories_use_policy_and_identity_blocks_old_cache(self):
        from dscg.pipelines.baseline import make_openai_compatible_pipeline
        from dscg.pipelines.defended import make_defended_pipeline, router_configuration_hash
        from experiments.common.benchmark_reuse import _compatible_binding
        config = self.config()
        def handler(request):
            value = json.loads(request.content)
            self.assertFalse(any(m['role']=='developer' for m in value['messages']))
            return httpx.Response(200, json=completion(), request=request)
        def raw_factory(**kwargs):
            raw = OpenAI(**kwargs, http_client=httpx.Client(transport=httpx.MockTransport(handler)))
            self.addCleanup(raw.close)
            return raw
        with patch('openai.OpenAI', side_effect=raw_factory):
            baseline, main = make_openai_compatible_pipeline(model_config=config)
            defended, main_defended, security = make_defended_pipeline(model_config=config, sec_model_config=config)
        for pipeline in (baseline, defended):
            self.assertEqual(pipeline.dscg_model_config['chat_request_adapter'], 'dashscope-system-v1')
        for tracker in (main, main_defended, security):
            tracker.chat.completions.create(model=config.model_id, messages=[{'role':'developer','content':'trusted'}])
        from dscg.benchmark_catalog import benchmark_identity
        old_public = {k:v for k,v in config.public_dict().items() if k != 'chat_request_adapter'}
        old = {'benchmark':benchmark_identity(), 'main_model': old_public}
        current = {'benchmark':benchmark_identity(), 'main_model': config.public_dict()}
        self.assertFalse(_compatible_binding(old, current))
        options = dict(input_isolation=True, authorization_precheck=True, l1_projection_mode='projected',
                       planning_tool_view=True, delegated_tasks=True)
        new_hash = router_configuration_hash(config, config, **options)
        with patch.object(ModelConfig, 'public_dict', return_value=old_public):
            self.assertNotEqual(router_configuration_hash(config, config, **options), new_hash)

    def test_unadapted_native_role_can_reproduce_mock_provider_rejection(self):
        from agentdojo.agent_pipeline.llms.openai_llm import OpenAILLM, _message_to_openai
        from agentdojo.functions_runtime import FunctionsRuntime
        captured = []
        def handler(request):
            value = json.loads(request.content); captured.append(value)
            if any(m['role']=='developer' for m in value['messages']):
                return httpx.Response(400, json={'error':{'code':'InvalidParameter','message':'unsupported role'}}, request=request)
            return httpx.Response(200, json=completion(), request=request)
        _, raw = self.client(handler)
        messages = [{'role':'system','content':[{'type':'text','content':'trusted'}]}]
        llm = OpenAILLM(raw, 'qwen3.7-flash', reasoning_effort='none')
        native_role = _message_to_openai(messages[0], 'qwen3.7-flash')['role']
        if native_role == 'developer':
            with self.assertRaises(BadRequestError):
                llm.query('fixture', FunctionsRuntime(), messages=messages)
        else:
            llm.query('fixture', FunctionsRuntime(), messages=messages)
        self.assertEqual(len(captured), 1)
        self.assertEqual(captured[0]['messages'][0]['role'], native_role)

    def test_dashboard_api_failure_does_not_persist_raw_sdk_text(self):
        import dashboard.app as dashboard
        from dscg.request_compatibility import attach_api_error
        artifacts = Path(__file__).resolve().parents[1]/'workshop/artifacts/20261019_agentdyn_qwen_roles'
        request = httpx.Request('POST', 'https://offline.invalid/v1/chat/completions')
        error = BadRequestError('PRIVATE_BODY', response=httpx.Response(400, request=request),
                                body={'code':'InvalidParameter','param':'messages[0].role','message':'PRIVATE_BODY'})
        attach_api_error(error, [{'role':'system','content':'PRIVATE_REQUEST'}])
        config = {'suites':['fixture'],'run_attack':False,'origin':False}
        with TemporaryDirectory(dir=artifacts) as tmp, \
                patch.object(dashboard, 'DASHBOARD_RESULTS_DIR', Path(tmp)), \
                patch.object(dashboard, 'validate_backend', return_value={'id':'fixture'}), \
                patch.object(dashboard, 'make_defended_pipeline', side_effect=error), \
                patch.object(dashboard, 'get_suite', return_value=SimpleNamespace(user_tasks={},injection_tasks={})), \
                patch.object(dashboard, 'push_log') as log, patch.object(dashboard, 'push_done') as done, \
                patch.object(dashboard.threading, 'Thread'):
            dashboard.run_test_thread('api_error_fixture', config)
            value = json.loads((Path(tmp)/'api_error_fixture/execution_error.json').read_text())
            self.assertEqual(value['api_error']['http_status'], 400)
            self.assertEqual(done.call_args.args[1]['api_error'], value['api_error'])
            self.assertNotIn('PRIVATE', str(log.call_args_list))
            self.assertNotIn('PRIVATE', json.dumps(value))

    def test_direct_goal_screen_failure_keeps_safe_diagnostics(self):
        from experiments import run_injection_precheck as screen
        from dscg.request_compatibility import attach_api_error
        artifacts = Path(__file__).resolve().parents[1]/'workshop/artifacts/20261019_agentdyn_qwen_roles'
        request = httpx.Request('POST', 'https://offline.invalid/v1/chat/completions')
        error = BadRequestError('PRIVATE', response=httpx.Response(400, request=request),
                                body={'code':'InvalidParameter','message':'PRIVATE'})
        detail = attach_api_error(error, [{'role':'system','content':'PRIVATE'}])
        with TemporaryDirectory(dir=artifacts) as tmp, patch.object(screen, 'make_openai_compatible_pipeline', side_effect=error):
            record = screen._native_attempt(Path(tmp), SimpleNamespace(name='fixture'), SimpleNamespace(ID='u0'),
                                            self.config(), {'source':{'agentdojo':'0.1.35'}})
            self.assertEqual(record['api_error'], detail)
            self.assertEqual(record['status'], 'error')
            self.assertIsNone(record['native_utility'])
            self.assertNotIn('PRIVATE', json.dumps(record))

    def test_dashboard_write_error_cannot_hide_terminal_api_failure(self):
        import dashboard.app as dashboard
        from dscg.request_compatibility import attach_api_error
        artifacts = Path(__file__).resolve().parents[1]/'workshop/artifacts/20261019_agentdyn_qwen_roles'
        request = httpx.Request('POST', 'https://offline.invalid/v1/chat/completions')
        error = BadRequestError('PRIVATE', response=httpx.Response(400, request=request), body={'code':'InvalidParameter'})
        attach_api_error(error, [{'role':'system','content':'PRIVATE'}])
        run_id = 'api_write_failure_fixture'
        dashboard.runs_store[run_id] = {'status':'running'}
        try:
            with TemporaryDirectory(dir=artifacts) as tmp, \
                    patch.object(dashboard, 'DASHBOARD_RESULTS_DIR', Path(tmp)), \
                    patch.object(dashboard, 'validate_backend', return_value={'id':'fixture'}), \
                    patch.object(dashboard, 'make_defended_pipeline', side_effect=error), \
                    patch.object(dashboard, 'get_suite', return_value=SimpleNamespace(user_tasks={},injection_tasks={})), \
                    patch.object(dashboard, 'push_log') as log, patch.object(dashboard, 'push_done') as done, \
                    patch.object(dashboard.threading, 'Thread'), \
                    patch.object(Path, 'write_text', side_effect=OSError('PRIVATE_DISK_DETAIL')):
                dashboard.run_test_thread(run_id, {'suites':['fixture'],'run_attack':False,'origin':False})
                self.assertEqual(dashboard.runs_store[run_id]['status'], 'error')
                self.assertEqual(done.call_args.args[1]['api_error']['http_status'], 400)
                self.assertNotIn('PRIVATE', str(log.call_args_list))
        finally:
            dashboard.runs_store.pop(run_id, None)

