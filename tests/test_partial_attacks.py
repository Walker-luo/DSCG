from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import json
import gzip
import os
from pathlib import Path
from test_partial_agentdyn import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from agentdojo.attacks.attack_registry import ATTACKS
from agentdojo import attacks
from agentdojo.task_suite import get_suite

from experiments import run_partial_benchmark as runner
from dscg.pipelines.defended import _append_full_trace


def fake_pipeline(*args, **kwargs):
    return SimpleNamespace(name="offline-model", dscg_model_config={"model_id": "offline-model"}), SimpleNamespace(
        total_prompt_tokens=0, total_completion_tokens=0, get_total_tokens=lambda: 0,
    )


def fake_attack(name, suite, pipeline):
    return SimpleNamespace(name=name, is_dos_attack=ATTACKS[name].is_dos_attack)


def fake_results(pipeline, suite, attack, logdir, **kwargs):
    injections = ([next(iter(suite.injection_tasks))] if attack.is_dos_attack else kwargs["injection_tasks"])
    keys = [(user, injection) for user in kwargs["user_tasks"] for injection in injections]
    return {"utility_results": dict.fromkeys(keys, True), "security_results": dict.fromkeys(keys, False)}


class PartialAttackTests(unittest.TestCase):
    def test_cli_defaults_to_typical_and_accepts_all_or_specific_attack_flags(self):
        with patch.object(runner, "main", return_value=0) as run, patch.dict(os.environ, {}, clear=True):
            self.assertEqual(runner.cli([]), 0)
            self.assertEqual(run.call_args.kwargs["attack"], ["typical"])
            self.assertEqual(runner.cli(["--attack", "all"]), 0)
            self.assertEqual(run.call_args.kwargs["attack"], ["all"])
            self.assertEqual(runner.cli([
                "--baseline", "--attack", "tool_knowledge", "injecagent",
                "--attack", "ignore_previous",
            ]), 0)
            self.assertEqual(run.call_args.kwargs["attack"], ["tool_knowledge", "injecagent", "ignore_previous"])

    def test_cli_rejects_unknown_attack_before_model_initialization(self):
        with patch.object(runner, "main") as run, redirect_stderr(StringIO()):
            for name in ["not-an-attack", "manual"]:
                with self.subTest(attack=name), self.assertRaises(SystemExit) as error:
                    runner.cli(["--attack", name])
                self.assertEqual(error.exception.code, 2)
                run.assert_not_called()

    def test_selection_is_registry_based_stable_and_deduplicated(self):
        expected = sorted(name for name in ATTACKS if name != "manual")
        self.assertEqual(runner.resolve_attack_names("all"), expected)
        self.assertEqual(runner.resolve_attack_names(["tool_knowledge", "injecagent", "tool_knowledge"]), ["tool_knowledge", "injecagent"])
        with self.assertRaises(ValueError):
            runner.resolve_attack_names("manual")
        with self.assertRaises(ValueError):
            runner.resolve_attack_names(["all", "injecagent"])

    def test_typical_preset_is_fixed_targeted_and_rejects_mixed_selections(self):
        expected = ["ignore_previous", "important_instructions", "tool_knowledge"]
        self.assertEqual(runner.resolve_attack_names(), expected)
        self.assertEqual(runner.resolve_attack_names("typical"), expected)
        self.assertTrue(all(not ATTACKS[name].is_dos_attack for name in expected))
        for selection in [["typical", "injecagent"], ["typical", "all"]]:
            with self.subTest(selection=selection), self.assertRaises(ValueError):
                runner.resolve_attack_names(selection)
        with patch.dict(ATTACKS, {name: cls for name, cls in ATTACKS.items()
                                 if name != "tool_knowledge"}, clear=True):
            with self.assertRaises(ValueError):
                runner.resolve_attack_names("typical")

    def test_all_registered_automatic_payloads_generate_on_current_task_grid(self):
        # Real attack construction and ground-truth injection reachability;
        # no model factory or network client is involved.
        pipeline = SimpleNamespace(name="gpt-4o-2024-05-13")
        generated = 0
        for name in runner.resolve_attack_names("all"):
            for suite_name in ["workspace", "travel", "banking", "slack"]:
                suite = get_suite("v1.2", suite_name)
                attack = attacks.load_attack(name, suite, pipeline)
                users = list(suite.user_tasks)[:3]
                injections = (list(suite.injection_tasks)[:1] if attack.is_dos_attack
                              else list(suite.injection_tasks)[:3])
                for user in users:
                    for injection in injections:
                        with self.subTest(attack=name, suite=suite_name, user=user, injection=injection):
                            payload = attack.attack(suite.user_tasks[user], suite.injection_tasks[injection])
                            self.assertTrue(payload)
                            self.assertTrue(set(payload) <= suite.get_injection_vector_defaults().keys())
                            self.assertTrue(all(isinstance(value, str) and value for value in payload.values()))
                            generated += 1
        expected = sum(12 if cls.is_dos_attack else 36 for name, cls in ATTACKS.items() if name != "manual")
        self.assertEqual(generated, expected)

    def test_default_and_all_keep_reports_and_task_subsets_separate_in_both_modes(self):
        selections = {
            "typical": ["ignore_previous", "important_instructions", "tool_knowledge"],
            "all": sorted(name for name in ATTACKS if name != "manual"),
        }
        suite = get_suite("v1.2", "workspace")
        users = list(suite.user_tasks)[:3]
        injections = list(suite.injection_tasks)[:3]
        with TemporaryDirectory() as directory, redirect_stdout(StringIO()), patch.object(
            runner, "make_openai_compatible_pipeline", side_effect=fake_pipeline
        ), patch.object(runner, "make_defended_pipeline", side_effect=lambda *a, **k: (*fake_pipeline(), None)), patch.object(
            runner, "load_tool_metadata", return_value={}
        ), patch.object(runner.attacks, "load_attack", side_effect=fake_attack) as load, patch.object(
            runner.benchmark, "benchmark_suite_with_injections", side_effect=fake_results
        ) as benchmark:
            for preset, origin in [(preset, origin) for preset in selections for origin in [True, False]]:
                selected_attacks = selections[preset]
                mode = f"{'baseline' if origin else 'dscg'}_{preset}"
                self.assertEqual(runner.main(origin=origin, suites=["workspace"], run_name=mode,
                                             results_dir=directory, force_rerun=True,
                                             **({"attack": "all"} if preset == "all" else {})), 0)
                base = Path(directory) / f"agentdojo/offline-model_{mode}"
                manifest = json.loads((base / "attack_manifest.json").read_text())
                self.assertEqual(manifest["attacks"], selected_attacks)
                self.assertEqual(manifest["excluded_from_all"], {"manual": "requires interactive input"})
                self.assertEqual(len(manifest["runs"]), len(selected_attacks))
                combined = (base / "summary.md").read_text()
                self.assertFalse(list(base.rglob('all_report.txt')))
                self.assertFalse(list(base.rglob('report.txt')))
                for attack_name in selected_attacks:
                    output = base / attack_name / "workspace"
                    report = json.loads((output / "summary.json").read_text())
                    is_dos = ATTACKS[attack_name].is_dos_attack
                    expected_injections = [next(iter(suite.injection_tasks))] if is_dos else injections
                    self.assertEqual(report["task_selection"]["user_task_ids"], users)
                    self.assertEqual(report["task_selection"]["injection_task_ids"], expected_injections)
                    self.assertEqual(report["task_selection"]["attack"], attack_name)
                    self.assertEqual(report["attack_kind"], "dos" if is_dos else "targeted")
                    self.assertEqual(report["task_counts"]["planned_tasks"], 3 if is_dos else 9)
                    self.assertEqual(report["task_counts"]["total_tasks"], 3 if is_dos else 9)
                    self.assertIn(attack_name, (output / "detailed_results.csv").read_text())
                    self.assertIn(attack_name, combined)
                    self.assertEqual(Path(manifest["runs"][selected_attacks.index(attack_name)]["output_dir"]), base / attack_name)
                self.assertTrue(all(run["status"] == "completed" for run in manifest["runs"]))
            self.assertEqual(load.call_count, 2 * sum(len(names) for names in selections.values()))
            self.assertEqual(benchmark.call_count, load.call_count)
            self.assertTrue(all(call.kwargs["force_rerun"] for call in benchmark.call_args_list))

    def test_failed_attack_is_recorded_and_later_attacks_still_run(self):
        def results(*args, **kwargs):
            if args[2].name == "tool_knowledge":
                raise ValueError("fixture attack unavailable")
            return fake_results(*args, **kwargs)

        with TemporaryDirectory() as directory, redirect_stdout(StringIO()), patch.object(
            runner, "make_openai_compatible_pipeline", side_effect=fake_pipeline
        ), patch.object(runner.attacks, "load_attack", side_effect=fake_attack), patch.object(
            runner.benchmark, "benchmark_suite_with_injections", side_effect=results
        ):
            self.assertEqual(runner.main(origin=True, suites=["workspace"], run_name="partial",
                                         results_dir=directory, attack=["tool_knowledge", "injecagent"]), 1)
            manifest = json.loads((Path(directory) / "agentdojo/offline-model_partial" / "attack_manifest.json").read_text())
            self.assertEqual([run["status"] for run in manifest["runs"]], ["error", "completed"])
            self.assertEqual(manifest["runs"][0]["error_type"], "ValueError")
            self.assertTrue((Path(directory) / "agentdojo/offline-model_partial/injecagent/workspace/summary.json").exists())

    def test_native_traces_sidecars_and_cache_use_the_nested_attack_directory(self):
        # Real AgentDojo logger/cache, with task execution replaced by an offline oracle.
        suite = get_suite("v1.2", "workspace")
        model_id = "gpt-4o-2024-05-13"
        attack_name = "tool_knowledge"  # This real template infers the model name at construction.
        def pipeline_factory(*args, **kwargs):
            pipeline, tracker = fake_pipeline()
            pipeline.name = model_id
            pipeline.dscg_model_config["model_id"] = model_id
            return pipeline, tracker

        def execute(*args, **kwargs):
            runner.logging.Logger.get().log([
                {"role": "user", "content": [{"type": "text", "content": "offline fixture"}]},
                {"role": "assistant", "content": [{"type": "text", "content": "done"}], "tool_calls": None},
            ])
            _append_full_trace({"_dscg_trace_level": "full"}, "fixture", {"offline": True})
            return True, False

        with TemporaryDirectory() as directory, redirect_stdout(StringIO()), patch.object(
            runner, "make_openai_compatible_pipeline", side_effect=pipeline_factory
        ), patch.object(type(suite), "run_task_with_pipeline", autospec=True, side_effect=execute) as task:
            options = dict(model_id=model_id, origin=True, suites=["workspace"], run_name="baseline",
                           results_dir=directory, attack=attack_name)
            self.assertEqual(runner.main(**options), 0)
            self.assertEqual(task.call_count, 12)  # 3 prechecks + 9 attacked tasks.
            root = Path(directory) / f"agentdojo/{model_id}_baseline"
            result = root / attack_name / "workspace"
            injection = next(iter(suite.injection_tasks))
            trace = result / "user_task_0" / attack_name / f"{injection}.json"
            self.assertTrue(trace.exists())
            raw = json.loads(trace.read_text())
            self.assertEqual(raw["attack_type"], attack_name)
            self.assertEqual(raw["benchmark_version"], "v1.2")
            self.assertIn("GPT-4", "\n".join(raw["injections"].values()))
            self.assertTrue(raw["utility"])
            cached = runner.benchmark.load_task_results(attack_name, "workspace", "user_task_0",
                                                        attack_name, injection, root)
            self.assertTrue(cached.utility)
            with gzip.open(trace.with_suffix(".dscg_trace.jsonl.gz"), "rt") as stream:
                self.assertEqual(json.loads(stream.readline())["event"], "fixture")
            self.assertTrue((result / "summary.json").exists())
            self.assertTrue((root / "summary.md").exists())
            self.assertFalse((root / "all_report.txt").exists())
            legacy_report = root / 'all_report.txt'
            legacy_report.write_text('Historical report: preserve original bytes.')
            before = trace.read_bytes()
            self.assertEqual(runner.main(**options), 0)
            self.assertEqual(legacy_report.read_text(), 'Historical report: preserve original bytes.')
            self.assertEqual(task.call_count, 12)  # All raw results reused from the new path.
            self.assertEqual(trace.read_bytes(), before)
            self.assertEqual(runner.main(**options, force_rerun=True), 0)
            self.assertEqual(task.call_count, 24)

    def test_cli_returns_nonzero_for_partial_attack_failure(self):
        with patch.object(runner, "main", return_value=1):
            self.assertEqual(runner.cli(["--attack", "tool_knowledge"]), 1)

    def test_no_attack_python_mode_runs_once_without_loading_attack(self):
        with TemporaryDirectory() as directory, redirect_stdout(StringIO()), patch.object(
            runner, "make_openai_compatible_pipeline", side_effect=fake_pipeline
        ), patch.object(runner.attacks, "load_attack") as load, patch.object(
            runner.benchmark, "benchmark_suite_without_injections",
            autospec=True,
            return_value={"utility_results": {("user_task_0", None): True}},
        ) as benchmark:
            self.assertEqual(runner.main(origin=True, suites=["workspace"], results_dir=directory,
                                         run_attack=False), 0)
            load.assert_not_called()
            benchmark.assert_called_once()


if __name__ == "__main__":
    unittest.main()


# Explicitly retain historical upstream suites as generic offline fixtures.
def setUpModule():
    global _fixture_backend
    from test_partial_agentdyn import legacy_fixture_backend
    _fixture_backend = legacy_fixture_backend(globals())


def tearDownModule():
    _fixture_backend.close()
