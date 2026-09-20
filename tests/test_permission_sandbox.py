from types import SimpleNamespace
import unittest

from agentdojo.functions_runtime import FunctionCall

from dscg.pipelines.defended import (
    OurFrameExecutor,
    PermissionSandbox,
    SandboxPolicyState,
)


class PermissionSandboxTests(unittest.TestCase):
    def _runtime(self, *names):
        return SimpleNamespace(functions={name: SimpleNamespace(name=name) for name in names})

    def _assistant_message(self, *calls):
        return {
            "role": "assistant",
            "content": [],
            "tool_calls": [FunctionCall(function=name, args={}) for name in calls],
        }

    def _tool_calls(self, message):
        return message["tool_calls"] if isinstance(message, dict) else message.tool_calls

    def test_none_and_empty_allowlist_are_distinct_and_fail_closed(self):
        runtime = self._runtime("read_profile")

        uninitialized = PermissionSandbox()
        self.assertEqual(uninitialized.policy_state, SandboxPolicyState.UNINITIALIZED)
        result = uninitialized.query(
            "request", runtime, None, [self._assistant_message("read_profile")], {}
        )
        self.assertEqual(self._tool_calls(result[3][-1]), [])

        initialized_empty = PermissionSandbox([])
        self.assertEqual(initialized_empty.policy_state, SandboxPolicyState.INITIALIZED_EMPTY)
        result = initialized_empty.query(
            "request", runtime, None, [self._assistant_message("read_profile")], {}
        )
        self.assertEqual(self._tool_calls(result[3][-1]), [])

    def test_unknown_tool_is_blocked_even_when_allowlisted(self):
        sandbox = PermissionSandbox(["ghost_tool"])
        result = sandbox.query(
            "request",
            self._runtime("known_tool"),
            None,
            [self._assistant_message("ghost_tool")],
            {},
        )
        self.assertEqual(self._tool_calls(result[3][-1]), [])

    def test_error_state_blocks_all_actions(self):
        sandbox = PermissionSandbox(["safe_tool"])
        sandbox.mark_error(ValueError("invalid JSON"))
        self.assertEqual(sandbox.policy_state, SandboxPolicyState.ERROR)
        result = sandbox.query(
            "request",
            self._runtime("safe_tool"),
            None,
            [self._assistant_message("safe_tool")],
            {},
        )
        self.assertEqual(self._tool_calls(result[3][-1]), [])

    def test_intent_parser_exception_sets_error_state_before_execution(self):
        class FailingCompletions:
            def create(self, **kwargs):
                raise TimeoutError("intent parser timeout")

        class FakeLLM:
            name = "test-model"
            client = SimpleNamespace(
                chat=SimpleNamespace(completions=FailingCompletions())
            )

            def query(self, query, runtime, env, messages, extra_args):
                self_message = {
                    "role": "assistant",
                    "content": [],
                    "tool_calls": [FunctionCall(function="send_message", args={})],
                }
                return query, runtime, env, [self_message], extra_args

        llm = FakeLLM()
        sandbox = PermissionSandbox([])
        executor = OurFrameExecutor(llm, sandbox=sandbox)
        runtime = self._runtime("send_message")

        executor.query(
            "send a message",
            runtime,
            None,
            [
                {
                    "role": "user",
                    "content": [{"type": "text", "content": "send a message"}],
                }
            ],
            {},
        )

        self.assertEqual(sandbox.policy_state, SandboxPolicyState.ERROR)
        result = sandbox.query(
            "request",
            runtime,
            None,
            [self._assistant_message("send_message")],
            {},
        )
        self.assertEqual(self._tool_calls(result[3][-1]), [])

    def test_mixed_batch_prunes_unknown_action_and_keeps_authorized_action(self):
        sandbox = PermissionSandbox(["safe_tool"])
        result = sandbox.query(
            "request",
            self._runtime("safe_tool"),
            None,
            [self._assistant_message("safe_tool", "unknown_tool")],
            {},
        )
        calls = result[3][-1]["tool_calls"]
        self.assertEqual([call.function for call in calls], ["safe_tool"])


if __name__ == "__main__":
    unittest.main()
