import unittest
import queue
from unittest.mock import patch
from types import SimpleNamespace

from dashboard.app import (
    app,
    _redact_run_config,
    push_log,
    run_queues,
    run_secrets,
    runs_store,
    run_test_thread,
)


IDENTITY = {"id": "agentdyn", "repository": "https://github.com/AgentDyn/AgentDyn",
            "revision": "test-revision", "suite_version": "v1.2",
            "implementation_sha256": "a" * 64, "catalog_sha256": "b" * 64}


def profile(identity=IDENTITY, suites=("shopping", "github", "dailylife")):
    return SimpleNamespace(id=identity["id"], label="AgentDyn" if identity["id"] == "agentdyn" else "AgentDojo",
                           suites=suites, suite_version="v1.2", repository=identity["repository"],
                           lock_path="config/mock.lock.json", tool_metadata_path=f"config/tools.{identity['id']}-v1.2.toml")


class DashboardConfigTests(unittest.TestCase):
    def setUp(self):
        for target, value in (("dashboard.app.get_backend", profile()),
                              ("dashboard.evaluation.get_suites", profile().suites)):
            mocker = patch(target, return_value=value, create=True)
            mocker.start()
            self.addCleanup(mocker.stop)
        metadata = patch("dashboard.app.resolve_tool_metadata", side_effect=lambda backend: SimpleNamespace(
            public_dict=lambda: {"path": str(backend.tool_metadata_path), "source": "builtin", "backend_id": backend.id,
                                 "catalog_backend_id": backend.id, "skipped_generic_path": None, "warning": None}), create=True)
        metadata.start()
        self.addCleanup(metadata.stop)
        self.backend = patch("dashboard.app.validate_backend", return_value=IDENTITY, create=True)
        self.backend.start()
        self.addCleanup(self.backend.stop)

    def test_backend_failure_rejects_execution_without_starting_a_worker(self):
        with patch("dashboard.app.validate_backend", side_effect=ValueError("AgentDyn fork missing"), create=True), \
             patch("dashboard.app.threading.Thread") as worker:
            response = app.test_client().post("/api/run", json={"suites": ["shopping"]})
        self.assertEqual(response.status_code, 400)
        self.assertIn("AgentDyn fork missing", response.get_json()["error"])
        worker.assert_not_called()
        self.assertEqual(runs_store, {})

    def test_worker_checks_backend_before_constructing_any_model(self):
        with patch("dashboard.app.validate_backend", side_effect=ValueError("changed backend")), \
             patch("dashboard.app.make_defended_pipeline") as defended, \
             patch("dashboard.app.make_openai_compatible_pipeline") as baseline, \
             patch("dashboard.app.threading.Thread"):
            run_test_thread("backend-worker-test", {"suites": ["shopping"]})
        defended.assert_not_called()
        baseline.assert_not_called()

    def test_comparison_rejects_cross_benchmark_and_catalog_pairing(self):
        suite = {"suite_name": "shopping", "task_counts": {}, "metrics": {},
                 "task_selection": {"user_task_ids": ["u1"], "injection_task_ids": ["i1"]}}
        for run_id, identity in (("run-a", IDENTITY), ("run-b", {**IDENTITY, "catalog_sha256": "other"})):
            runs_store[run_id] = {"run_id": run_id, "config": {"benchmark": identity}, "suites": [suite]}
        response = app.test_client().post("/api/compare", json={"run_ids": ["run-a", "run-b"]})
        self.assertEqual(response.status_code, 400)
        self.assertIn("benchmark_or_catalog_mismatch", response.get_json()["comparison_warnings"])

    def test_backend_absence_keeps_config_and_history_available(self):
        with patch("dashboard.app.suite_catalog", side_effect=ValueError("Install the AgentDyn fork"), create=True):
            client = app.test_client()
            response = client.get("/api/config")
            self.assertEqual(response.status_code, 200)
            self.assertFalse(response.get_json()["backend_ready"])
            self.assertEqual(response.get_json()["suites"], [])
            self.assertIn("Install", response.get_json()["backend_error"])
            self.assertEqual(client.get("/history").status_code, 200)

    def test_config_uses_real_catalog_counts(self):
        catalog = [{"id": "shopping", "label": "Shopping", "user_tasks": 7, "injection_tasks": 2}]
        with patch("dashboard.app.suite_catalog", return_value=catalog, create=True):
            data = app.test_client().get("/api/config").get_json()
        self.assertEqual(data["suites"], catalog)
        self.assertEqual(data["benchmark"], IDENTITY)
        self.assertTrue(data["backend_ready"])

    def test_new_execution_rejects_inactive_suites(self):
        with patch("dashboard.app.threading.Thread") as worker:
            response = app.test_client().post("/api/run", json={"suites": ["workspace"]})
        self.assertEqual(response.status_code, 400)
        worker.assert_not_called()

    def test_environment_profile_controls_catalog_label_risk_path_and_new_run_namespace(self):
        for backend_id, suites in (("agentdojo", ("workspace", "travel", "banking", "slack")),
                                  ("agentdyn", ("shopping", "github", "dailylife"))):
            identity = {**IDENTITY, "id": backend_id}
            active = profile(identity, suites)
            catalog = [{"id": name, "label": name.title(), "user_tasks": 7, "injection_tasks": 2} for name in suites]
            with self.subTest(backend=backend_id), \
                 patch("dashboard.app.get_backend", return_value=active, create=True), \
                 patch("dashboard.evaluation.get_suites", return_value=suites, create=True), \
                 patch("dashboard.app.suite_catalog", return_value=catalog), \
                 patch("dashboard.app.validate_backend", return_value=identity), \
                 patch("dashboard.app.threading.Thread"):
                response = app.test_client().get("/api/config")
                config = response.get_json()
                self.assertEqual(config["benchmark_id"], backend_id)
                self.assertEqual(config["benchmark_label"], active.label)
                self.assertEqual(config["tool_metadata_path"], active.tool_metadata_path)
                self.assertEqual(config["suites"], catalog)
                started = app.test_client().post("/api/run", json={"suites": [suites[0]]})
                self.assertEqual(started.status_code, 200)
                self.assertTrue(started.get_json()["run_id"].startswith(backend_id + "_"))

    def test_config_reports_effective_metadata_selection_and_skipped_generic_warning(self):
        catalog = [{"id": "shopping", "label": "Shopping", "user_tasks": 7, "injection_tasks": 2}]
        selection = {"path": "config/tools.agentdyn-v1.2.toml", "source": "builtin", "backend_id": "agentdyn",
                     "catalog_backend_id": "agentdyn", "skipped_generic_path": "config/tools.local.toml", "warning": "Skipping opposite catalog"}
        with patch("dashboard.app.resolve_tool_metadata", return_value=SimpleNamespace(
                 path=selection["path"], public_dict=lambda: selection), create=True), \
             patch("dashboard.app.suite_catalog", return_value=catalog):
            config = app.test_client().get("/api/config").get_json()
        self.assertEqual(config["tool_metadata_selection"], selection)
        self.assertIsNone(config["tool_metadata_error"])

    def test_unknown_backend_keeps_history_and_config_available(self):
        with patch("dashboard.app.get_backend", side_effect=ValueError("unrecognized installation"), create=True):
            client = app.test_client()
            config = client.get("/api/config").get_json()
            self.assertFalse(config["backend_ready"])
            self.assertEqual(config["benchmark_id"], "unknown")
            self.assertEqual(config["suites"], [])
            self.assertIsNone(config["tool_metadata_path"])
            self.assertEqual(client.get("/history").status_code, 200)

    def tearDown(self):
        for run_id in list(runs_store):
            runs_store.pop(run_id, None)
        for run_id in list(run_queues):
            run_queues.pop(run_id, None)
        for run_id in list(run_secrets):
            run_secrets.pop(run_id, None)

    def test_redaction_removes_raw_credentials_from_public_config(self):
        safe = _redact_run_config({"api_key": "main-secret", "sec_api_key": "audit-secret"})
        self.assertEqual(safe["api_key"], "[provided]")
        self.assertEqual(safe["sec_api_key"], "[provided]")

    def test_start_run_stores_redacted_config_but_passes_secret_to_worker(self):
        with patch("dashboard.app.threading.Thread") as thread_cls:
            response = app.test_client().post(
                "/api/run",
                json={
                    "api_key": "main-secret",
                    "sec_api_key": "audit-secret",
                    "base_url": "https://gateway.example/v1",
                    "suites": ["shopping"],
                },
            )

        self.assertEqual(response.status_code, 200)
        run_id = response.get_json()["run_id"]
        self.assertTrue(run_id.startswith("agentdyn_"))
        stored = runs_store[run_id]["config"]
        self.assertEqual(stored["benchmark"], IDENTITY)
        self.assertNotEqual(stored["api_key"], "main-secret")
        self.assertNotEqual(stored["sec_api_key"], "audit-secret")
        worker_config = thread_cls.call_args.kwargs["args"][1]
        self.assertEqual(worker_config["api_key"], "main-secret")

    def test_log_redaction_covers_provider_error_messages(self):
        run_id = "dashboard-redaction-test"
        run_queues[run_id] = queue.Queue()
        run_secrets[run_id] = ("main-secret",)
        push_log(run_id, "error", "provider rejected main-secret")
        self.assertNotIn("main-secret", run_queues[run_id].get()["message"])

    def test_invalid_layer_switch_does_not_create_a_run(self):
        response = app.test_client().post("/api/run", json={"suites": ["shopping"], "input_isolation": "false"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(runs_store, {})

    def test_layer_config_is_normalized_before_worker_and_public_storage(self):
        with patch("dashboard.app.threading.Thread"):
            response = app.test_client().post("/api/run", json={"suites": ["shopping"], "use_sandbox": False})
        config = runs_store[response.get_json()["run_id"]]["config"]
        self.assertFalse(config["authorization_precheck"])
        self.assertTrue(config["input_isolation"])

    def test_page_and_config_follow_the_engine_version_instead_of_fixed_labels(self):
        with patch("dashboard.app.FRAMEWORK_VERSION", "future-engine-version", create=True):
            client = app.test_client()
            self.assertEqual(client.get("/api/config").get_json().get("framework_version"), "future-engine-version")
            self.assertIn('data-framework-version="future-engine-version"', client.get("/").get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
