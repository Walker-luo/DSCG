import json
import unittest
from types import SimpleNamespace
from unittest.mock import Mock
from test_step_authorization import runtime
from dscg.pipelines import defended as d


class CompletePermissionTests(unittest.TestCase):
    def compile(self, permissions):
        client = Mock()
        client.chat.completions.create.return_value = SimpleNamespace(choices=[SimpleNamespace(
            message=SimpleNamespace(content=json.dumps({'tool_permissions':permissions}), refusal=None), finish_reason='stop')])
        compiler = d.ToolAuthorizationCompiler(SimpleNamespace(name='offline', client=client))
        return compiler.compile(d.TrustedTaskRequest('Find a channel and send a reply there.'),runtime()), client

    def test_complete_action_decisions_merge_reads_in_one_call(self):
        grant, client = self.compile({'send_channel_message':True})
        self.assertEqual(grant.allowed_tools, {'discover','send_channel_message'})
        self.assertEqual(grant.public_dict()['tool_permissions'], {'send_channel_message':True})
        self.assertEqual(client.chat.completions.create.call_count, 1)
        packet = json.loads(client.chat.completions.create.call_args.kwargs['messages'][1]['content'])
        self.assertEqual(set(packet['action_tools']), {'send_channel_message'})
        self.assertEqual(set(packet['automatic_read_tools']), {'discover'})

    def test_omitted_unknown_and_nonboolean_decisions_fail_closed(self):
        for permissions in [{}, {'send_channel_message':True,'unknown':True}, {'send_channel_message':1}]:
            with self.subTest(permissions=permissions), self.assertRaises(d.AuthorizationCompilationError):
                self.compile(permissions)

    def test_false_action_decision_preserves_reads_without_granting_action(self):
        grant, _ = self.compile({'send_channel_message':False})
        self.assertEqual(grant.allowed_tools, {'discover'})


class PermissionDiagnosticTests(unittest.TestCase):
    """Permission failures stay fail-closed but explain their shape without values."""

    def test_shape_counts_are_bounded_and_exclude_keys_and_values(self):
        from dscg.intent_evidence import PermissionContractError, parse_permissions
        cases = [
            ({'tool_permissions': {'create_file': True}}, {'send_email', 'create_file'}, 'missing_keys', 1),
            ({'tool_permissions': {'send_email': True, 'unknown_tool': False}}, {'send_email'}, 'extra_keys', 1),
            ({'tool_permissions': {'send_email': 'true'}}, {'send_email'}, 'non_bool_values', 1),
        ]
        for payload, names, field, expected in cases:
            with self.subTest(field=field):
                with self.assertRaises(PermissionContractError) as caught:
                    parse_permissions(payload, names)
                diagnostics = caught.exception.diagnostics
                self.assertEqual(diagnostics['failure_type'], 'AUTH_INVALID_TOOL_PERMISSIONS')
                self.assertEqual(diagnostics[field], expected)
                self.assertEqual(caught.exception.reason_code, 'AUTH_INVALID_TOOL_PERMISSIONS')
                rendered = json.dumps(diagnostics)
                self.assertNotIn('unknown_tool', rendered)
                self.assertNotIn('true', rendered)

    def test_valid_table_still_returns_true_keys(self):
        from dscg.intent_evidence import parse_permissions
        selected, frozen = parse_permissions(
            {'tool_permissions': {'send_email': True, 'create_file': False}}, {'send_email', 'create_file'})
        self.assertEqual(selected, {'send_email'})
        self.assertEqual(frozen, (('create_file', False), ('send_email', True)))
