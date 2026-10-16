"""Auditors receive bounded task evidence, not an unauthenticated grant."""
from copy import deepcopy
import json
from types import SimpleNamespace
import unittest
import yaml

from agentdojo.functions_runtime import FunctionCall, FunctionsRuntime
from dscg.pipelines.defended import ActionSecurityChecker


def user(text):
    return {'role': 'user', 'content': [{'type': 'text', 'content': text}]}


def result(name, args, text, ident='read', error=None):
    return {'role': 'tool', 'tool_call_id': ident,
            'tool_call': FunctionCall(function=name, args=args, id=ident),
            'content': [{'type': 'text', 'content': text}], 'error': error}


class AuditEvidenceTests(unittest.TestCase):
    def packet(self, query, messages, name='send_email', args=None):
        checker = ActionSecurityChecker(SimpleNamespace(name='offline'))
        call = FunctionCall(function=name, args=args or {}, id='candidate')
        return checker._audit_packet(query, FunctionsRuntime(), [call], {}, messages)

    def test_empty_return_retains_its_channel_argument_without_mutating_history(self):
        messages = [user('Add a user to the quietest channel'),
                    result('read_channel_messages', {'channel': 'announcements'}, '[]')]
        before = deepcopy(messages)
        packet = self.packet('Add a user to the quietest channel', messages,
                             'add_user_to_channel', {'channel': 'announcements', 'user': 'Kim'})
        evidence = packet['recent_tool_results'][0]
        self.assertEqual(evidence.get('call_arguments'), {'channel': 'announcements'})
        self.assertEqual(evidence['content'], '[]')
        self.assertEqual(evidence['trust'], 'untrusted')
        self.assertEqual(messages, before)

    def test_matching_older_document_survives_recency_but_previous_task_does_not(self):
        query = 'Email a summary of minutes.docx to the client'
        messages = [user('Old task'), result('get_file_by_id', {'file_id': 'old'},
                    'old-client@example.test minutes.docx'), user(query),
                    result('search_files_by_filename', {'filename': 'minutes.docx'},
                           'Client contact: new-client@example.test. Next meeting: September 4.', 'doc')]
        messages += [result('lookup', {}, 'unrelated ' + str(i), str(i)) for i in range(12)]
        packet = self.packet(query, messages, args={'recipients': ['new-client@example.test']})
        contents = '\n'.join(r['content'] for r in packet['recent_tool_results'])
        self.assertIn('Next meeting: September 4.', contents)
        self.assertNotIn('old-client@example.test', json.dumps(packet))
        self.assertTrue(packet['tool_results_window_truncated'])

    def test_file_comparison_keeps_every_record_and_its_tail_metadata(self):
        query = 'Find and delete the largest file in my drive'
        rows = [{'content': 'ordinary document ' * 180, 'id_': str(i),
                 'filename': f'document-{i}.txt', 'size': 9000 if i == 25 else i + 1,
                 'owner': 'owner@example.test', 'shared_with': {},
                 'last_modified': '2025-03-01 12:00:00'} for i in range(26)]
        packet = self.packet(query, [user(query), result('list_files', {}, yaml.safe_dump(rows))],
                             'delete_file', {'file_id': '25'})
        evidence = packet['recent_tool_results'][0]
        self.assertEqual(evidence.get('representation'), 'file_metadata')
        visible = json.loads(evidence['content'])
        self.assertEqual(len(visible), 26)
        self.assertEqual([r['size'] for r in visible], list(range(1, 26)) + [9000])
        self.assertEqual(visible[-1]['id_'], '25')
        self.assertFalse(evidence['content_truncated'])
        self.assertEqual(evidence.get('omitted_fields'), ['content'])

    def test_document_summary_preserves_body_and_invalid_lists_are_not_compacted(self):
        text = yaml.safe_dump([{'id_': '7', 'filename': 'minutes.docx', 'size': 50,
                              'content': 'The next meeting is September 4.'}])
        packet = self.packet('Summarize minutes.docx', [user('Summarize minutes.docx'),
                             result('list_files', {}, text)])
        self.assertIn('September 4', packet['recent_tool_results'][0]['content'])
        bad = '- id_: "7"\n  id_: "8"\n  filename: x\n  size: 1\n  content: a\n'
        packet = self.packet('Delete the largest file', [user('Delete the largest file'),
                             result('list_files', {}, bad)], 'delete_file', {'file_id': '8'})
        self.assertEqual(packet['recent_tool_results'][0].get('representation'), 'raw')
        self.assertIn('id_', packet['recent_tool_results'][0]['content'])

    def test_budget_and_loss_flags_cover_content_and_call_arguments(self):
        query = 'Read the records'
        messages = [user(query)] + [result('read_records', {'path': str(i)}, 'x' * 12000, str(i))
                                   for i in range(12)]
        packet = self.packet(query, messages, 'read_records')
        self.assertLessEqual(sum(len(r['content']) for r in packet['recent_tool_results']), 8192)
        self.assertTrue(packet['tool_results_window_truncated'])
        self.assertTrue(any(r['content_truncated'] for r in packet['recent_tool_results']))
        messages = [user(query), result('read_records', {'path': 'x' * 6000}, '[]')]
        packet = self.packet(query, messages, 'read_records')
        self.assertTrue(packet['recent_tool_results'][0].get('call_arguments_truncated'))
        self.assertLessEqual(len(json.dumps(packet['recent_tool_results'][0]['call_arguments'])), 1024)

    def test_deeply_nested_structured_result_falls_back_instead_of_crashing(self):
        query = 'Delete the largest file'
        text = '[' * 1100 + '0' + ']' * 1100
        packet = self.packet(query, [user(query), result('list_files', {}, text)],
                             'delete_file', {'file_id': '1'})
        self.assertEqual(packet['recent_tool_results'][0]['representation'], 'raw')
        self.assertEqual(packet['recent_tool_results'][0]['content'], text)

    def test_size_comparison_does_not_remove_body_required_for_a_summary(self):
        query = 'Summarize the largest file in my drive and email it to Alice'
        row = dict(id_='7', filename='minutes.docx', size=100, owner='owner@example.test',
                   shared_with={}, last_modified='2025-03-01', content='The meeting is on September 4.')
        packet = self.packet(query, [user(query), result('get_file_by_id', {'file_id': '7'},
                             yaml.safe_dump(row))], args={'recipients': ['alice@example.test']})
        self.assertIn('The meeting is on September 4.', packet['recent_tool_results'][0]['content'])
        self.assertEqual(packet['recent_tool_results'][0]['representation'], 'raw')

    def test_latest_conflicting_lookup_is_not_outvoted_by_older_candidate_matches(self):
        query = 'Send the invoice to the current billing contact'
        messages = [user(query)] + [result('lookup_contact', {'account': 'billing'},
                    'Contact is alice@example.test', str(i)) for i in range(8)]
        messages.append(result('lookup_contact', {'account': 'billing'},
                               'Contact is now bob@example.test', 'latest'))
        packet = self.packet(query, messages, args={'recipients': ['alice@example.test']})
        self.assertIn('Contact is now bob@example.test', '\n'.join(r['content'] for r in packet['recent_tool_results']))

    def test_recent_correction_survives_following_unrelated_diagnostics(self):
        query = 'Send the invoice to the current billing contact'
        messages = [user(query)] + [result('lookup_contact', {'account': 'billing'},
                    'Contact is alice@example.test', str(i)) for i in range(8)]
        messages += [result('lookup_contact', {'account': 'billing'}, 'Contact is now bob@example.test', 'updated'),
                     result('diagnostic', {}, 'connection ready', 'connection'),
                     result('diagnostic', {}, 'logging ready', 'logging')]
        packet = self.packet(query, messages, args={'recipients': ['alice@example.test']})
        self.assertIn('Contact is now bob@example.test', '\n'.join(r['content'] for r in packet['recent_tool_results']))

    def test_original_structure_controls_historical_argument_loss_flags(self):
        query = 'Read the records'
        for arguments, flag in (({'a': {'b': {'c': {'id': 1}}}}, 'call_arguments_truncated'),
                                ({'number': float('nan')}, 'call_arguments_nonfinite_or_unsupported')):
            packet = self.packet(query, [user(query), result('read_records', arguments, '[]')], 'read_records')
            self.assertTrue(packet['recent_tool_results'][0].get(flag), arguments)

    def test_json_escaping_cannot_exceed_per_record_or_combined_budget(self):
        query = 'Read the records'
        messages = [user(query)] + [result('read_records', {'path': '\\' * 6000}, 'data', str(i)) for i in range(8)]
        packet = self.packet(query, messages, 'read_records')
        facts = packet['recent_tool_results']
        self.assertTrue(all(len(json.dumps(r['call_arguments'], ensure_ascii=False)) <= 1024 for r in facts))
        self.assertLessEqual(sum(len(r['content']) + len(json.dumps(r['call_arguments'], ensure_ascii=False)) for r in facts), 8192)

    def test_errors_share_the_fact_budget_instead_of_adding_an_unbounded_allowance(self):
        query = 'Read the records'
        messages = [user(query)] + [result('read_records', {'path': 'x' * 800}, '', str(i), error='e' * 2000)
                                   for i in range(8)]
        packet = self.packet(query, messages, 'read_records')
        facts = packet['recent_tool_results']
        self.assertLessEqual(sum(len(r['content']) + len(json.dumps(r['call_arguments'], ensure_ascii=False)) + len(r['error'] or '')
                                 for r in facts), 8192)

    def test_outbound_action_keeps_file_body_even_if_task_does_not_say_summary(self):
        query = 'Find the largest file and send its explanation to Alice'
        row = dict(id_='9', filename='report.txt', size=100, owner='owner@example.test',
                   shared_with={}, last_modified='2025-03-01', content='The system was unavailable for two hours.')
        packet = self.packet(query, [user(query), result('get_file_by_id', {'file_id': '9'},
                             yaml.safe_dump(row))], args={'recipients': ['alice@example.test']})
        self.assertIn('unavailable for two hours', packet['recent_tool_results'][0]['content'])


if __name__ == '__main__':
    unittest.main()
