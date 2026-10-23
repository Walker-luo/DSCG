"""Verify a portable export against two existing smoke runs; never rerun models."""

import io
import json
import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))

from dashboard.app import app  # noqa: E402

OUTPUT = Path(__file__).resolve().parent
client = app.test_client()
catalog = client.get("/api/history/catalog").get_json()
sources = [
    "partial_benchmark/deepseek-flash_workshop_2.0",
    "partial_benchmark/deepseek-flash_workshop_1.1",
]
by_source = {run["source"]: run["id"] for run in catalog}
response = client.post("/api/history/export", json={
    "run_ids": [by_source[source] for source in sources], "suites": ["workspace"],
})
assert response.status_code == 200, response.get_json()
assert response.mimetype == "application/zip"
assert "attachment;" in response.headers["Content-Disposition"]
with zipfile.ZipFile(io.BytesIO(response.data)) as archive:
    assert archive.testzip() is None
    assert set(archive.namelist()) == {"analysis.json", "summary.csv", "task_records.csv", "README.md"}
    data = json.loads(archive.read("analysis.json"))
    assert data["counts"] == {"experiments": 2, "suites": 2, "task_records": 8}
    assert [run["source"] for run in data["experiments"]] == sources
    for run, expected_tsr in zip(data["experiments"], [75.0, 100.0]):
        suite = run["suites"][0]
        assert suite["suite_name"] == "workspace"
        assert suite["metrics"]["utility_rate"] == expected_tsr
        assert suite["metrics"]["attack_success_rate"] == 0.0
        assert suite["record_statistics"]["asr"]["denominator"] == 4
        assert not suite["task_records_truncated"]

# Exclusive creation protects all previously recorded evidence.
with (OUTPUT / "comparison.zip").open("xb") as output_file:
    output_file.write(response.data)
with (OUTPUT / "analysis.json").open("x", encoding="utf-8") as output_file:
    json.dump(data, output_file, ensure_ascii=False, indent=2)
print(json.dumps({"status": "pass", "http_status": 200, **data["counts"], "scope": "existing smoke outcomes; no new benchmark"}))
