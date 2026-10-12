import unittest
import queue
from unittest.mock import patch

from dashboard.app import (
    app,
    _redact_run_config,
    push_log,
    run_queues,
    run_secrets,
    runs_store,
)


class DashboardConfigTests(unittest.TestCase):
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
                    "suites": ["workspace"],
                },
            )

        self.assertEqual(response.status_code, 200)
        run_id = response.get_json()["run_id"]
        stored = runs_store[run_id]["config"]
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
        response = app.test_client().post("/api/run", json={"suites": ["workspace"], "input_isolation": "false"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(runs_store, {})

    def test_layer_config_is_normalized_before_worker_and_public_storage(self):
        with patch("dashboard.app.threading.Thread"):
            response = app.test_client().post("/api/run", json={"suites": ["workspace"], "use_sandbox": False})
        config = runs_store[response.get_json()["run_id"]]["config"]
        self.assertFalse(config["authorization_precheck"])
        self.assertTrue(config["input_isolation"])


if __name__ == "__main__":
    unittest.main()
