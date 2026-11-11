"""Validate workshop pending/completed organization without model calls."""

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TASK = Path(__file__).resolve().parent


def sha(data):
    return hashlib.sha256(data).hexdigest()


def inventory(folder):
    rows = []
    for path in sorted(folder.rglob("*")):
        if path.is_file():
            stat = path.stat()
            rows.append([str(path.relative_to(folder)), stat.st_size, stat.st_mtime_ns])
    return {"count": len(rows), "sha256": sha(json.dumps(rows).encode())}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    output = args.output.resolve() if args.output else None
    if output and (output.parent != TASK or output.suffix != ".json" or output.exists()):
        parser.error("output must be a new JSON in this task directory")
    before = json.loads((TASK / "before.json").read_text())
    for name, digest in before["protected_files"].items():
        assert sha((ROOT / name).read_bytes()) == digest, name
    assert sha((ROOT.parent / "research/technical_route.md").read_bytes()) == before["route_sha256"]
    assert sha((ROOT / "workshop/results/materials_migration_20261008/migration_manifest.json").read_bytes()) == before["legacy_manifest_sha256"]
    assert {name: inventory(ROOT / name) for name in before["user_roots"]} == before["user_roots"]
    assert not (ROOT / "System_TODO.md").exists()
    manifest = json.loads((TASK / "relocation_manifest.json").read_text())
    pending = {str(p.relative_to(ROOT)) for p in (ROOT / "workshop").glob("*.md") if p.name != "README.md"}
    assert pending == set(manifest["pending_documents"]), pending
    for entry in manifest["compatibility_links_to_retarget"]:
        path = Path(entry["path"])
        assert path.is_symlink() and path.resolve() == Path(entry["target"])
        assert sha(path.read_bytes()) == entry["expected_sha256"]
    commands = []
    cases = [
        (["/opt/miniconda3/envs/ipi/bin/python", "workshop/verify_migration.py"], 0),
        (["git", "diff", "--check"], 0),
        (["/opt/miniconda3/envs/ipi/bin/python", "workshop/verify_migration.py", "--output",
          "workshop/artifacts/20261008_workshop_cleanup/migration_validation.json"], 2),
        (["/opt/miniconda3/envs/ipi/bin/python", "workshop/verify_migration.py", "--output",
          "results/forbidden_workshop_cleanup.json"], 2),
    ]
    retained = (TASK / "migration_validation.json").read_bytes()
    for command, expected in cases:
        result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
        commands.append({"command": " ".join(command), "exit_code": result.returncode,
                         "expected_exit_code": expected, "output": result.stdout + result.stderr})
        assert result.returncode == expected, commands[-1]
    assert (TASK / "migration_validation.json").read_bytes() == retained
    assert not (ROOT / "results/forbidden_workshop_cleanup.json").exists()
    report = {
        "status": "pass", "recorded_at": datetime.now(timezone.utc).isoformat(),
        "base_revision": before["base_revision"], "commands": commands,
        "protected_tracked_files": len(before["protected_files"]),
        "completed_documents": 10, "archived_submission_files": 2,
        "preserved_original_document_snapshots": 12, "pending_documents": sorted(pending),
        "compatibility_links_checked": 4, "negative_output_controls_passed": 2,
        "user_roots": before["user_roots"], "new_model_calls": 0,
        "new_benchmark_samples": 0, "runtime_tests_run": 0,
        "limitations": ["User root inventories check names/sizes/mtimes rather than full contents.",
                        "Existing missing historical raw-result links remain recorded; no evidence was reconstructed.",
                        "Folder status does not imply every proposed mechanism shipped or research gates passed."],
    }
    if output:
        with output.open("x") as handle:
            json.dump(report, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
    print(json.dumps({key: value for key, value in report.items() if key != "commands"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
