"""Bounded live collector tested exclusively with in-memory clients."""

from artifact_support import ensure_artifacts
ensure_artifacts('test_utility_collect')
import copy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from baseintent.model_config import ModelConfig
from experiments.diagnostics.utility_stages import build_stage, compare_stage
from experiments.diagnostics import utility_collect as c


def reply(text='{"decision":"allow","violations":[],"confidence":1,"reason_code":"FIXTURE"}'):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=text,refusal=None),
                                                    finish_reason='stop')],
                           usage=SimpleNamespace(total_tokens=20), model='offline-fixture')


class UtilityCollectorTests(unittest.TestCase):
    def config(self):
        return ModelConfig('qwen3.7-flash','not-a-real-key','https://example.invalid/v1','dashscope')

    def client(self):
        client=Mock();client.with_options.return_value=client
        client.chat.completions.create.return_value=reply()
        return client

    def test_explicit_budget_retries_disabled_and_request_template_preserved(self):
        bundle=build_stage('audit');original=copy.deepcopy(bundle)
        client=self.client();factory=Mock(return_value=client)
        with TemporaryDirectory(dir='artifacts/tests/test_utility_collect') as folder:
            result=c.collect_stage(bundle,self.config(),Path(folder)/'live',max_calls=4,client_factory=factory)
            self.assertEqual(result['collector']['attempted_calls'],4)
            self.assertEqual(client.chat.completions.create.call_count,4)
            client.with_options.assert_called_once_with(max_retries=0)
            calls=client.chat.completions.create.call_args_list
            self.assertEqual({r['profile'] for r in result['records']},set(bundle['profiles']))
            self.assertTrue(all(x.kwargs['model']=='qwen3.7-flash' and
                                x.kwargs['reasoning_effort']=='none' for x in calls))
            self.assertEqual(bundle,original)
            self.assertEqual(compare_stage(bundle,result)['status'],'incomplete')
            self.assertNotIn('not-a-real-key',(Path(folder)/'live/responses.json').read_text())
            client.close.assert_called_once()

    def test_invalid_or_existing_output_fails_before_clients(self):
        bundle=build_stage('audit');factory=Mock()
        with TemporaryDirectory(dir='artifacts/tests/test_utility_collect') as folder:
            for limit in (True,0,-1,97,1.5):
                with self.subTest(limit=limit), self.assertRaises(ValueError):
                    c.collect_stage(bundle,self.config(),Path(folder)/'new',max_calls=limit,client_factory=factory)
            with self.assertRaises(FileExistsError):
                c.collect_stage(bundle,self.config(),Path(folder),max_calls=4,client_factory=factory)
            factory.assert_not_called()

    def test_first_api_error_stops_and_saves_started_attempt(self):
        bundle=build_stage('audit');client=self.client()
        client.chat.completions.create.side_effect=RuntimeError('PRIVATE_SDK_KEY_AND_BODY')
        with TemporaryDirectory(dir='artifacts/tests/test_utility_collect') as folder:
            out=Path(folder)/'live'
            result=c.collect_stage(bundle,self.config(),out,max_calls=96,client_factory=Mock(return_value=client))
            self.assertEqual(client.chat.completions.create.call_count,1)
            self.assertEqual(result['collector']['status'],'stopped_api_error')
            self.assertEqual(result['records'][0]['error'],'MODEL_ERROR')
            self.assertNotIn('PRIVATE_SDK_KEY_AND_BODY',(out/'responses.json').read_text())
            journal=[json.loads(x) for x in (out/'attempts.jsonl').read_text().splitlines()]
            self.assertEqual(journal[0]['event'],'started')
            self.assertEqual(journal[-1]['event'],'failed')

    def test_schema_invalid_response_is_kept_without_retry(self):
        bundle=build_stage('audit');client=self.client()
        client.chat.completions.create.return_value=reply('not JSON')
        with TemporaryDirectory(dir='artifacts/tests/test_utility_collect') as folder:
            result=c.collect_stage(bundle,self.config(),Path(folder)/'live',max_calls=2,
                                   client_factory=Mock(return_value=client))
            self.assertEqual(len(result['records']),2)
            self.assertEqual(result['records'][0]['content'],'not JSON')
            self.assertEqual(client.chat.completions.create.call_count,2)

    def test_empty_choices_preserves_transport_failure_subclass(self):
        bundle=build_stage('audit');client=self.client()
        client.chat.completions.create.return_value=SimpleNamespace(choices=[],usage=None)
        with TemporaryDirectory(dir='artifacts/tests/test_utility_collect') as folder:
            result=c.collect_stage(bundle,self.config(),Path(folder)/'live',max_calls=2,
                                   client_factory=Mock(return_value=client))
            compared=compare_stage(bundle,result)
            self.assertEqual(compared['profiles']['legacy']['failure_counts'],{'NO_CHOICES':1})


if __name__=='__main__':unittest.main()
