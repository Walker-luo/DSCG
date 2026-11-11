"""One-time, fail-on-collision workshop material relocation; no runtime changes."""

import hashlib
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PROJECT = ROOT.parent
RESEARCH = PROJECT / "research"
WORKSHOP = ROOT / "workshop"
OUT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tracked(repo):
    return set(subprocess.check_output(["git", "-C", str(repo), "ls-files"], text=True).splitlines())


def main():
    assert ROOT == Path("/Users/luo/Desktop/AgentDefence/DSCG")
    documents = [
        ROOT / "docs/workshop_optimization_report.md",
        ROOT / "docs/framework_optimization_report.md",
        ROOT / "docs/framework_v2_report.md",
        ROOT / "docs/framework_v2_followup_report.md",
        ROOT / "docs/superpowers/plans/2026-10-05-workshop-engineering-optimization.md",
        *sorted((RESEARCH / "paper").glob("framework_optimization*.md")),
        RESEARCH / "paper/3_layer_opt.md",
        RESEARCH / "paper/3_layer_sources_20261008.json",
    ]
    old_artifacts = ROOT / "examples/results/framework_optimization"
    new_artifacts = WORKSHOP / "results/framework_optimization"
    assert old_artifacts.is_dir() and not old_artifacts.is_symlink()
    assert not new_artifacts.exists()
    for source in documents:
        assert source.is_file() and not source.is_symlink(), source
        assert not (WORKSHOP / source.name).exists(), source
    assert len(documents) == 11
    old_git = {ROOT: tracked(ROOT), RESEARCH: tracked(RESEARCH)}
    entries = []
    for source in sorted(p for p in old_artifacts.rglob("*") if p.is_file()):
        destination = new_artifacts / source.relative_to(old_artifacts)
        entries.append({"old_path": str(source.relative_to(PROJECT)),
                        "new_path": str(destination.relative_to(ROOT)),
                        "sha256_before": sha(source), "sha256_after": sha(source),
                        "legacy_read_path": str(source.relative_to(PROJECT)),
                        "legacy_sha256": sha(source), "original_storage": str(destination.relative_to(ROOT)),
                        "source_tracked": str(source.relative_to(ROOT)) in old_git[ROOT],
                        "source_repository": "DSCG", "kind": "artifact"})
    old_artifacts.rename(new_artifacts)
    old_artifacts.symlink_to(os.path.relpath(new_artifacts, old_artifacts.parent), target_is_directory=True)
    for source in documents:
        repo = ROOT if source.is_relative_to(ROOT) else RESEARCH
        relative = source.relative_to(repo)
        data = source.read_bytes()
        before = hashlib.sha256(data).hexdigest()
        destination = WORKSHOP / source.name
        source.rename(destination)
        if source.name == "3_layer_opt.md":
            text = data.decode().replace("(../technical_route.md)", "(../../research/technical_route.md)")
            text = text.replace("实现与文档分属两个仓库，工程入口见", "按用户的 workshop 归档要求，本优化材料维护于 `DSCG/workshop/`；正式研究路线与工程回报仍在 `research/`。工程入口见")
            destination.write_text(text)
        elif source.name == "workshop_optimization_report.md":
            destination.write_text(data.decode().replace("(./i3_p0_stress_report.md)", "(../docs/i3_p0_stress_report.md)"))
        elif source.name == "framework_v2_followup_report.md":
            destination.write_text(data.decode().replace("(../examples/results/framework_optimization/20261007_v2_followup/)", "(./results/framework_optimization/20261007_v2_followup/)"))
        after = sha(destination)
        original = destination
        if before != after:
            original = WORKSHOP / "archive/original_documents" / repo.name / relative
            original.parent.mkdir(parents=True, exist_ok=True)
            original.write_bytes(data)
        source.symlink_to(os.path.relpath(original, source.parent))
        entries.append({"old_path": str(source.relative_to(PROJECT)),
                        "new_path": str(destination.relative_to(ROOT)),
                        "sha256_before": before, "sha256_after": after,
                        "legacy_read_path": str(source.relative_to(PROJECT)),
                        "legacy_sha256": before, "original_storage": str(original.relative_to(ROOT)),
                        "source_tracked": str(relative) in old_git[repo],
                        "source_repository": repo.name, "kind": "document"})
    for entry in entries:
        assert sha(ROOT / entry["new_path"]) == entry["sha256_after"]
        assert sha(PROJECT / entry["legacy_read_path"]) == entry["sha256_before"]
    payload = {
        "schema_version": 1, "purpose": "User-requested workshop material ownership and relocation, not framework behavior",
        "dscg_base_revision": subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip(),
        "research_base_revision": subprocess.check_output(["git", "-C", str(RESEARCH), "rev-parse", "HEAD"], text=True).strip(),
        "scope": "11 documents/catalog + framework_optimization diagnostic tree; runtime/tests/results/download unchanged",
        "raw_results_policy": "User chose to leave raw benchmark results in results/; download exports also retained.",
        "preexisting_dscg_change_preserved": " D System_TODO.md",
        "runtime_sha256": sha(ROOT / "dscg/pipelines/defended.py"),
        "research_route_sha256": sha(RESEARCH / "technical_route.md"),
        "compatibility_directory": {"old": "examples/results/framework_optimization", "new": "workshop/results/framework_optimization"},
        "document_count": len(documents), "artifact_count": sum(e["kind"] == "artifact" for e in entries),
        "historical_documents_archived_before_link_edits": sum(e["sha256_before"] != e["sha256_after"] for e in entries),
        "entries": entries,
    }
    (OUT / "migration_manifest.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"documents_moved": len(documents), "artifacts_moved": payload["artifact_count"],
                      "historical_originals_hash_preserved": len(entries),
                      "raw_results_moved": 0, "runtime_changed": False}, ensure_ascii=False))


if __name__ == "__main__":
    main()
