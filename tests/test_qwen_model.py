"""Qwen defaults and credential-safe configuration, without network calls."""
import unittest
from unittest.mock import Mock, patch
from dscg.model_config import resolve_model_config, reasoning_effort_for_config, ModelConfigurationError


class QwenModelTests(unittest.TestCase):
    def test_native_and_defended_factories_send_the_same_explicit_reasoning_setting(self):
        from agentdojo.functions_runtime import FunctionsRuntime
        from openai.types.chat import ChatCompletionMessage
        from types import SimpleNamespace
        from dscg.pipelines import baseline, defended
        config = resolve_model_config('qwen3.7-flash', api_key='fixture-key', local_settings={}, env={})
        client = Mock()
        client.chat.completions.create.return_value = SimpleNamespace(
            choices=[SimpleNamespace(message=ChatCompletionMessage(role='assistant', content='done'))], usage=None)
        with patch.object(baseline, 'create_openai_client', return_value=client):
            pipe, tracker = baseline.make_openai_compatible_pipeline(model_config=config)
            pipe.query('hello', FunctionsRuntime([]))
        self.assertEqual(client.chat.completions.create.call_args.kwargs['reasoning_effort'], 'none')
        with patch.object(defended, 'create_openai_client', return_value=client):
            pipe, _, _ = defended.make_defended_pipeline(model_config=config, sec_model_config=config)
        self.assertEqual(pipe.task_executor.llm.reasoning_effort, 'none')
        self.assertEqual(pipe.task_executor.authorization_compiler.llm.reasoning_effort, 'none')
        loop = pipe.elements[-1]
        checker = next(v for v in loop.elements if isinstance(v, defended.ActionSecurityChecker))
        self.assertEqual(checker.small_llm.reasoning_effort, 'none')

    def test_default_main_and_secondary_share_qwen_workspace_and_key(self):
        settings = {'providers': {'dashscope': {'api_key': 'offline-qwen-key',
            'base_url': 'https://workspace.cn-beijing.maas.aliyuncs.com/compatible-mode/v1'}}}
        main = resolve_model_config(local_settings=settings, env={}, api_key='offline-qwen-key')
        audit = resolve_model_config(prefix='DSCG_SEC', local_settings=settings, env={}, fallback=main)
        self.assertEqual(main.model_id, 'qwen3.7-flash')
        self.assertEqual(audit, main)
        self.assertIn('workspace.cn-beijing', main.base_url)
        self.assertEqual(main.api_key, 'offline-qwen-key')

    def test_qwen_thinking_is_explicitly_off_and_bound_in_public_config(self):
        model = resolve_model_config('qwen3.7-flash', local_settings={}, env={}, api_key='offline-key')
        self.assertEqual(reasoning_effort_for_config(model), 'none')
        self.assertEqual(model.public_dict()['reasoning_effort'], 'none')
        self.assertNotIn('offline-key', str(model.public_dict()))

    def test_credentials_in_api_key_env_are_rejected_without_echo(self):
        secret = 'sk-offline-secret-must-not-appear'
        with self.assertRaises(ModelConfigurationError) as error:
            resolve_model_config('qwen3.7-flash', local_settings={'providers': {'dashscope': {
                'api_key_env': secret}}}, env={})
        self.assertIn('environment variable name', str(error.exception))
        self.assertNotIn(secret, str(error.exception))

    def test_explicit_deepseek_configuration_still_works(self):
        config = resolve_model_config('deepseek-flash', provider='deepseek',
                                      local_settings={'providers': {'deepseek': {'api_key': 'offline-ds'}}}, env={})
        self.assertEqual(config.api_key, 'offline-ds')
        self.assertEqual(config.base_url, 'https://api.deepseek.com')
        self.assertEqual(reasoning_effort_for_config(config), 'none')
