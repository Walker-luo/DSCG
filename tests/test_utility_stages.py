"""Offline stage export and comparison; fixtures are not efficacy labels."""
import copy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from experiments.diagnostics import utility_stages as u


def responses(bundle):
    cases = {r['id']: r for r in bundle['cases']}
    rows = []
    for request in bundle['requests']:
        case = cases[request['case_id']]
        payload = ({'tools': case['required_tools']} if bundle['stage'] == 'authorization' else
                   dict(decision=case['expected'], violations=[], confidence=.9, reason_code='FIXTURE'))
        rows.append(dict(request_id=request['id'], request_sha256=request['request_sha256'],
                         content=json.dumps(payload), finish_reason='stop', refusal_present=False,
                         total_tokens=10))
    return dict(schema_version=u.RESPONSE_SCHEMA, bundle_sha256=bundle['bundle_sha256'],
                model_config={'model_id': 'offline-fixture', 'provider': 'fixture'}, records=rows)


class UtilityStageTests(unittest.TestCase):
    def test_export_counts_fixed_inputs_and_no_clients(self):
        with patch('dscg.pipelines.defended.create_openai_client', side_effect=AssertionError('no clients')):
            audit = u.build_stage('audit')
            auth = u.build_stage('authorization')
            source = u.build_stage('source')
        self.assertEqual((len(audit['cases']), len(audit['requests'])), (24, 96))
        self.assertEqual((len(auth['cases']), len(auth['requests'])), (12, 48))
        self.assertEqual(len(source['requests']), 96)
        bank = [c for c in audit['cases'] if c['suite'] == 'banking']
        self.assertEqual([sum(c['expected'] == label for c in bank) for label in ('allow','deny','abstain')], [6,4,2])
        self.assertEqual(sum(bool(c['required_tools']) for c in auth['cases']), 6)
        self.assertEqual(audit['model_calls'], 0)
        self.assertEqual(audit, u.build_stage('audit'))
        payloads = {}
        for r in audit['requests']:
            payload = json.loads(r['request']['messages'][1]['content'])
            self.assertNotIn('expected', payload)
            if r['case_id'] in payloads:
                self.assertEqual(payloads[r['case_id']], payload)
            payloads[r['case_id']] = payload

    def test_empty_and_partial_responses_are_not_measured_not_passed(self):
        b = u.build_stage('audit')
        r = responses(b); r['records'] = []
        result = u.compare_stage(b, r)
        self.assertEqual(result['status'], 'not_measured')
        self.assertFalse(result['diagnostic_gate_passed'])
        self.assertEqual(result['missing_responses'], 96)
        r = responses(b); r['records'].pop()
        result = u.compare_stage(b, r)
        self.assertEqual(result['status'], 'incomplete')
        self.assertIsNone(result['total_tokens'])
        self.assertFalse(result['diagnostic_gate_passed'])

    def test_protocol_error_reduction_is_not_automatic_promotion(self):
        b = u.build_stage('audit'); r = responses(b)
        r['records'][0]['content'] = '{"decision":"allow","violations":[],"confidence":1,"reason_code":"bad code"}'
        result = u.compare_stage(b, r)
        self.assertTrue(result['diagnostic_gate_passed'])
        self.assertEqual(result['profiles']['legacy']['failure_counts'], {'INVALID_REASON_CODE': 1})
        self.assertIsNone(result['selected_default'])
        # Equal counts can hide a newly unsafe pair; compare individual case/repetition keys.
        for profile in ('legacy', 'protocol-v1'):
            chosen = next(row for row in b['requests'] if row['profile'] == profile and
                          next(c for c in b['cases'] if c['id'] == row['case_id'])['expected'] == 'deny')
            if profile == 'protocol-v1':
                chosen = next(row for row in b['requests'] if row['profile'] == profile and
                              row['case_id'] != chosen['case_id'] and
                              next(c for c in b['cases'] if c['id'] == row['case_id'])['expected'] == 'deny')
            out = next(row for row in r['records'] if row['request_id'] == chosen['id'])
            out['content'] = '{"decision":"allow","violations":[],"confidence":1,"reason_code":"FIXTURE"}'
        result = u.compare_stage(b, r)
        self.assertGreater(result['new_unsafe_pairs'], 0)
        self.assertFalse(result['diagnostic_gate_passed'])

    def test_strict_response_identity_transport_and_unknown_cost(self):
        b = u.build_stage('audit'); r = responses(b)
        for mutate in (lambda x: x.update(bundle_sha256='wrong'),
                       lambda x: x['records'].append(copy.deepcopy(x['records'][0])),
                       lambda x: x['records'][0].update(request_sha256='wrong'),
                       lambda x: x['model_config'].update(api_key='private')):
            changed = copy.deepcopy(r); mutate(changed)
            with self.assertRaises(ValueError): u.compare_stage(b, changed)
        r['records'][0].update(finish_reason='length', total_tokens=None)
        result = u.compare_stage(b, r)
        self.assertEqual(result['profiles']['legacy']['failure_counts'], {'INCOMPLETE_RESPONSE': 1})
        self.assertIsNone(result['total_tokens'])
        self.assertEqual(result['known_total_tokens'], 950)
        self.assertNotIn('content', result['trials'][0])

    def test_authorization_is_replayed_through_real_strict_compiler(self):
        b = u.build_stage('authorization'); r = responses(b)
        control = b['profiles'][0]
        request = next(row for row in b['requests'] if row['profile'] == control and
                       next(c for c in b['cases'] if c['id'] == row['case_id'])['required_tools'])
        next(row for row in r['records'] if row['request_id'] == request['id'])['content'] = '{"tools":[]}'
        result = u.compare_stage(b, r)
        self.assertTrue(result['diagnostic_gate_passed'])
        self.assertEqual(result['profiles'][control]['missing_required_trials'], 1)
        negative = next(row for row in b['requests'] if row['profile'] == 'tool-semantics-v1' and
                        not next(c for c in b['cases'] if c['id'] == row['case_id'])['required_tools'])
        next(row for row in r['records'] if row['request_id'] == negative['id'])['content'] = '{"tools":["send_channel_message"]}'
        self.assertFalse(u.compare_stage(b, r)['diagnostic_gate_passed'])
        r['records'][0]['content'] = '{"tools":["not_registered"]}'
        self.assertIn('AUTH_UNKNOWN_TOOL', u.compare_stage(b, r)['profiles'][control]['failure_counts'])

    def test_modified_labels_cannot_be_rebound_as_the_fixed_diagnostic_set(self):
        b = u.build_stage('audit')
        b['cases'][0]['expected'] = 'deny'
        b['bundle_sha256'] = u.digest({k:v for k,v in b.items() if k != 'bundle_sha256'})
        with self.assertRaises(ValueError): u.compare_stage(b)

    def test_transport_errors_and_profile_costs_are_separate(self):
        b = u.build_stage('audit'); r = responses(b)
        r['records'][0].update(error='TIMEOUT', content=None, total_tokens=None)
        result = u.compare_stage(b, r)
        self.assertEqual(result['profiles']['legacy']['execution_errors'], 1)
        self.assertEqual(result['profiles']['legacy']['protocol_failures'], 0)
        self.assertEqual(result['profiles']['protocol-v1']['total_tokens'], 480)
        self.assertIsNone(result['profiles']['legacy']['total_tokens'])
        self.assertFalse(result['diagnostic_gate_passed'])

    def test_moving_parse_failure_to_positive_case_is_not_target_improvement(self):
        for stage in ('authorization','source'):
            b = u.build_stage(stage); r = responses(b)
            control, candidate = b['profiles']
            positive = next(c for c in b['cases'] if bool(c.get('required_tools'))
                            or c.get('expected') == 'allow')
            negative = next(c for c in b['cases'] if not bool(c.get('required_tools'))
                            and c.get('expected') != 'allow')
            for profile,case,content in (
                (control,positive,'{"tools":[]}' if stage == 'authorization' else
                 '{"decision":"deny","violations":["OFF_TASK"],"confidence":1,"reason_code":"FIXTURE"}'),
                (control,negative,'not JSON'), (candidate,positive,'not JSON')):
                request = next(q for q in b['requests'] if q['profile']==profile and
                               q['case_id']==case['id'] and q['repetition']==1)
                next(q for q in r['records'] if q['request_id']==request['id'])['content'] = content
            result = u.compare_stage(b,r)
            with self.subTest(stage=stage):
                self.assertFalse(result['diagnostic_gate_passed'])
                self.assertFalse(result['target_comparison_complete'])
                failed = next(q for q in result['trials'] if q['profile']==candidate and q['failure_type'])
                self.assertIsNone(failed['unsafe'])

    def test_trace_signals_overlap_without_claiming_causality(self):
        trace = {'utility': False, 'security': False, 'messages': [{'role':'assistant','tool_calls':[]}],
                 'dscg_audit_summary': {'reason_code_counts': {'AUDIT_SCHEMA_INVALID': 2}},
                 'dscg_action_ledger': [{'state':'blocked','transitions':[{'reason_code':'AUDIT_DENY'}]}]}
        row = u.trace_signals(trace)
        self.assertTrue(row['protocol_failure_seen'])
        self.assertTrue(row['audit_deny_seen'])
        self.assertTrue(row['no_proposed_calls'])
        self.assertEqual(row['attribution'], 'overlapping_observations_not_causal_labels')
        self.assertEqual(u.trace_signals({'error':'failed'})['status'], 'error_or_incomplete')
        compact = {k:v for k,v in trace.items() if k != 'dscg_action_ledger'}
        compact['dscg_action_summary'] = {'reason_code_counts':{'AUDIT_DENY':1}}
        self.assertTrue(u.trace_signals(compact)['audit_deny_seen'])

    def test_export_cli_refuses_overwrite_and_report_never_sends_requests(self):
        root = Path('workshop/artifacts').resolve()
        with TemporaryDirectory(dir=root) as directory:
            output = Path(directory)/'bundle.json'
            self.assertEqual(u.main(['export','--stage','audit','--output',str(output)]),0)
            with self.assertRaises(FileExistsError): u.main(['export','--stage','audit','--output',str(output)])
            report = Path(directory)/'report'
            self.assertEqual(u.main(['compare','--bundle',str(output),'--output-dir',str(report)]),0)
            data = json.loads((report/'comparison.json').read_text())
            self.assertEqual(data['status'], 'not_measured')
            with self.assertRaises(FileExistsError): u.main(['compare','--bundle',str(output),'--output-dir',str(report)])


if __name__ == '__main__':
    unittest.main()
