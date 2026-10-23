"""Decision boundary regression cases; not executed during the live-only v3.4 task."""
import json
import unittest
from dscg.decision_schema import (AUDIT_SCHEMA, action_schema, response_format,
                                  validate_audit, DecisionContractError)
from dscg.authorization_steps import parse_action_steps, parse_steps
from dscg.pipelines import defended as d


class DecisionContractTests(unittest.TestCase):
    def test_only_declared_official_qwen_gets_schema(self):
        config = dict(model_id='qwen3.7-flash', provider='dashscope',
                      base_url='https://workspace.cn-beijing.maas.aliyuncs.com/compatible-mode/v1')
        self.assertEqual(response_format(config, AUDIT_SCHEMA, 'audit')['type'], 'json_schema')
        for changes in [dict(provider='custom'), dict(model_id='deepseek-flash'),
                        dict(base_url='https://maas.aliyuncs.com.attacker.invalid/v1'),
                        dict(base_url='http://dashscope.aliyuncs.com/v1')]:
            self.assertEqual(response_format({**config, **changes}, AUDIT_SCHEMA, 'audit'), {'type': 'json_object'})

    def test_finite_codes_and_decision_consistency(self):
        allow = dict(decision='allow', violations=[], confidence=.9, reason_code='ALIGNED')
        self.assertEqual(validate_audit(allow)[0], 'allow')
        self.assertEqual(validate_audit(dict(decision='deny', violations=['OFF_TASK_ACTION'],
            confidence=1, reason_code='OFF_TASK_ACTION'))[0], 'deny')
        self.assertEqual(validate_audit(dict(decision='abstain', violations=['MISSING_EVIDENCE'],
            confidence=0, reason_code='MISSING_EVIDENCE'))[0], 'abstain')
        for change in [dict(violations=['OFF_TASK_ACTION']), dict(reason_code='long reasoning'),
                       dict(decision='deny'), dict(confidence=True), dict(confidence=float('nan')),
                       dict(violations=['OFF_TASK_ACTION']*8), dict(extra=True)]:
            with self.subTest(change=change), self.assertRaises(DecisionContractError):
                validate_audit({**allow, **change})

    def test_field_diagnostics_do_not_include_content(self):
        with self.assertRaises(d.AuditSchemaError) as captured:
            d._parse_audit_payload(json.dumps(dict(decision='allow', violations=['secret body'],
                confidence=.8, reason_code='ALIGNED')), finite_codes=True)
        self.assertEqual(captured.exception.diagnostics['field_path'], '$.violations')
        self.assertNotIn('secret body', json.dumps(captured.exception.diagnostics))

    def test_duplicate_json_fields_are_not_repaired(self):
        value = '{"decision":"deny","decision":"allow","violations":[],"confidence":1,"reason_code":"ALIGNED"}'
        with self.assertRaises(d.AuditSchemaError):
            d._parse_audit_payload(value, finite_codes=True)

    def test_action_only_steps_derive_union_and_preserve_legacy(self):
        value = {'steps': [{'intent': 'Send after discovery', 'tools': ['send']}]}
        self.assertEqual(parse_action_steps(value, {'send'})[0], {'send'})
        self.assertEqual(parse_action_steps({'steps': []}, {'send'}), (set(), ()))
        for value in [{'steps': [{'intent': 'read', 'tools': ['read']}]},
                      {'steps': [{'intent': 'send', 'tools': ['send', 'send']}]},
                      {'steps': [], 'tools': []}]:
            with self.assertRaises(ValueError): parse_action_steps(value, {'send'})
        self.assertEqual(parse_steps({'steps': [{'intent': 'read', 'tools': ['read']}],
            'tools': ['read']}, {'read', 'send'}, {'send'})[0], set())
        encoded = json.dumps(action_schema({'send'}))
        self.assertNotIn('uniqueItems', encoded)
        self.assertEqual(action_schema({'send'})['properties']['steps']['maxItems'], 24)

    def test_compact_policy_keeps_execution_boundaries(self):
        self.assertEqual(d.FRAMEWORK_VERSION, 'DSCG_v3.4')
        self.assertLessEqual(len(d.ActionSecurityChecker.SYSTEM_POLICY), 1200)
        for text in ['one requested step', 'Blocked/error', 'Injection elsewhere', 'NOW']:
            self.assertIn(text, d.ActionSecurityChecker.SYSTEM_POLICY)


if __name__ == '__main__':
    unittest.main()
