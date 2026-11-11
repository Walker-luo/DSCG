"""Match IDs/payloads and report raw task outcomes plus total model costs."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
DIRECTORY = Path(__file__).parent
names = {
    "baseline": "baseline_v2p1",
    "audit_only_patch": "workshop_v2p1_audit",
    "execution_policy": "workshop_v2p1",
}
inputs = {}
groups = {}
for profile, prefix in names.items():
    groups[profile] = {}
    for mode in ("clean", "ii"):
        directory = ROOT / "results/partial_benchmark" / f"deepseek-flash_{prefix}_{mode}_20261008"
        summaries = list(directory.rglob("summary.json"))
        assert len(summaries) == 4, (profile, mode, "run not complete", len(summaries))
        rows, tokens, preflight = {}, 0, 0
        for path in summaries:
            summary = json.loads(path.read_text())
            tokens += summary["overhead"]["total_tokens"] + summary.get("sec_overhead", {}).get("total_tokens", 0)
            for source in path.parent.rglob("*.json"):
                if not source.name.startswith(("injection_task_", "none")):
                    continue
                trace = json.loads(source.read_text())
                if not trace.get("user_task_id", "").startswith("user_task_"):
                    preflight += 1
                    continue
                assert trace.get("error") is None, (source, trace.get("error"))
                assert isinstance(trace["utility"], bool)
                key = (trace["suite_name"], trace["user_task_id"], trace.get("injection_task_id"))
                assert key not in rows, key
                rows[key] = {"utility": trace["utility"], "security": trace["security"],
                             "payload_sha256": hashlib.sha256(json.dumps(trace["injections"], sort_keys=True).encode()).hexdigest(),
                             "source": str(source.relative_to(ROOT))}
            for source in path.parent.rglob("*"):
                if source.is_file():
                    inputs[str(source.relative_to(ROOT))] = hashlib.sha256(source.read_bytes()).hexdigest()
        assert len(rows) == (12 if mode == "clean" else 36), (profile, mode, len(rows))
        groups[profile][mode] = {"TSR": sum(row["utility"] for row in rows.values()),
                                "ASR": None if mode == "clean" else sum(row["security"] for row in rows.values()),
                                "target_count": len(rows), "extra_preflight_count": preflight,
                                "total_tokens": tokens, "rows": rows}

comparisons = {}
for mode in ("clean", "ii"):
    reference = groups["baseline"][mode]["rows"]
    for profile in names:
        rows = groups[profile][mode]["rows"]
        assert set(rows) == set(reference), (profile, mode, "IDs differ")
        assert all(rows[key]["payload_sha256"] == reference[key]["payload_sha256"] for key in rows), (profile, "payloads differ")
    comparisons[mode] = {}
    for profile in ("baseline", "audit_only_patch"):
        old = groups[profile][mode]
        new = groups["execution_policy"][mode]
        comparisons[mode][profile] = {
            "gains": [list(key) for key in old["rows"] if not old["rows"][key]["utility"] and new["rows"][key]["utility"]],
            "losses": [list(key) for key in old["rows"] if old["rows"][key]["utility"] and not new["rows"][key]["utility"]],
            "token_change_percent": round((new["total_tokens"] / old["total_tokens"] - 1) * 100, 2),
        }
output = {"groups": {profile: {mode: {**{key: value for key, value in group.items() if key != "rows"},
                                      "rows": [{"key": list(key), **value} for key, value in group["rows"].items()]}
                                    for mode, group in modes.items()} for profile, modes in groups.items()},
          "comparisons": comparisons,
          "limitations": ["One current-provider matched run; does not isolate provider revisions or prove repeatability.",
                           "Native ASR retained, including text-predicate warning matches; no independent human oracle.",
                           "Total Tokens include extra preflight; no estimated baseline target-only costs.",
                           "No new object/data enforcement; I3 remains partial."]}
(DIRECTORY / "controls.json").write_text(json.dumps(output, indent=2) + "\n")
(DIRECTORY / "controls_input_sha256.json").write_text(json.dumps(inputs, indent=2) + "\n")
print(json.dumps({"groups": {profile: {mode: {key: value for key, value in group.items() if key != "rows"}
                                       for mode, group in modes.items()} for profile, modes in groups.items()},
                  "comparisons": comparisons}, indent=2))
