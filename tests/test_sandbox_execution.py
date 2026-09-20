"""Offline regressions with AgentDojo's executor and local recording tools."""
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from agentdojo import agent_pipeline
from agentdojo.functions_runtime import EmptyEnv, FunctionCall, FunctionsRuntime

from dscg.pipelines.defended import (
    OurFrameExecutor, PermissionSandbox, SandboxPolicyState, make_defended_pipeline,
)
from dscg.model_config import ModelConfig


def assistant(*names):
    return {
        "role": "assistant", "content": [],
        "tool_calls": [FunctionCall(function=name, args={}, id=str(i))
                       for i, name in enumerate(names)],
    }


USER = {"role": "user", "content": [{"type": "text", "content": "test request"}]}


class SandboxExecutionTests(unittest.TestCase):
    def setUp(self):
        self.executed = []
        self.runtime = FunctionsRuntime()

        @self.runtime.register_function
        def safe_tool() -> str:
            """Record a permitted local action."""
            self.executed.append("safe_tool")
            return "ok"

        @self.runtime.register_function
        def forbidden_tool() -> str:
            """Record a forbidden local action."""
            self.executed.append("forbidden_tool")
            return "ok"

        self.env = EmptyEnv()

    def execute(self, sandbox, *names):
        state = sandbox.query("test", self.runtime, self.env, [assistant(*names)], {})
        agent_pipeline.ToolsExecutor().query(*state)
        return state[3][-1]

    def test_empty_policies_with_bound_model_never_execute_or_retry(self):
        for tools in (None, []):
            with self.subTest(tools=tools):
                sandbox = PermissionSandbox(tools, model=Mock())
                self.assertEqual(self.execute(sandbox, "safe_tool")["tool_calls"], [])
                sandbox.llm.query.assert_not_called()
                self.assertEqual(self.executed, [])

    def test_mixed_batches_execute_only_authorized_actions(self):
        for denied in ("ghost_tool", "forbidden_tool"):
            with self.subTest(denied=denied):
                self.executed.clear()
                self.execute(PermissionSandbox(["safe_tool"]), denied, "safe_tool")
                self.assertEqual(self.executed, ["safe_tool"])

    def parser_llm(self, content='{"tools": ["safe_tool"]}', refusal=None, finish="stop"):
        llm = SimpleNamespace(name="offline-model", client=Mock(), query=Mock())
        llm.client.chat.completions.create.return_value = SimpleNamespace(choices=[
            SimpleNamespace(message=SimpleNamespace(content=content, refusal=refusal),
                            finish_reason=finish)
        ])
        llm.query.side_effect = lambda q, r, e, m, a: (q, r, e, [*m, assistant("safe_tool")], a)
        return llm

    def test_parser_failures_clear_existing_policy_and_cannot_execute(self):
        cases = [
            {"content": "not JSON"}, {"content": None}, {"content": "{}"},
            {"content": '{"tools": "safe_tool"}'}, {"content": '{"tools": [1]}'},
            {"content": '{"tools": ["safe_tool", "ghost_tool"]}'},
            {"content": '{"tools": [], "extra": true}'},
            {"refusal": "refused"}, {"finish": "length"}, {"finish": "content_filter"},
            {"timeout": True},
        ]
        for case in cases:
            with self.subTest(case=case):
                llm = self.parser_llm(**{k: v for k, v in case.items() if k != "timeout"})
                if case.get("timeout"):
                    llm.client.chat.completions.create.side_effect = TimeoutError()
                sandbox = PermissionSandbox(["safe_tool"], model=llm)
                executor = OurFrameExecutor(llm, sandbox)
                state = executor.query("test", self.runtime, self.env, [USER], {})
                self.assertEqual(sandbox.policy_state, SandboxPolicyState.ERROR)
                state = sandbox.query(*state)
                agent_pipeline.ToolsExecutor().query(*state)
                self.assertEqual(self.executed, [])
                self.assertEqual(llm.query.call_count, 1)

    def test_parser_valid_object_and_legacy_array(self):
        for content in ('{"tools": ["safe_tool"]}', '["safe_tool"]'):
            llm = self.parser_llm(content)
            result = OurFrameExecutor(llm)._authorize_tools_dynamically("test", self.runtime, [])
            self.assertEqual(result, ["safe_tool"])
            self.assertEqual(llm.client.chat.completions.create.call_args.kwargs["timeout"], 30.0)

    def test_valid_empty_parser_response_is_not_an_error(self):
        result = OurFrameExecutor(self.parser_llm('{"tools": []}'))._authorize_tools_dynamically(
            "test", self.runtime, []
        )
        sandbox = PermissionSandbox(result)
        self.assertEqual(sandbox.policy_state, SandboxPolicyState.INITIALIZED_EMPTY)
        self.execute(sandbox, "safe_tool")
        self.assertEqual(self.executed, [])

    def test_new_text_only_turn_clears_old_permissions(self):
        llm = self.parser_llm()
        llm.query.side_effect = lambda q, r, e, m, a: (q, r, e, [*m, assistant()], a)
        sandbox = PermissionSandbox(["safe_tool"])
        OurFrameExecutor(llm, sandbox).query("test", self.runtime, self.env, [USER], {})
        self.assertEqual(sandbox.policy_state, SandboxPolicyState.UNINITIALIZED)
        self.execute(sandbox, "safe_tool")
        self.assertEqual(self.executed, [])

    def test_invalid_policy_update_revokes_old_permissions(self):
        for invalid in ("safe_tool", [None], [""]):
            with self.subTest(invalid=invalid):
                sandbox = PermissionSandbox(["safe_tool"])
                with self.assertRaises((ValueError, TypeError)):
                    sandbox.allowed_tools = invalid
                self.assertEqual(sandbox.policy_state, SandboxPolicyState.ERROR)
                self.execute(sandbox, "safe_tool")
                self.assertEqual(self.executed, [])

    def test_allowlist_cannot_be_mutated_through_input_or_getter(self):
        tools = ["safe_tool"]
        sandbox = PermissionSandbox(tools)
        tools.append("forbidden_tool")
        sandbox.allowed_tools.append("forbidden_tool")
        self.execute(sandbox, "forbidden_tool")
        self.assertEqual(self.executed, [])

    def test_checker_replacement_is_filtered_in_actual_pipeline_order(self):
        config = ModelConfig(
            model_id="deepseek-flash",
            api_key="test-key",
            base_url="https://api.deepseek.com",
            provider="deepseek",
        )
        with patch("dscg.pipelines.defended.create_openai_client", return_value=Mock()):
            pipeline, _, _ = make_defended_pipeline(model_config=config, sec_model_config=config)
        loop = pipeline.elements[-1]
        sandbox = loop.elements[0]
        sandbox.allowed_tools = ["safe_tool"]
        checker = loop.elements[1]
        replacement = lambda q, r, e, m, a: (q, r, e, [*m[:-1], assistant("forbidden_tool")], a)
        with patch.object(checker, "query", side_effect=replacement):
            state = ("test", self.runtime, self.env, [assistant("safe_tool")], {})
            for element in loop.elements[:-1]:  # through ToolsExecutor; no model calls
                state = element.query(*state)
        self.assertEqual(self.executed, [])


if __name__ == "__main__":
    unittest.main()
