"""Execution guidance belongs in DSCG's system message, not native baseline or grants."""
import unittest
from unittest.mock import Mock, patch

from agentdojo.functions_runtime import FunctionsRuntime
from agentdojo.types import get_text_content_as_str
from dscg.model_config import ModelConfig
from dscg.pipelines.baseline import make_openai_compatible_pipeline
from dscg.pipelines.defended import make_defended_pipeline, load_system_message, SandboxPolicyState


class ExecutionPolicyTests(unittest.TestCase):
    config = ModelConfig(provider="custom", model_id="fixture", api_key="offline", base_url="http://offline")

    def test_default_guidance_is_delivered_as_system_data_without_granting_tools(self):
        with patch("dscg.pipelines.defended.create_openai_client", return_value=Mock()):
            pipeline, _, _ = make_defended_pipeline(model_config=self.config, use_security_checker=False)
        *_, messages, _ = pipeline.elements[0].query("task", FunctionsRuntime(), messages=[])
        self.assertEqual(messages[0]["role"], "system")
        content = get_text_content_as_str(messages[0]["content"])
        self.assertTrue(content.startswith(load_system_message(None)))
        self.assertGreater(len(content), len(load_system_message(None)))
        self.assertFalse(pipeline.dscg_optimization_config["completion_prompt"])
        self.assertEqual(pipeline.dscg_optimization_config["audit_retries"], 0)
        self.assertEqual(pipeline.reference_monitor.sandbox.policy_state, SandboxPolicyState.UNINITIALIZED)

    def test_native_baseline_retains_exact_original_system_message(self):
        with patch("dscg.pipelines.baseline.create_openai_client", return_value=Mock()):
            pipeline, _ = make_openai_compatible_pipeline(model_config=self.config)
        *_, messages, _ = pipeline.elements[0].query("task", FunctionsRuntime(), messages=[])
        self.assertEqual(get_text_content_as_str(messages[0]["content"]), load_system_message(None))

    def test_disabling_both_framework_layers_retains_original_system_message(self):
        with patch("dscg.pipelines.defended.create_openai_client", return_value=Mock()):
            pipeline, _, _ = make_defended_pipeline(
                model_config=self.config, use_sandbox=False, use_security_checker=False)
        *_, messages, _ = pipeline.elements[0].query("task", FunctionsRuntime(), messages=[])
        self.assertEqual(get_text_content_as_str(messages[0]["content"]), load_system_message(None))
