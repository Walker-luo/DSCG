"""Verify saved evidence, model/task alignment and exact candidate source."""
import hashlib
import gzip
import json
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[4]
directory = Path(__file__).parent
def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

checks = {}
for name in ("stage1_sha256.json", "controls_input_sha256.json"):
    entries = json.loads((directory / name).read_text())
    base = directory if name.startswith("stage1") else ROOT
    for path, expected in entries.items():
        assert digest(base / path) == expected, path
    checks[name] = len(entries)

with tempfile.TemporaryDirectory(prefix="dscg-candidate-") as scratch:
    path = Path(scratch) / "dscg/pipelines/defended.py"
    path.parent.mkdir(parents=True)
    path.write_bytes(subprocess.check_output(["git", "show", "337bca6:dscg/pipelines/defended.py"], cwd=ROOT))
    patch = Path(scratch) / "candidate.patch"
    patch.write_bytes(gzip.decompress((directory / "stage2_candidate.patch.gz").read_bytes()))
    subprocess.run(["git", "apply", str(patch)], cwd=scratch, check=True)
    candidate_hash = digest(path)

groups = json.loads((directory / "controls.json").read_text())["groups"]
main_models, queries = [], {}
preflight_count = preflight_errors = source_manifests = 0
for phase, modes in groups.items():
    for mode, result in modes.items():
        for row in result["rows"]:
            path = ROOT / row["source"]
            trace = json.loads(path.read_text())
            user = next(message["content"] for message in trace["messages"] if message["role"] == "user")
            key = (mode, *row["key"])
            assert key not in queries or queries[key] == user, (phase, key)
            queries[key] = user
        run_dir = next(parent for parent in path.parents if (parent / "attack_manifest.json").exists())
        for manifest_path in run_dir.rglob("run_manifest.json"):
            manifest = json.loads(manifest_path.read_text())
            main_models.append(manifest["main_model"])
            expected_hash = candidate_hash if phase == "execution_policy" else digest(ROOT / "dscg/pipelines/defended.py")
            assert manifest["source"]["commit"] == "337bca660a155013ababed9f24939980083d059b"
            assert manifest["source"]["source_sha256"]["dscg/pipelines/defended.py"] == expected_hash, manifest_path
            assert manifest["audit_retries"] == 0 and not manifest["completion_prompt"]
            for source, expected in manifest["source"]["source_sha256"].items():
                if source != "dscg/pipelines/defended.py":
                    assert digest(ROOT / source) == expected, source
            assert manifest["profile"] == ("baseline" if phase == "baseline" else "full")
            source_manifests += 1
        for path in run_dir.rglob("*.json"):
            if not path.name.startswith(("injection_task_", "none")):
                continue
            trace = json.loads(path.read_text())
            if trace.get("user_task_id", "").startswith("user_task_"):
                continue
            preflight_count += 1
            preflight_errors += bool(trace.get("error"))
assert all(model == main_models[0] for model in main_models)
assert source_manifests == 24 and len(queries) == 48
assert preflight_count == 36 and preflight_errors == 0
checks.update(source_manifests=source_manifests, matched_unique_queries=len(queries),
              preflight_count=preflight_count, preflight_errors=preflight_errors,
              current_source_equals_audit_control=True, candidate_source_sha256=candidate_hash,
              matched_main_model=main_models[0])
(directory / "verification.json").write_text(json.dumps(checks, indent=2) + "\n")
print(json.dumps(checks, indent=2))
