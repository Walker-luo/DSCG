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
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
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
        self.assertIn(b"/static/js/history.js", response.data)

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
        self.assertEqual(data["schema_version"], 1)
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
