"""Verify the current README snapshot without running models or modifying results."""
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[4]
EXPORT = ROOT / "download/dscg-history-analysis-20261007T153203Z"
analysis = json.loads((EXPORT / "analysis.json").read_text())
groups = defaultdict(list)
for experiment in analysis["experiments"]:
    groups[experiment["model_group"]].append(experiment)

expected = {
    "deepseek-flash_baseline": (118, 6, 1735456),
    "deepseek-flash_workshop_new": (111, 6, 2520100),
    "deepseek-flash_workshop_v2": (122, 5, 2077620),
}
assert set(groups) == set(expected)
keys = {}
summary = {}
for group, experiments in groups.items():
    suites = [suite for experiment in experiments for suite in experiment["suites"]]
    rows = [record for suite in suites for record in suite["task_records"]]
    assert len(experiments) == 4 and len(suites) == 16 and len(rows) == 144
    assert Counter(record["sample_status"] for record in rows) == {"valid": 144}
    assert not any(suite["warnings"] for suite in suites)
    utility = sum(record["utility_success"] is True for record in rows)
    attack = sum(record["attack_success"] is True for record in rows)
    tokens = sum(suite["overhead"]["total_tokens"] for suite in suites)
    assert (utility, attack, tokens) == expected[group]
    keys[group] = {
        (suite["suite_name"], record["user_task_id"], record["injection_task_id"],
         record["model_id"], record["attack_type"])
        for suite in suites for record in suite["task_records"]
    }
    assert len(keys[group]) == 144
    summary[group] = {"records": 144, "utility_success": utility,
                      "attack_success": attack, "total_tokens": tokens}
assert all(value == next(iter(keys.values())) for value in keys.values())

readme = (ROOT / "README.md").read_text()
assert readme.count("## 本轮框架优化\n") == 1
assert "## 防御改进\n" not in readme
assert "--completion-prompt" not in readme and "--audit-retries" not in readme
assert "--task-manifest" not in readme
assert "workshop_v2_r2" in readme and "baseline_v2_control_r2" in readme
assert "122/144（84.72%）" in readme and "5/144（3.47%）" in readme
commands = re.findall(r"^python -m experiments\.run_partial_benchmark .*$", readme, re.M)
assert not any("--trace-level full" in command for command in commands)
for name in ("README.md", "AGENTS.md"):
    path = ROOT / name
    text = path.read_text()
    assert text.count("```") % 2 == 0
    for target in re.findall(r"\]\(([^)]+)\)", text):
        if "://" in target or target.startswith("#"):
            continue
        assert (path.parent / target.split("#")[0]).resolve().exists(), (name, target)

historical = {}
archive = ROOT / "examples/results/framework_optimization/20261007_v2_implementation"
for names, base, label in (
    (("stage1_sha256.json", "stage2_sha256.json", "stage3_initial_sha256.json",
      "stage4_sha256.json"), archive, "stage_artifacts"),
    (("controls_input_sha256.json", "final_controls_input_sha256.json"), ROOT,
     "raw_benchmark_inputs"),
):
    checked, missing = 0, []
    for name in names:
        for relative, digest in json.loads((archive / name).read_text()).items():
            path = base / relative
            if not path.exists():
                missing.append(relative)
                continue
            assert hashlib.sha256(path.read_bytes()).hexdigest() == digest, (name, relative)
            checked += 1
    historical[label] = {"checked_hash_entries": checked,
                         "missing_hash_entries": len(missing), "missing_paths": missing}
assert not historical["stage_artifacts"]["missing_paths"]

hashes = {
    str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
    for path in [ROOT / "README.md", ROOT / "AGENTS.md", Path(__file__).resolve(),
                 *sorted(EXPORT.iterdir())]
    if path.is_file()
}
output = {"status": "pass", "scope": "documentation_only",
          "matched_keys_per_run": 144, "exported_records": 432,
          "model_calls": 0, "groups": summary, "sha256": hashes,
          "historical_artifacts": historical}
(Path(__file__).parent / "validation.json").write_text(
    json.dumps(output, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({**output, "historical_artifacts": {
    label: {key: value for key, value in counts.items() if key != "missing_paths"}
    for label, counts in historical.items()
}}, ensure_ascii=False, indent=2))
