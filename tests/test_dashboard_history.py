import csv
import json
import tempfile
import unittest
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


if __name__ == "__main__":
    unittest.main()
