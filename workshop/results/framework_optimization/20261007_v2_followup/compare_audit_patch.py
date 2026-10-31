"""Paired final-runtime versus native baseline, using saved matched controls."""
import hashlib
import json
from pathlib import Path

directory = Path(__file__).parent
source = directory / "controls.json"
groups = json.loads(source.read_text())["groups"]
result = {"source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(), "comparisons": {}}
for mode in ("clean", "ii"):
    old, new = groups["baseline"][mode], groups["audit_only_patch"][mode]
    old_rows = {tuple(row["key"]): row for row in old["rows"]}
    new_rows = {tuple(row["key"]): row for row in new["rows"]}
    assert set(old_rows) == set(new_rows)
    result["comparisons"][mode] = {
        "baseline_TSR": old["TSR"], "current_TSR": new["TSR"],
        "baseline_ASR": old["ASR"], "current_ASR": new["ASR"], "target_count": new["target_count"],
        "gains": [list(key) for key in old_rows if not old_rows[key]["utility"] and new_rows[key]["utility"]],
        "losses": [list(key) for key in old_rows if old_rows[key]["utility"] and not new_rows[key]["utility"]],
        "token_change_percent": round((new["total_tokens"] / old["total_tokens"] - 1) * 100, 2),
    }
(directory / "audit_patch_comparison.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
