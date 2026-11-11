from contextlib import redirect_stdout
from io import StringIO
import json
import os
from pathlib import Path
from test_partial_agentdyn import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from agentdojo import agent_pipeline
from agentdojo.task_suite import get_suite

from dscg.model_config import ModelConfigurationError, resolve_model_config
from dscg.pipelines import baseline
from experiments import run_partial_benchmark as runner


SUITES = ["workspace", "travel", "banking", "slack"]


class PartialBaselineTests(unittest.TestCase):
    def test_cli_baseline_retains_attack_and_forces_rerun(self):
        with patch.object(runner, "main") as run, patch.dict(os.environ, {}, clear=True):
            self.assertEqual(runner.cli([
                "--baseline", "--force-rerun", "--name", "baseline-check",
                "--attack", "important_instructions",
            ]), 0)
        options = run.call_args.kwargs
        self.assertTrue(options["origin"])
        self.assertIsNone(options["defense"])
        self.assertTrue(options["run_attack"])
        self.assertTrue(options["force_rerun"])
        self.assertEqual(options["suites"], SUITES)
        self.assertEqual(options["run_name"], "baseline-check")
        self.assertEqual(options["attack"], ["important_instructions"])

    def test_cli_default_keeps_dscg_and_cache_policy(self):
        with patch.object(runner, "main") as run, patch.dict(os.environ, {}, clear=True):
            self.assertEqual(runner.cli([]), 0)
        self.assertFalse(run.call_args.kwargs["origin"])
        self.assertFalse(run.call_args.kwargs["force_rerun"])

    def test_cli_retains_force_rerun_environment_switch(self):
        with patch.object(runner, "main") as run, patch.dict(
            os.environ, {"DSCG_FORCE_RERUN": "1"}, clear=True
        ):
            self.assertEqual(runner.cli(["--baseline"]), 0)
        self.assertTrue(run.call_args.kwargs["force_rerun"])

    def test_cli_configuration_failure_returns_nonzero(self):
        with patch.object(runner, "main", side_effect=ModelConfigurationError("missing model")), redirect_stdout(StringIO()):
            self.assertEqual(runner.cli(["--baseline"]), 1)

    @staticmethod
    def fake_pipeline(*args, **kwargs):
        pipeline = SimpleNamespace(
            name="offline-model",
            dscg_model_config={"model_id": "offline-model"},
        )
        tracker = SimpleNamespace(
            total_prompt_tokens=0, total_completion_tokens=0,
            get_total_tokens=lambda: 0,
        )
        return pipeline, tracker

    @staticmethod
    def fake_results(*args, **kwargs):
        keys = [
            (user, injection)
            for user in kwargs["user_tasks"]
            for injection in kwargs["injection_tasks"]
        ]
        return {
            "utility_results": dict.fromkeys(keys, True),
            "security_results": dict.fromkeys(keys, False),
        }

    def test_baseline_and_dscg_use_identical_actual_catalog_subsets(self):
        with TemporaryDirectory() as directory, redirect_stdout(StringIO()), patch.object(
            runner, "make_openai_compatible_pipeline", side_effect=self.fake_pipeline
        ) as original, patch.object(
            runner, "make_defended_pipeline",
            side_effect=lambda *args, **kwargs: (*self.fake_pipeline(), None),
        ) as defended, patch.object(runner, "load_tool_metadata", return_value={}), patch.object(
            runner.attacks, "load_attack", return_value=SimpleNamespace(is_dos_attack=False)
        ) as attack, patch.object(
            runner.benchmark, "benchmark_suite_with_injections", side_effect=self.fake_results
        ) as benchmark:
            for origin, name in [(True, "baseline"), (False, "dscg")]:
                runner.main(origin=origin, suites=SUITES, run_name=name,
                            force_rerun=True, results_dir=directory, attack="important_instructions")
            self.assertEqual(original.call_count, 4)
            self.assertEqual(defended.call_count, 4)
            self.assertEqual(benchmark.call_count, 8)
            for index, suite_name in enumerate(SUITES):
                suite = get_suite("v1.2", suite_name)
                expected = {
                    "suite_version": "v1.2",
                    "seed": 7,
                    "user_task_ids": list(suite.user_tasks)[:3],
                    "injection_task_ids": list(suite.injection_tasks)[:3],
                    "attack": "important_instructions",
                }
                for call_index, mode in [(index, "baseline"), (index + 4, "dscg")]:
                    options = benchmark.call_args_list[call_index].kwargs
                    self.assertEqual(options["user_tasks"], expected["user_task_ids"])
                    self.assertEqual(options["injection_tasks"], expected["injection_task_ids"])
                    self.assertTrue(options["force_rerun"])
                    report = json.loads((Path(directory) / f"offline-model_agentdojo_{mode}" / "important_instructions" / suite_name / "summary.json").read_text())
                    self.assertEqual(report["task_selection"], expected)
                    self.assertEqual(report["task_counts"]["total_tasks"], 9)
                    self.assertEqual(report["defense"], None if mode == "baseline" else "dscg")
                    if mode == "baseline":
                        self.assertNotIn("sec_overhead", report)
                self.assertIsNone(original.call_args_list[index].kwargs["ad_defense"])
            self.assertTrue(all(call.args[0] == "important_instructions" for call in attack.call_args_list))

    def test_baseline_does_not_load_defense_metadata_or_security_pipeline(self):
        with TemporaryDirectory() as directory, redirect_stdout(StringIO()), patch.object(
            runner, "make_openai_compatible_pipeline", side_effect=self.fake_pipeline
        ), patch.object(runner, "make_defended_pipeline") as defended, patch.object(
            runner, "load_tool_metadata", side_effect=AssertionError("defense metadata was read")
        ) as metadata, patch.object(runner.attacks, "load_attack", return_value=SimpleNamespace(is_dos_attack=False)), patch.object(
            runner.benchmark, "benchmark_suite_with_injections", side_effect=self.fake_results
        ):
            runner.main(origin=True, suites=["workspace"], results_dir=directory,
                        tool_metadata_path="/nonexistent/defense.toml", attack="important_instructions")
            defended.assert_not_called()
            metadata.assert_not_called()

    def test_original_pipeline_uses_native_tool_loop_without_defense(self):
        config = resolve_model_config(local_settings={"main": {
            "provider": "custom", "model_id": "offline-model",
            "base_url": "https://model.example/v1", "api_key": "test-key",
        }}, env={})
        with patch.object(baseline, "create_openai_client", return_value=Mock()):
            pipeline, _ = baseline.make_openai_compatible_pipeline(model_config=config)
        self.assertEqual([type(element) for element in pipeline.elements], [
            agent_pipeline.SystemMessage, agent_pipeline.InitQuery,
            agent_pipeline.OpenAILLM, agent_pipeline.ToolsExecutionLoop,
        ])
        self.assertEqual([type(element) for element in pipeline.elements[-1].elements], [
            agent_pipeline.ToolsExecutor, agent_pipeline.OpenAILLM,
        ])
        self.assertFalse(hasattr(pipeline, "dscg_security_model_config"))


if __name__ == "__main__":
    unittest.main()


# Explicitly retain historical upstream suites as generic offline fixtures.
def setUpModule():
    global _fixture_backend
    from test_partial_agentdyn import legacy_fixture_backend
    _fixture_backend = legacy_fixture_backend(globals())


def tearDownModule():
    _fixture_backend.close()
