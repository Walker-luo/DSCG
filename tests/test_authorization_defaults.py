"""Authorization compiler protocol and diagnostics, without model calls."""
import json
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from agentdojo.functions_runtime import FunctionsRuntime, EmptyEnv
from dscg.pipelines.defended import (
    ToolAuthorizationCompiler, TrustedTaskRequest, OurFrameExecutor,
    PermissionSandbox, _compact_authorization_record,
)


def runtime(reverse=False):
    tools = FunctionsRuntime()

    def update_payment() -> str:
        """Change an existing scheduled payment."""
        return "updated"

    def send_money() -> str:
        """Create a new payment."""
        return "sent"

    for function in ([update_payment, send_money] if reverse else [send_money, update_payment]):
        tools.register_function(function)
    return tools


def model(content='{"tools":["update_payment"]}', finish="stop", refusal=None):
    client = Mock()
    client.chat.completions.create.return_value = SimpleNamespace(choices=[
        SimpleNamespace(message=SimpleNamespace(content=content, refusal=refusal), finish_reason=finish)
    ])
    return SimpleNamespace(name="offline", client=client, query=Mock(
        side_effect=lambda q, r, e, m, a: (q, r, e, [*m, {"role": "assistant", "content": [], "tool_calls": []}], a)
    ))


class AuthorizationDefaultsTests(unittest.TestCase):
    def test_registration_order_has_identical_request_and_contract(self):
        requests, contracts = [], []
        for reverse in (False, True):
            llm = model()
            contract = ToolAuthorizationCompiler(llm).compile(
                TrustedTaskRequest("Read my payments and adjust the existing rent if needed."), runtime(reverse))
            request = llm.client.chat.completions.create.call_args.kwargs
            self.assertEqual(request.get("temperature"), 0.0)
            self.assertEqual(list(json.loads(request["messages"][1]["content"])["available_tools"]),
                             ["send_money", "update_payment"])
            self.assertEqual(contract.allowed_tools, frozenset({"update_payment"}))
            requests.append(request)
            contracts.append(contract.public_dict())
        self.assertEqual(requests[0], requests[1])
        self.assertEqual(contracts[0], contracts[1])

    def test_failures_are_coded_and_remain_fail_closed_in_compact_trace(self):
        cases = [
            (model(content="bad JSON"), "AUTH_INVALID_JSON"),
            (model(content=None), "AUTH_INVALID_JSON"),
            (model(content="{}"), "AUTH_INVALID_SCHEMA"),
            (model(content='{"tools":["ghost"]}'), "AUTH_UNKNOWN_TOOL"),
            (model(refusal="refused"), "AUTH_REFUSED"),
            (model(finish="length"), "AUTH_INCOMPLETE"),
        ]
        empty = model()
        empty.client.chat.completions.create.return_value = SimpleNamespace(choices=[])
        cases.append((empty, "AUTH_NO_CHOICE"))
        timed_out = model()
        timed_out.client.chat.completions.create.side_effect = TimeoutError("private provider details")
        cases.append((timed_out, "AUTH_API_ERROR"))
        for llm, code in cases:
            with self.subTest(code=code):
                sandbox = PermissionSandbox(["send_money"])
                extra = {}
                OurFrameExecutor(llm, sandbox=sandbox).query("adjust payment", runtime(), EmptyEnv(),
                    [{"role": "user", "content": [{"type": "text", "content": "adjust payment"}]}], extra)
                record = _compact_authorization_record(extra["dscg_authorization"])
                self.assertEqual(record.get("error_code"), code)
                self.assertEqual(record["policy_state"], "error")
                self.assertFalse(sandbox.assess("send_money", runtime())[0])
                self.assertNotIn("private provider details", json.dumps(record))

    def test_empty_request_has_error_code_without_api_call(self):
        llm = model()
        with self.assertRaises(ValueError) as caught:
            ToolAuthorizationCompiler(llm).compile(TrustedTaskRequest(" "), runtime())
        self.assertEqual(getattr(caught.exception, "reason_code", None), "AUTH_EMPTY_REQUEST")
        llm.client.chat.completions.create.assert_not_called()
