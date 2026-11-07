"""Read-only checks for the unimplemented authorization audit candidate."""

import argparse
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
TASK = Path(__file__).resolve().parent


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    output = args.output.resolve() if args.output else None
    if output is not None:
        if output.parent != TASK or output.suffix != ".json" or output.exists():
            parser.error("output must be a new JSON in this task's artifact directory")

    protected = json.loads((TASK / "protected_state.json").read_text())
    for name, digest in protected["protected_files"].items():
        assert sha256((ROOT / name).read_bytes()) == digest, name
        committed = subprocess.check_output(["git", "show", f"HEAD:{name}"], cwd=ROOT)
        assert sha256(committed) == digest, name
    assert sha256((ROOT.parent / "research/technical_route.md").read_bytes()) == protected["route_sha256"]
    assert not (ROOT / "System_TODO.md").exists(), "preserve the user's deletion"

    documents = ["README.md", "AGENTS.md", "workshop/README.md",
                 "workshop/original_framework_direction_20261008.md"]
    links = []
    for name in documents:
        path = ROOT / name
        for target in re.findall(r"\]\(([^)]+)\)", path.read_text()):
            if "://" in target or target.startswith("#"):
                continue
            target = target.split("#")[0].strip("<>")
            assert (path.parent / target).exists(), (name, target)
            links.append([name, target])

    sources = json.loads((TASK / "source_screening.json").read_text())
    memo = (ROOT / documents[-1]).read_text()
    for entry in sources["sources"]:
        assert entry["url"] in memo, entry["url"]
    assert "Tony Z. Zhao" not in memo
    assert "Zihao Zhao" in memo

    commands = []
    for command in [["git", "diff", "--check"],
                    ["/opt/miniconda3/envs/ipi/bin/python", "workshop/verify_migration.py"]]:
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
        commands.append({"command": " ".join(command), "exit_code": result.returncode,
                         "output": result.stdout + result.stderr})
        assert result.returncode == 0, commands[-1]

    report = {
        "status": "pass", "recorded_at": datetime.now(timezone.utc).isoformat(),
        "scope": "Documentation and source consistency; no implementation or security gate",
        "command": "/opt/miniconda3/envs/ipi/bin/python "
                   "workshop/artifacts/20261008_authorization_audit_design/verify_design.py"
                   + (f" --output {output.relative_to(ROOT)}" if output else ""),
        "commands": commands, "local_links_checked": len(links),
        "primary_source_entries_checked": len(sources["sources"]),
        "protected_tracked_files_checked": len(protected["protected_files"]),
        "checked_links": links, "new_model_calls": 0, "new_benchmark_samples": 0,
        "planned_cases": 48, "runtime_tests_run": 0, "novelty_gate": "not passed",
        "artifact_sha256": {
            name: sha256((ROOT / name).read_bytes()) for name in documents
        },
    }
    if output:
        with output.open("x") as handle:
            json.dump(report, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
    print(json.dumps({key: value for key, value in report.items()
                      if key not in {"commands", "checked_links", "artifact_sha256"}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
