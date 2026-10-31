"""Rescore immutable probe responses; never rerun a model."""
import hashlib
import json
from pathlib import Path
from agentdojo.functions_runtime import FunctionCall
from evidence_scoring import matches

directory = Path(__file__).parent
groups = []
for phase in ("control", "candidate", "shipped"):
    path = directory / ("executor_" + phase + ".json")
    raw = json.loads(path.read_text())
    rows = []
    for row in raw["rows"]:
        message = {"content": [{"type": "text", "content": row.get("content", "")}],
                   "tool_calls": [FunctionCall(**call) for call in row.get("calls", [])]}
        rows.append({"case": row["case"], "repeat": row["repeat"], "error": row["error"],
                     "original_match": row["match"],
                     "strict_match": not row["error"] and matches(row["case"], message)})
    groups.append({"phase": phase, "source": path.name,
                   "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                   "matches": sum(row["strict_match"] for row in rows),
                   "valid": sum(not row["error"] for row in rows),
                   "errors": sum(bool(row["error"]) for row in rows), "rows": rows})
result = {"groups": groups,
          "scorer_sha256": hashlib.sha256((directory / "evidence_scoring.py").read_bytes()).hexdigest(),
          "limitations": "Recorded-output rescore only; authored next-action checks and string checks for clarification, not native benchmark metrics or semantic guarantees."}
(directory / "executor_rescored.json").write_text(json.dumps(result, indent=2) + "\n")
for group in groups:
    print(group["phase"], group["matches"], group["valid"], group["errors"])
