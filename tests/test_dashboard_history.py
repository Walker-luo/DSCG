import csv
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from dashboard.app import app


def write_json(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(content), encoding="utf-8")


def summary(suite, utility, attack, defense):
    return {
        "suite_name": suite,
        "pipeline_name": "test-model",
        "metrics": {
            "utility_rate": utility,
            "attack_success_rate": attack,
            "defense_success_rate": defense,
        },
        "task_counts": {"total_tasks": 2, "utility_passed": 1, "attacked_tasks": 2},
        "overhead": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    }


class DashboardHistoryTests(unittest.TestCase):
    def test_backend_folders_and_legacy_results_stay_separate_in_history_and_export(self):
        sources=[]
        for backend,suite in [('agentdojo','workspace'),('agentdyn','shopping')]:
            identity={'id':backend,'revision':'revision-'+backend,'suite_version':'v1.2',
                      'verification_mode':'metadata_only','runtime_variant':'unverified'}
            payload={**summary(suite,.5,0,1),'benchmark':identity,
                     'task_selection':{'attack':'tool_knowledge','user_task_ids':['u1'],'injection_task_ids':['i1']}}
            for run in (f'{backend}/qwen_baseline',f'qwen_{backend}_baseline'):
                source=f'partial_benchmark/{run}/tool_knowledge';sources.append(source)
                write_json(self.results_root/source/suite/'summary.json',payload)
        with patch('dashboard.app.RESULTS_DIR',self.results_root):
            catalog=self.client.get('/api/history/catalog').get_json()
            rows=[row for row in catalog if row['source'] in sources]
            self.assertEqual(len(rows),4)
            self.assertEqual(len({row['id'] for row in rows}),4)
            self.assertEqual(len({row['model_group'] for row in rows}),4)
            self.assertTrue(all(row['result_folder']=='partial_benchmark' for row in rows))
            ids=[row['id'] for row in rows]
            analyzed=self.client.post('/api/history/analyze',json={'run_ids':ids}).get_json()
            self.assertFalse(analyzed['paired_comparison_ready'])
            response=self.client.post('/api/history/export',json={'run_ids':ids})
            self.assertEqual(response.status_code,200)
        with zipfile.ZipFile(io.BytesIO(response.data)) as archive:
            data=json.loads(archive.read('analysis.json'))
        self.assertEqual(len(data['experiments']),4)
        self.assertEqual({row['source'] for row in data['experiments']},set(sources))
        self.assertEqual({row['benchmark']['id'] for row in data['experiments']},{'agentdojo','agentdyn'})

    def test_history_preserves_dynamic_suites_and_recorded_benchmark_identity(self):
        identity = {"id": "agentdyn", "catalog_sha256": "catalog-a", "revision": "revision-a"}
        payload = {**summary("shopping", .5, 0, 1), "benchmark": identity,
                   "task_selection": {"user_task_ids": ["u1"], "injection_task_ids": ["i1"]}}
        write_json(self.results_root / "benchmarks/agentdyn_trial/tool_knowledge/shopping/summary.json", payload)
        with patch("dashboard.app.RESULTS_DIR", self.results_root):
            catalog = self.client.get("/api/history/catalog").get_json()
            run = next(row for row in catalog if row["source"].endswith("tool_knowledge"))
            legacy = next(row for row in catalog if row["source"].startswith("partial_benchmark"))
            self.assertEqual(run["benchmark"], identity)
            self.assertEqual(run["suites"][0]["suite_name"], "shopping")
            self.assertEqual(run["suites"][0]["task_selection"], payload["task_selection"])
            self.assertEqual(legacy["benchmark_id"], "unknown")
            self.assertIsNone(legacy["benchmark"])
            response = self.client.post("/api/history/analyze", json={"run_ids": [run["id"], legacy["id"]]})
            self.assertFalse(response.get_json()["paired_comparison_ready"])
            self.assertIn("benchmark_or_catalog_mismatch", response.get_json()["comparison_warnings"])
            analyzed = response.get_json()["experiments"][0]
            self.assertEqual(analyzed["benchmark"], identity)

    def test_export_includes_recorded_identity_and_warns_before_pairing(self):
        identity = {"id": "agentdojo", "repository": "https://github.com/ethz-spylab/agentdojo",
                    "revision": "revision", "suite_version": "v1.2",
                    "implementation_sha256": "impl", "catalog_sha256": "catalog",
                    "package_version": "0.1.35", "runtime_variant": "reviewed",
                    "source_kind": "pypi-release", "release_sha256": "release-hash",
                    **{role + "_sha256": role for role in ("tasks", "environments", "attacks", "tools")}}
        run_root = self.results_root / "dashboard/agentdyn_export"
        write_json(run_root / "overall_results.json", {
            "benchmark": identity, "config": {"benchmark": identity},
            "suites": [{**summary("github", 100, 0, 100), "benchmark": identity,
                        "task_counts": {"total_tasks": 2, "utility_passed": 1, "attacked_tasks": 2, "utility_valid": 1, "execution_errors": 1},
                        "task_selection": {"user_task_ids": ["u1"], "injection_task_ids": ["i1"]}}],
            "structured_records": [{"suite_name": "github", "user_task_id": "u1", "injection_task_id": "i1",
                "utility_success": True, "attack_success": False, "defense_success": True, "sample_status": "valid"}]})
        with patch("dashboard.app.RESULTS_DIR", self.results_root):
            catalog = self.client.get("/api/history/catalog").get_json()
            run = next(row for row in catalog if row["source"] == "dashboard/agentdyn_export")
            response = self.client.post("/api/history/export", json={"run_ids": [run["id"]]})
        self.assertEqual(response.status_code, 200)
        with zipfile.ZipFile(io.BytesIO(response.data)) as archive:
            data = json.loads(archive.read("analysis.json"))
            rows = list(csv.DictReader(io.StringIO(archive.read("task_records.csv").decode("utf-8-sig"))))
        self.assertEqual(data["experiments"][0]["benchmark"], identity)
        self.assertTrue(data["paired_comparison_ready"])
        counts = data["experiments"][0]["suites"][0]["task_counts"]
        self.assertEqual(counts["utility_valid"], 1)
        self.assertEqual(counts["execution_errors"], 1)
        self.assertEqual(rows[0]["benchmark_id"], "agentdojo")
        self.assertEqual(rows[0]["benchmark_catalog_sha256"], "catalog")
        for role in ("tasks", "environments", "attacks", "tools"):
            self.assertEqual(rows[0]["benchmark_" + role + "_sha256"], role)

    def test_unknown_sibling_suite_cannot_inherit_identity_or_pair(self):
        from dashboard.app import _history_benchmark_metadata, _comparison_metadata
        identity = {"id": "agentdyn", "repository": "repo", "revision": "rev", "suite_version": "v1.2",
                    "implementation_sha256": "impl", "catalog_sha256": "cat"}
        entry = {"suites": {"shopping": {"summary": {"benchmark": identity}}, "github": {"summary": {}}}}
        self.assertIsNone(_history_benchmark_metadata(entry)["benchmark"])
        selection = {"user_task_ids": ["u1"], "injection_task_ids": ["i1"]}
        run = {"benchmark": identity, "suites": [
            {"suite_name": "shopping", "benchmark": identity, "task_selection": selection},
            {"suite_name": "github", "benchmark": None, "task_selection": selection}]}
        comparison = _comparison_metadata([run, run])
        self.assertFalse(comparison["paired_comparison_ready"])
        self.assertIn("benchmark_identity_unavailable", comparison["comparison_warnings"])

    def setUp(self):
        artifact_root = Path(__file__).resolve().parents[1] / "workshop/artifacts/20261018_dual_benchmark/dashboard"
        artifact_root.mkdir(parents=True, exist_ok=True)
        self.temp_dir = tempfile.TemporaryDirectory(dir=artifact_root)
        self.results_root = Path(self.temp_dir.name)
        self.client = app.test_client()

        write_json(
            self.results_root / "partial_benchmark" / "trial-p04" / "workspace" / "summary.json",
            summary("workspace", 0.5, 0.25, 0.75),
        )
        csv_path = self.results_root / "partial_benchmark" / "trial-p04" / "workspace" / "detailed_results.csv"
        with csv_path.open("w", encoding="utf-8", newline="") as result_file:
            writer = csv.DictWriter(result_file, fieldnames=[
                "suite_name", "user_task_id", "injection_task_id", "utility_success",
                "attack_success", "defense_success",
            ])
            writer.writeheader()
            writer.writerow({
                "suite_name": "workspace",
                "user_task_id": "user_task_0",
                "injection_task_id": "injection_task_0",
                "utility_success": "True",
                "attack_success": "False",
                "defense_success": "True",
            })

        dashboard_root = self.results_root / "dashboard" / "run-001"
        write_json(
            dashboard_root / "overall_results.json",
            {
                "config": {"label": "Dashboard trial", "api_key": "must-not-leak"},
                "suites": [summary("travel", 100, 20, 80)],
                "structured_records": [{
                    "suite_name": "travel",
                    "user_task_id": "user_task_1",
                    "injection_task_id": "injection_task_1",
                    "utility_success": False,
                    "attack_success": True,
                    "defense_success": False,
                }],
            },
        )
        write_json(
            dashboard_root / "model-name" / "slack" / "summary.json",
            summary("slack", 25, 50, 50),
        )
        write_json(
            self.results_root / "benchmarks" / "ablation_study" / "model-name" / "banking" / "summary.json",
            summary("banking", 0.75, 0.25, 0.75),
        )
        csv_only = self.results_root / "partial_benchmark" / "csv-only" / "travel" / "detailed_results.csv"
        csv_only.parent.mkdir(parents=True, exist_ok=True)
        with csv_only.open("w", encoding="utf-8", newline="") as result_file:
            writer = csv.DictWriter(result_file, fieldnames=[
                "suite_name", "user_task_id", "injection_task_id", "utility_success",
                "attack_success", "defense_success",
            ])
            writer.writeheader()
            writer.writerows([
                {
                    "suite_name": "travel", "user_task_id": "user_task_0",
                    "injection_task_id": "injection_task_0", "utility_success": "True",
                    "attack_success": "False", "defense_success": "True",
                },
                {
                    "suite_name": "travel", "user_task_id": "user_task_1",
                    "injection_task_id": "injection_task_1", "utility_success": "False",
                    "attack_success": "True", "defense_success": "False",
                },
            ])
        bad_summary = self.results_root / "partial_benchmark" / "broken" / "workspace" / "summary.json"
        bad_summary.parent.mkdir(parents=True)
        bad_summary.write_text("{bad json", encoding="utf-8")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_dashboard_exposes_the_history_analysis_view(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"tab-history-analysis", response.data)
        self.assertIn(b'href="/history"', response.data)
        self.assertNotIn(b"history-analysis-modal", response.data)
        self.assertNotIn(b"/static/js/history.js", response.data)

    def test_history_is_a_separate_page_with_multiselect_models_and_no_experiment_script(self):
        response = self.client.get("/history")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"history-model-options", response.data)
        self.assertIn(b"history-model-select-all", response.data)
        self.assertIn(b"history-model-clear", response.data)
        self.assertIn(b"/static/js/history.js", response.data)
        self.assertNotIn(b"/static/js/app.js", response.data)
        self.assertNotIn(b"history-analysis-modal", response.data)
        self.assertIn(b'aria-current="page"', response.data)

    def test_catalog_discovers_result_layouts_and_normalizes_rates(self):
        with patch("dashboard.app.RESULTS_DIR", self.results_root):
            response = self.client.get("/api/history/catalog")
        self.assertEqual(response.status_code, 200)
        catalog = response.get_json()
        self.assertEqual(len(catalog), 4)
        partial = next(item for item in catalog if item["source"] == "partial_benchmark/trial-p04")
        self.assertEqual(partial["suites"][0]["metrics"]["utility_rate"], 50.0)
        csv_only = next(item for item in catalog if item["source"] == "partial_benchmark/csv-only")
        self.assertEqual(csv_only["suites"][0]["metrics"]["utility_rate"], 50.0)
        dashboard = next(item for item in catalog if item["source"] == "dashboard/run-001")
        self.assertEqual({item["suite_name"] for item in dashboard["suites"]}, {"travel", "slack"})
        self.assertNotIn("must-not-leak", json.dumps(catalog))

    def test_catalog_groups_nested_attacks_by_folder_and_model_suffix(self):
        for attack in ["injecagent", "tool_knowledge"]:
            data = summary("workspace", 0.5, 0.25, 0.75)
            data["task_selection"] = {"attack": attack}
            write_json(self.results_root / "partial_benchmark/model_baseline" / attack / "workspace/summary.json", data)
        with patch("dashboard.app.RESULTS_DIR", self.results_root):
            catalog = self.client.get("/api/history/catalog").get_json()
            nested = [item for item in catalog if item["source"].startswith("partial_benchmark/model_baseline/")]
            self.assertEqual(len(nested), 2)
            self.assertEqual({item["attack_name"] for item in nested}, {"injecagent", "tool_knowledge"})
            for item in nested:
                self.assertEqual(item["result_folder"], "partial_benchmark")
                self.assertEqual(item["model_suffix"], "model_baseline")
                self.assertEqual(item["model_group"], "model_baseline")
            selected = next(item for item in nested if item["attack_name"] == "injecagent")
            result = self.client.post("/api/history/analyze", json={"run_ids": [selected["id"]]}).get_json()
            self.assertEqual(result["experiments"][0]["attack_name"], "injecagent")
            self.assertEqual(result["experiments"][0]["model_suffix"], "model_baseline")
        archive, exported = self.read_export(self.export_results([selected["source"]]))
        self.assertEqual(exported["experiments"][0]["attack_name"], "injecagent")
        rows = list(csv.DictReader(io.StringIO(archive.read("summary.csv").decode("utf-8-sig"))))
        self.assertEqual(rows[0]["result_folder"], "partial_benchmark")
        self.assertEqual(rows[0]["model_suffix"], "model_baseline")
        self.assertEqual(rows[0]["attack_name"], "injecagent")

    def test_disabled_attack_config_takes_precedence_over_retained_attack_name(self):
        write_json(self.results_root / "dashboard/benign/overall_results.json", {
            "config": {"run_attack": False, "attack_name": "important_instructions"},
            "suites": [summary("workspace", 100, 0, 100)],
        })
        with patch("dashboard.app.RESULTS_DIR", self.results_root):
            catalog = self.client.get("/api/history/catalog").get_json()
        benign = next(item for item in catalog if item["source"] == "dashboard/benign")
        self.assertEqual(benign["attack_name"], "none")
        self.assertEqual(benign["attack_names"], ["none"])

    def test_legacy_attack_metadata_is_read_without_guessing_missing_or_mixed_attacks(self):
        path = self.results_root / "partial_benchmark/trial-p04/workspace/detailed_results.csv"
        with path.open() as stream:
            rows = list(csv.DictReader(stream))
        with path.open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=[*rows[0], "attack_type"])
            writer.writeheader()
            writer.writerow({**rows[0], "attack_type": "important_instructions"})
        write_json(self.results_root / "benchmarks/ablation_study/model__injecagent/workspace/summary.json",
                   {**summary("workspace", 0.5, 0.5, 0.5), "task_selection": {"attack": "injecagent"}})
        write_json(self.results_root / "benchmark/model/workspace/summary.json", summary("workspace", 0.5, 0.5, 0.5))
        write_json(self.results_root / "dashboard/mixed/overall_results.json", {
            "suites": [summary("workspace", 50, 50, 50)],
            "structured_records": [
                {"suite_name": "workspace", "attack_type": attack} for attack in ["injecagent", "tool_knowledge"]
            ],
        })
        with patch("dashboard.app.RESULTS_DIR", self.results_root):
            by_source = {item["source"]: item for item in self.client.get("/api/history/catalog").get_json()}
        self.assertEqual(by_source["partial_benchmark/trial-p04"]["attack_name"], "important_instructions")
        legacy = by_source["benchmarks/ablation_study/model__injecagent"]
        self.assertEqual(legacy["model_group"], "ablation_study/model")
        self.assertEqual(legacy["model_suffix"], "model")
        self.assertEqual(by_source["benchmark/model"]["result_folder"], "benchmark")
        self.assertEqual(by_source["benchmark/model"]["attack_name"], "unknown")
        self.assertEqual(by_source["dashboard/mixed"]["attack_name"], "mixed")

    def test_analyze_loads_task_records_only_for_selected_results(self):
        with patch("dashboard.app.RESULTS_DIR", self.results_root):
            catalog = self.client.get("/api/history/catalog").get_json()
            partial = next(item for item in catalog if item["source"] == "partial_benchmark/trial-p04")
            response = self.client.post(
                "/api/history/analyze",
                json={
                    "run_ids": [partial["id"]],
                    "suites": ["workspace"],
                    "include_task_records": True,
                },
            )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()["experiments"][0]["suites"][0]
        self.assertEqual(data["task_records"][0]["utility_success"], True)

    def test_analysis_rejects_unmapped_ids_and_invalid_suites(self):
        with patch("dashboard.app.RESULTS_DIR", self.results_root):
            unknown = self.client.post(
                "/api/history/analyze", json={"run_ids": ["../../outside"], "suites": []}
            )
            invalid_suite = self.client.post(
                "/api/history/analyze",
                json={"run_ids": ["unknown"], "suites": ["../../outside"]},
            )
        self.assertEqual(unknown.status_code, 404)
        self.assertEqual(invalid_suite.status_code, 400)

    def export_results(self, sources, suites=None):
        with patch("dashboard.app.RESULTS_DIR", self.results_root):
            catalog = self.client.get("/api/history/catalog").get_json()
            by_source = {item["source"]: item["id"] for item in catalog}
            return self.client.post("/api/history/export", json={
                "run_ids": [by_source[source] for source in sources],
                "suites": suites or [],
            })

    def read_export(self, response):
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/zip")
        self.assertIn("attachment;", response.headers["Content-Disposition"])
        archive = zipfile.ZipFile(io.BytesIO(response.data))
        return archive, json.loads(archive.read("analysis.json"))

    def test_export_contains_selected_comparison_metrics_and_task_records(self):
        response = self.export_results([
            "partial_benchmark/trial-p04", "dashboard/run-001",
        ])
        archive, data = self.read_export(response)
        self.assertEqual(set(archive.namelist()), {
            "analysis.json", "summary.csv", "task_records.csv", "README.md",
        })
        self.assertEqual(data["schema_version"], 2)
        self.assertEqual([run["source"] for run in data["experiments"]], [
            "partial_benchmark/trial-p04", "dashboard/run-001",
        ])
        partial = data["experiments"][0]["suites"][0]
        self.assertEqual(partial["metrics"]["utility_rate"], 50.0)
        self.assertEqual(partial["metrics"]["attack_success_rate"], 25.0)
        self.assertEqual(partial["record_statistics"]["tsr"]["denominator"], 1)
        self.assertEqual(partial["record_statistics"]["asr"]["numerator"], 0)
        self.assertEqual(partial["task_records"][0]["user_task_id"], "user_task_0")
        self.assertEqual(data["counts"], {"experiments": 2, "suites": 3, "task_records": 2})
        for name in archive.namelist():
            self.assertNotIn(b"must-not-leak", archive.read(name))
            self.assertNotIn(b"api_key", archive.read(name))

    def test_export_respects_suite_filter_and_csv_rates_use_percent_units(self):
        archive, data = self.read_export(self.export_results(
            ["dashboard/run-001"], ["travel"],
        ))
        self.assertEqual(data["selection"]["suites"], ["travel"])
        self.assertEqual([s["suite_name"] for s in data["experiments"][0]["suites"]], ["travel"])
        rows = list(csv.DictReader(io.StringIO(archive.read("summary.csv").decode("utf-8-sig"))))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["tsr_percent"], "100.0")
        self.assertEqual(rows[0]["asr_percent"], "20.0")
        records = list(csv.DictReader(io.StringIO(archive.read("task_records.csv").decode("utf-8-sig"))))
        self.assertEqual(records[0]["attack_success"], "True")

    def test_export_keeps_missing_and_error_results_out_of_observed_denominators(self):
        path = self.results_root / "dashboard" / "errors" / "overall_results.json"
        write_json(path, {
            "suites": [summary("travel", None, None, None)],
            "structured_records": [
                {"suite_name": "travel", "user_task_id": "ok", "sample_status": "valid",
                 "utility_success": True, "attack_success": False, "model_id": "demo",
                 "attack_type": "important_instructions"},
                {"suite_name": "travel", "user_task_id": "error", "sample_status": "infrastructure_error",
                 "utility_success": False, "attack_success": None},
                {"suite_name": "travel", "user_task_id": "missing"},
            ],
        })
        archive, data = self.read_export(self.export_results(["dashboard/errors"]))
        suite = data["experiments"][0]["suites"][0]
        self.assertIsNone(suite["metrics"]["attack_success_rate"])
        self.assertEqual(suite["record_statistics"]["tsr"], {
            "numerator": 1, "denominator": 1, "percent": 100.0,
        })
        self.assertEqual(suite["record_statistics"]["asr"], {
            "numerator": 0, "denominator": 1, "percent": 0.0,
        })
        self.assertEqual(suite["record_statistics"]["sample_status_counts"], {
            "valid": 1, "infrastructure_error": 1, "unknown": 1,
        })
        self.assertEqual(suite["task_records"][0]["model_id"], "demo")
        self.assertIsNone(suite["task_records"][1]["attack_success"])
        rows = list(csv.DictReader(io.StringIO(archive.read("summary.csv").decode("utf-8-sig"))))
        self.assertEqual(rows[0]["asr_percent"], "")

    def test_export_marks_every_suite_affected_by_global_record_limit(self):
        with patch("dashboard.app.MAX_HISTORY_TASK_RECORDS", 1):
            _, data = self.read_export(self.export_results([
                "partial_benchmark/trial-p04", "dashboard/run-001",
            ]))
        suites = data["experiments"][1]["suites"]
        travel = next(item for item in suites if item["suite_name"] == "travel")
        slack = next(item for item in suites if item["suite_name"] == "slack")
        self.assertEqual(travel["task_records"], [])
        self.assertTrue(travel["task_records_truncated"])
        self.assertIsNone(travel["record_statistics"]["asr"]["percent"])
        self.assertTrue(travel["warnings"])
        self.assertFalse(slack["task_records_truncated"])
        self.assertTrue(slack["warnings"])

    def test_export_excludes_policy_errors_and_timeouts_even_with_boolean_outcomes(self):
        write_json(self.results_root / "dashboard" / "errors" / "overall_results.json", {
            "suites": [summary("travel", 0, 0, 100)],
            "structured_records": [
                {"suite_name": "travel", "sample_status": status,
                 "utility_success": False, "attack_success": False}
                for status in ("policy_error", "timeout")
            ],
        })
        _, data = self.read_export(self.export_results(["dashboard/errors"]))
        stats = data["experiments"][0]["suites"][0]["record_statistics"]
        self.assertEqual(stats["sample_status_counts"], {"policy_error": 1, "timeout": 1})
        self.assertEqual(stats["asr"], {"numerator": 0, "denominator": 0, "percent": None})
        self.assertEqual(stats["tsr"]["denominator"], 0)

    def test_export_reads_csv_only_experiments_and_flags_legacy_status(self):
        _, data = self.read_export(self.export_results(["partial_benchmark/csv-only"]))
        suite = data["experiments"][0]["suites"][0]
        self.assertEqual(suite["metrics"]["attack_success_rate"], 50.0)
        self.assertEqual(suite["record_statistics"]["asr"]["denominator"], 2)
        self.assertEqual(suite["record_statistics"]["sample_status_counts"], {"unknown": 2})
        self.assertTrue(suite["warnings"])

    def test_export_rejects_invalid_or_disappeared_selections(self):
        cases = [
            (None, 400), ({}, 400), ({"run_ids": []}, 400),
            ({"run_ids": [False]}, 400), ({"run_ids": ["x"] * 101}, 400),
            ({"run_ids": ["../../outside"]}, 404),
            ({"run_ids": ["x"], "suites": ["../../outside"]}, 400),
        ]
        with patch("dashboard.app.RESULTS_DIR", self.results_root):
            for payload, expected in cases:
                with self.subTest(payload=payload):
                    response = self.client.post("/api/history/export", json=payload)
                    self.assertEqual(response.status_code, expected)
                    self.assertIsInstance(response.get_json(), dict)
                    self.assertIn("error", response.get_json())

    def test_export_deduplicates_selection_and_rejects_empty_suite_match(self):
        _, data = self.read_export(self.export_results([
            "partial_benchmark/trial-p04", "partial_benchmark/trial-p04",
        ]))
        self.assertEqual(len(data["experiments"]), 1)
        response = self.export_results(["partial_benchmark/trial-p04"], ["banking"])
        self.assertEqual(response.status_code, 400)

    def test_export_csv_neutralizes_formula_labels_without_changing_json(self):
        path = self.results_root / "dashboard" / "run-001" / "overall_results.json"
        content = json.loads(path.read_text())
        content["config"]["label"] = '=HYPERLINK("https://example.com")'
        write_json(path, content)
        archive, data = self.read_export(self.export_results(["dashboard/run-001"]))
        self.assertEqual(data["experiments"][0]["label"], '=HYPERLINK("https://example.com")')
        rows = list(csv.DictReader(io.StringIO(archive.read("summary.csv").decode("utf-8-sig"))))
        self.assertTrue(rows[0]["label"].startswith("'="))


if __name__ == "__main__":
    unittest.main()
