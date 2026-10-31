"""Only public request settings and native references may enter diagnostics."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from dscg.task_diagnostics import DiagnosticSession, load_task_trace
from dscg.token_tracking import TokenTrackerClient
from dscg.pipelines import defended as d


class ModelRequestDiagnosticsTests(unittest.TestCase):
    def test_transport_retries_are_disabled_and_publicly_bound(self):
        from unittest.mock import patch
        from dscg.model_config import ModelConfig, create_openai_client
        config=ModelConfig('offline','PRIVATE KEY','https://offline.invalid','custom')
        with patch('openai.OpenAI') as constructor:
            create_openai_client(config)
        self.assertEqual(constructor.call_args.kwargs['max_retries'],0)
        self.assertEqual(config.public_dict()['sdk_max_retries'],0)
        self.assertNotIn('PRIVATE KEY',json.dumps(config.public_dict()))

    def logger(self, root):
        return SimpleNamespace(dirpath=root, context=dict(pipeline_name='engine',
            suite_name='banking', user_task_id='user_task_0', attack_type='none', injection_task_id=None))

    def test_sampling_is_actual_not_invented_and_prompts_headers_are_absent(self):
        client = Mock()
        client.chat.completions.create.return_value = SimpleNamespace(
            usage=SimpleNamespace(prompt_tokens=2, completion_tokens=1))
        tracker = TokenTrackerClient(client)
        with TemporaryDirectory() as tmp:
            logger = self.logger(tmp)
            with DiagnosticSession(logger, 'one', {}) as session:
                with tracker.phase('generation'):
                    tracker.chat.completions.create(model='offline',
                        messages=[{'role':'user','content':'PRIVATE PROMPT'}],
                        tools=[{'type':'function','function':{'name':'read_data'}}],
                        extra_headers={'Authorization':'SECRET KEY'})
                with tracker.phase('audit'):
                    tracker.chat.completions.create(model='offline', temperature=0.0,
                        top_p=0.9, messages=[], extra_body={'enable_thinking':False, 'secret':'PRIVATE BODY'})
                session.finish({})
            side = Path(tmp)/'engine/banking/user_task_0/none/none.dscg.jsonl'
            text = side.read_text()
            records = [row['record'] for row in map(json.loads, text.splitlines())
                       if row['event'] == 'model_request']
            self.assertEqual(len(records), 2)
            self.assertEqual(records[0]['sampling'], {})
            self.assertEqual(records[0]['tools_count'], 1)
            self.assertRegex(records[0]['tools_sha256'], r'^[0-9a-f]{64}$')
            self.assertEqual(records[1]['sampling'], {'temperature':0.0,'top_p':0.9})
            self.assertEqual(records[1]['enable_thinking'], False)
            for private in ('PRIVATE PROMPT','SECRET KEY','PRIVATE BODY','Authorization'):
                self.assertNotIn(private, text)
            trace = side.with_name('none.json')
            trace.write_text(json.dumps({**logger.context,'messages':[]}))
            restored = load_task_trace(trace)
            self.assertEqual(restored['dscg_model_requests'], records)

    def test_compact_audit_preserves_input_identity_without_body(self):
        record = dict(audit_input_sha256='a'*64, audit_model_view_version='legacy-v4.2',
                      decision='allow', prompt='PRIVATE', policy_features={'secret':'PRIVATE'})
        compact = d._compact_audit_record(record)
        self.assertEqual(compact['audit_input_sha256'], 'a'*64)
        self.assertEqual(compact['audit_model_view_version'], 'legacy-v4.2')
        self.assertNotIn('PRIVATE', json.dumps(compact))

    def test_audit_reference_records_positions_and_hashes_without_tool_text(self):
        from test_audit_tool_context import AuditToolContextTests, user, result
        fixture = AuditToolContextTests()
        fixture.setUp()
        history = [user('Summarize Bob\'s article'), result('PRIVATE TOOL BODY'),
                   {'role':'assistant','content':[], 'tool_calls':[fixture.call]}]
        with TemporaryDirectory() as tmp:
            logger = self.logger(tmp)
            with DiagnosticSession(logger, 'one', {}) as session:
                fixture.checker.query('Summarize Bob\'s article', fixture.runtime, None, history, {})
                session.finish({})
            side = Path(tmp)/'engine/banking/user_task_0/none/none.dscg.jsonl'
            text = side.read_text()
            request = next(row['record'] for row in map(json.loads,text.splitlines())
                           if row['event'] == 'audit_request')
            self.assertEqual(request['native_history_length'], len(history))
            self.assertEqual(request['call_ids'], ['fetch-1'])
            self.assertEqual(request['selected_returns'][0]['tool_call_id'], 'read-1')
            self.assertEqual(request['selected_returns'][0]['content_characters'], len('PRIVATE TOOL BODY'))
            response = json.loads(side.with_name('none.dscg.responses.jsonl').read_text())['record']
            self.assertEqual(response['audit_input_sha256'], request['audit_input_sha256'])
            self.assertNotIn('PRIVATE TOOL BODY', text)


if __name__ == '__main__':
    unittest.main()
