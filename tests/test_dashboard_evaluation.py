import json
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from dashboard import evaluation
from dashboard.app import app, runs_store, run_test_thread


ARTIFACT_ROOT = Path(__file__).resolve().parents[1] / "workshop/artifacts/20261030_fliter_goal_impl/offline/dashboard"


class DashboardEvaluationTests(unittest.TestCase):
    def setUp(self):
        selector = patch("dashboard.evaluation.get_suites", return_value=("shopping", "github", "dailylife"), create=True)
        selector.start()
        self.addCleanup(selector.stop)

    def test_router_api_threshold_is_validated_and_default_stays_off(self):
        self.assertEqual(evaluation.normalize_config({'suites':['shopping']})['audit_router_mode'], 'off')
        config = evaluation.normalize_config({'suites':['shopping'], 'audit_router_mode':'selective',
                                              'audit_router_threshold':.65})
        self.assertEqual(config['audit_router_threshold'], .65)
        for changes in ({'audit_router_threshold':True}, {'audit_router_threshold':float('nan')},
                        {'audit_router_mode':'selective','origin':True}, {'audit_router_artifact':'old.json'}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                evaluation.normalize_config({'suites':['shopping'], **changes})

    def test_layer_dependencies_and_v2_control_are_recorded_as_effective_config(self):
        config = evaluation.normalize_config({"suites": ["shopping"], "input_isolation": False,
                                              "authorization_precheck": False})
        self.assertFalse(config["input_isolation"])
        self.assertFalse(config["authorization_precheck"])
        disabled = evaluation.normalize_config({"suites": ["shopping"], "use_sandbox": False,
                                                "use_security_checker": False})
        self.assertFalse(disabled["input_isolation"])
        self.assertFalse(disabled["authorization_precheck"])

    def test_baseline_has_no_dscg_layers_or_security_connection(self):
        config = evaluation.normalize_config({"suites": ["shopping"], "origin": True,
                                              "sec_api_key": "unused", "sec_model_id": "unused"})
        for key in ("input_isolation", "authorization_precheck", "use_sandbox", "use_security_checker"):
            self.assertFalse(config[key])
        self.assertIsNone(config["sec_model_id"])
        self.assertIsNone(config["sec_api_key"])

    def test_invalid_values_are_rejected_before_a_run_starts(self):
        for invalid in ({"input_isolation": "false"}, {"trace_level": "verbose"},
                        {"max_user_tasks": -1}, {"max_injection_tasks": 1.5},
                        {"suites": []}, {"suites": ["unknown"]}):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                evaluation.normalize_config({"suites": ["shopping"], **invalid})

    def test_aggregate_uses_task_denominators_and_includes_security_cost(self):
        summaries = [
            {"metrics": {"utility_rate": 100, "attack_success_rate": 50},
             "task_counts": {"total_tasks": 2, "utility_passed": 2, "security_valid": 2, "attack_successes": 1, "security_missing": 0},
             "overhead": {"prompt_tokens": 80, "completion_tokens": 20, "total_tokens": 100},
             "sec_overhead": {"prompt_tokens": 30, "completion_tokens": 10, "total_tokens": 40}},
            {"metrics": {"utility_rate": 0, "attack_success_rate": 0},
             "task_counts": {"total_tasks": 8, "utility_passed": 0, "security_valid": 7, "attack_successes": 0,
                             "security_missing": 1}, "overhead": {"total_tokens": 60}},
        ]
        aggregate = evaluation.aggregate(summaries)
        self.assertEqual(aggregate["avg_utility_rate"], 20)
        self.assertEqual(aggregate["avg_attack_success_rate"], 11.11)
        self.assertEqual(aggregate["security_denominator"], 9)
        self.assertEqual(aggregate["security_missing"], 1)
        self.assertEqual(aggregate["total_tokens"], 200)
        self.assertEqual(aggregate["main_total_tokens"], 160)
        self.assertEqual(aggregate["security_total_tokens"], 40)

    def test_aggregate_does_not_pool_mixed_recorded_catalogs(self):
        summaries = [{"benchmark": {"id": "agentdyn", "catalog_sha256": catalog},
                      "metrics": {"attack_success_rate": 0},
                      "task_counts": {"total_tasks": 1, "utility_passed": 1, "security_valid": 1},
                      "overhead": {}} for catalog in ("catalog-a", "catalog-b")]
        result = evaluation.aggregate(summaries)
        self.assertIsNone(result["avg_utility_rate"])
        self.assertIsNone(result["security_denominator"])
        self.assertIsNone(result["total_tasks"])
        self.assertEqual(result["aggregation_warning"], "benchmark_or_catalog_mismatch")

    def test_clean_or_missing_security_is_not_zero_asr(self):
        aggregate = evaluation.aggregate([{"metrics": {"utility_rate": 100, "attack_success_rate": None},
                                          "task_counts": {"total_tasks": 1, "utility_passed": 1,
                                                          "security_valid": 0}, "overhead": {}}])
        self.assertIsNone(aggregate["avg_attack_success_rate"])
        self.assertIsNone(aggregate["avg_defense_success_rate"])

    def test_clean_report_supports_nonapplicable_security_metrics(self):
        runs_store["clean-report"] = {"config": {"run_attack": False}, "suites": [],
                                      "aggregate_metrics": {"avg_utility_rate": 100,
                                                            "avg_attack_success_rate": None,
                                                            "avg_defense_success_rate": None}}
        try:
            response = app.test_client().get("/api/report/clean-report")
            self.assertEqual(response.status_code, 200)
            self.assertIn("N/A", response.get_data(as_text=True))
        finally:
            runs_store.pop("clean-report", None)

    def test_legacy_asr_without_valid_counts_remains_unknown(self):
        summary = {"metrics": {"attack_success_rate": 50},
                   "task_counts": {"total_tasks": 3, "attacked_tasks": 3}, "overhead": {}}
        result = evaluation.aggregate([summary])
        self.assertIsNone(result["avg_attack_success_rate"])
        self.assertIsNone(result["security_denominator"])
        self.assertIsNone(result["security_missing"])

    def test_legacy_records_restore_valid_denominator_without_mutating_history(self):
        run = {"config": {"run_attack": True}, "suites": [
            {"suite_name": "workspace", "metrics": {"attack_success_rate": 50},
             "task_counts": {"total_tasks": 3, "utility_passed": 2, "attacked_tasks": 3}, "overhead": {}},
            {"suite_name": "travel", "metrics": {"attack_success_rate": 0},
             "task_counts": {"total_tasks": 1, "utility_passed": 1, "attacked_tasks": 1}, "overhead": {}}],
            "structured_records": [
                {"suite_name": "workspace", "user_task_id": "u1", "injection_task_id": "i1", "attack_success": True},
                {"suite_name": "workspace", "user_task_id": "u2", "injection_task_id": "i1", "attack_success": False},
                {"suite_name": "workspace", "user_task_id": "u3", "injection_task_id": "i1", "attack_success": None},
                {"suite_name": "travel", "user_task_id": "u1", "injection_task_id": "i1", "attack_success": False}]}
        result = evaluation.display_metrics(run)
        self.assertEqual(result["avg_attack_success_rate"], 33.33)
        self.assertEqual(result["security_denominator"], 3)
        self.assertEqual(result["security_missing"], 1)
        self.assertNotIn("security_valid", run["suites"][0]["task_counts"])

    def test_legacy_cost_is_consistent_in_overview_comparison_and_report(self):
        run = {"run_id": "cost-check", "config": {"origin": True, "run_attack": False},
               "suites": [{"suite_name": "workspace", "metrics": {"utility_rate": 100,
                          "attack_success_rate": 0, "defense_success_rate": 100},
                           "task_counts": {"total_tasks": 1, "utility_passed": 1},
                           "overhead": {"prompt_tokens": 80, "completion_tokens": 20, "total_tokens": 100},
                           "sec_overhead": {"prompt_tokens": 30, "completion_tokens": 10, "total_tokens": 40}}],
               "aggregate_metrics": {"total_tokens": 100}}
        runs_store["cost-check"] = run
        try:
            client = app.test_client()
            self.assertEqual(client.get("/api/runs/cost-check").get_json()["display_metrics"]["total_tokens"], 140)
            self.assertEqual(client.post("/api/compare", json={"run_ids": ["cost-check"]}).get_json()["token_metrics"]["total_tokens"], [140])
            self.assertEqual(client.post("/api/compare", json={"run_ids": ["cost-check"]}).get_json()["per_suite"]["workspace"]["attack_rates"], [None])
            report = client.get("/api/report/cost-check").get_data(as_text=True)
            self.assertIn("Total=140", report)
            self.assertIn("ASR: N/A", report)
            self.assertEqual(run["aggregate_metrics"]["total_tokens"], 100)
        finally:
            runs_store.pop("cost-check", None)

    def test_worker_saves_real_config_and_both_cost_roles_without_a_model_run(self):
        ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)
        config = evaluation.normalize_config({"suites": ["shopping"], "run_attack": False,
                                               "input_isolation": False, "authorization_precheck": False,
                                               "trace_level": "standard", "audit_router_mode":"shadow",
                                               "audit_router_threshold":.65})
        def factory(*args, **kwargs):
            self.assertFalse(kwargs["input_isolation"])
            self.assertFalse(kwargs["authorization_precheck"])
            self.assertEqual(kwargs["trace_level"], "standard")
            self.assertEqual(kwargs["audit_router_mode"], "shadow")
            self.assertEqual(kwargs["audit_router_threshold"], .65)
            pipeline = SimpleNamespace(name="test-pipeline", dscg_optimization_config={
                "framework_version": "three-layer-v1", "input_isolation": False,
                "authorization_precheck": False, "use_security_checker": True})
            main = SimpleNamespace(total_prompt_tokens=80, total_completion_tokens=20, get_total_tokens=lambda:100)
            sec = SimpleNamespace(total_prompt_tokens=30, total_completion_tokens=10, get_total_tokens=lambda:40)
            return pipeline, main, sec
        def native_clean(pipeline, suite, attack, logdir, force_rerun=False, user_tasks=None, injection_tasks=None, benchmark_version=None):
            self.assertIsNone(attack)
            self.assertEqual(benchmark_version, "v1.2")
            return {"utility_results":{("u1",None):True}}
        with tempfile.TemporaryDirectory(dir=ARTIFACT_ROOT) as directory, \
             patch("dashboard.app.DASHBOARD_RESULTS_DIR", Path(directory)), \
             patch("dashboard.app.make_defended_pipeline", side_effect=factory), \
             patch("dashboard.app.validate_backend", return_value={"id": "agentdyn", "catalog_sha256": "test"}), \
             patch("dashboard.app.get_suite", return_value=SimpleNamespace(user_tasks={"u1":None}, injection_tasks={"i1":None})), \
             patch("dashboard.app.run_native_suite", side_effect=native_clean), \
             patch("dashboard.app.threading.Thread"):
            try:
                run_test_thread("worker-test", config)
                saved = json.loads((Path(directory)/"worker-test/overall_results.json").read_text())
                for name in ('summary.md','failure_cases.jsonl','l3_router_summary.json','l3_router_summary.md'):
                    self.assertTrue((Path(directory)/'worker-test'/name).is_file(),name)
                self.assertEqual(saved["aggregate_metrics"]["total_tokens"], 140)
                self.assertIsNone(saved["aggregate_metrics"]["avg_attack_success_rate"])
                self.assertFalse(saved["suites"][0]["framework"]["input_isolation"])
            finally:
                runs_store.pop("worker-test", None)

    def test_flat_layout_is_part_of_effective_config_identity(self):
        for supplied in ({}, {'task_layout': 'legacy'}):
            config = evaluation.normalize_config({'suites': ['shopping'], **supplied})
            self.assertEqual(config['task_layout'], 'flat-v1')

    def test_worker_native_clean_and_attack_write_flat_scored_traces_without_goal(self):
        from agentdojo import logging
        users = {'user_task_0': SimpleNamespace(ID='user_task_0')}
        targets = {'injection_task_0': SimpleNamespace(ID='injection_task_0')}
        calls = []
        def execute(pipeline, task, injection_task=None, injections=None):
            calls.append((task.ID, getattr(injection_task, 'ID', None)))
            logging.Logger.get().log([
                {'role': 'user', 'content': [{'type': 'text', 'content': 'fixture'}]},
                {'role': 'assistant', 'tool_calls': None, 'content': [{'type': 'text', 'content': 'done'}]}])
            return True, False
        suite = SimpleNamespace(name='shopping', user_tasks=users, injection_tasks=targets,
            get_user_task_by_id=users.__getitem__, get_injection_task_by_id=targets.__getitem__,
            run_task_with_pipeline=execute)
        tracker = SimpleNamespace(total_prompt_tokens=0, total_completion_tokens=0, get_total_tokens=lambda: 0)
        pipeline = SimpleNamespace(name='offline', dscg_model_config={'model_id': 'offline'})
        attack = SimpleNamespace(name='important_instructions', is_dos_attack=False, attack=lambda *_: {})
        ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ARTIFACT_ROOT) as directory, \
             patch('dashboard.app.DASHBOARD_RESULTS_DIR', Path(directory)), \
             patch('dashboard.app.make_openai_compatible_pipeline', return_value=(pipeline, tracker)), \
             patch('dashboard.app.validate_backend', return_value={'id': 'agentdyn'}), \
             patch('dashboard.app.get_suite', return_value=suite), \
             patch('dashboard.app.check_attack_compatibility', return_value=None), \
             patch('dashboard.app.attacks.load_attack', return_value=attack), \
             patch('agentdojo.benchmark.benchmark_suite_with_injections', side_effect=AssertionError('suite runner bypass')), \
             patch('agentdojo.benchmark.benchmark_suite_without_injections', side_effect=AssertionError('suite runner bypass')), \
             patch('dashboard.app.threading.Thread'):
            for attacked in (False, True):
                run_id = 'native-attack' if attacked else 'native-clean'
                config = evaluation.normalize_config({'suites': ['shopping'], 'origin': True,
                    'run_attack': attacked, 'attack_name': attack.name})
                try:
                    run_test_thread(run_id, config)
                    run_dir = Path(directory)/run_id
                    saved = json.loads((run_dir/'overall_results.json').read_text())
                    self.assertEqual(saved['config']['task_layout'], 'flat-v1')
                    self.assertEqual(saved['suites'][0]['task_counts']['total_tasks'], 1)
                    self.assertEqual(saved['suites'][0]['metrics']['utility_rate'], 100)
                    self.assertEqual(saved['suites'][0]['metrics']['attack_success_rate'], 0 if attacked else None)
                    trace = run_dir/'offline/shopping/user_task_0'/('injection_task_0.json' if attacked else 'none.json')
                    self.assertTrue(trace.is_file())
                    self.assertEqual(len(list(run_dir.rglob('user_task_0/*.json'))), 1)
                    self.assertFalse((run_dir/'offline/shopping/injection_task_0').exists())
                finally:
                    runs_store.pop(run_id, None)
        self.assertEqual(calls, [('user_task_0', None), ('user_task_0', 'injection_task_0')])

    def test_trace_stats_exclude_preflights_and_report_missing_coverage(self):
        ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ARTIFACT_ROOT) as directory:
            root = Path(directory)
            task = root / "pipeline/workspace/user_task_0/important_instructions/injection_task_0.json"
            task.parent.mkdir(parents=True)
            task.write_text(json.dumps({"dscg_layer_routing": {"precheck_rejected_batches": 2},
                                        "dscg_input_isolation": {"added_characters_total": 120}}))
            (task.parent / "none.json").write_text(json.dumps({"dscg_layer_routing": {"semantic_audit_calls": 99}}))
            stats = evaluation.trace_stats(root, "pipeline", "workspace", "important_instructions",
                                           [("user_task_0", "injection_task_0"), ("user_task_1", "injection_task_0")])
            self.assertEqual(stats["expected_records"], 2)
            self.assertEqual(stats["routing_records"], 1)
            self.assertEqual(stats["routing"]["precheck_rejected_batches"], 2)
            self.assertEqual(stats["routing"]["semantic_audit_calls"], 0)
            self.assertEqual(stats["isolation"]["added_characters_total"], 120)


if __name__ == "__main__":
    unittest.main()
