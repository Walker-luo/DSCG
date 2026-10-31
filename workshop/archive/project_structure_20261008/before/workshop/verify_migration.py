"""Read-only validation of workshop relocation and compatibility paths."""

import ast
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent
WORKSHOP = ROOT / "workshop"
OUT = WORKSHOP / "results/materials_migration_20261008"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def local_links(path, text=None):
    for label, target in re.findall(r"\[([^\]]+)\]\(([^)]+)\)", text if text is not None else path.read_text()):
        if target.startswith(("https://", "http://", "#", "app://", "codex://")):
            continue
        yield label, target, (path.parent / target.split("#", 1)[0]).resolve()


def main():
    manifest = json.loads((OUT / "migration_manifest.json").read_text())
    entries = manifest["entries"]
    assert len(entries) == manifest["document_count"] + manifest["artifact_count"] == 293
    assert len({e["new_path"] for e in entries}) == len(entries)
    checked_links, old_missing, roots_checked, python_files = [], [], [], []
    for entry in entries:
        new = ROOT / entry["new_path"]
        old = PROJECT / entry["legacy_read_path"]
        original = ROOT / entry["original_storage"]
        assert new.is_file() and not new.is_symlink(), new
        assert new.resolve().is_relative_to(WORKSHOP), new
        assert original.resolve().is_relative_to(WORKSHOP), original
        assert sha(new) == entry["sha256_after"], new
        assert sha(original) == entry["sha256_before"], original
        assert old.is_file() and sha(old) == entry["sha256_before"], old
        assert not entry["old_path"].startswith(("DSCG/results/", "DSCG/download/"))
        if entry["kind"] == "document":
            assert old.is_symlink(), old
            if new.suffix == ".md":
                previous = {(label, target) for label, target, dest in local_links(old, original.read_text()) if not dest.exists()}
                for label, target, dest in local_links(new):
                    if not dest.exists() and (label, target) in previous:
                        old_missing.append({"document": entry["new_path"], "target": target})
                    else:
                        assert dest.exists(), (new, target)
                        checked_links.append({"document": entry["new_path"], "target": str(dest)})
        if entry["kind"] == "artifact" and new.suffix == ".py":
            source = new.read_text()
            ast.parse(source, filename=str(new))
            python_files.append(str(new.relative_to(ROOT)))
            if "__file__" in source and "parents[4]" in source:
                assert new.resolve().parents[4] == ROOT, new
                roots_checked.append(str(new.relative_to(ROOT)))
    alias = ROOT / manifest["compatibility_directory"]["old"]
    assert alias.is_symlink() and alias.resolve() == ROOT / manifest["compatibility_directory"]["new"]
    for path in [ROOT / "README.md", WORKSHOP / "README.md"]:
        for _, target, dest in local_links(path):
            assert dest.exists(), (path, target)
            checked_links.append({"document": str(path.relative_to(ROOT)), "target": str(dest)})
    for _, target, dest in local_links(ROOT / "AGENTS.md"):
        assert dest.exists(), target
    assert sha(ROOT / "dscg/pipelines/defended.py") == manifest["runtime_sha256"]
    assert sha(PROJECT / "research/technical_route.md") == manifest["research_route_sha256"]
    runtime_changes = subprocess.check_output([
        "git", "-C", str(ROOT), "diff", "--name-only", manifest["dscg_base_revision"],
        "--", "dscg", "tests", "experiments", "dashboard", "config"], text=True)
    assert not runtime_changes.strip(), runtime_changes
    assert not (ROOT / "System_TODO.md").exists(), "Restore of user's deletion is outside scope"
    catalog = json.loads((WORKSHOP / "3_layer_sources_20261008.json").read_text())
    doc = (WORKSHOP / "3_layer_opt.md").read_text()
    refs = dict(re.findall(r"^\[([^\]]+)\]: (https://\S+)$", doc, re.M))
    assert {s["id"]: s["primary_url"] for s in catalog["sources"]} == refs
    result = {
        "status": "pass", "scope": "workshop material relocation, not benchmark efficacy",
        "document_count": manifest["document_count"], "artifact_count": manifest["artifact_count"],
        "moved_file_hashes_checked": len(entries), "original_bytes_and_legacy_hashes_checked": len(entries),
        "historical_documents_archived": manifest["historical_documents_archived_before_link_edits"],
        "local_links_checked": len(checked_links), "preexisting_missing_document_links": old_missing,
        "python_artifact_syntax_checked": len(python_files), "script_root_depths_checked": len(roots_checked),
        "runtime_changed": False, "research_route_changed": False, "raw_result_roots_moved": 0,
        "new_model_calls": 0, "new_benchmark_samples": 0,
        "runtime_sha256": manifest["runtime_sha256"],
        "migration_manifest_sha256": sha(OUT / "migration_manifest.json"),
        "verifier_sha256": sha(Path(__file__)),
        "checked_links": checked_links, "root_depth_scripts": roots_checked,
        "limitations": [
            "Original evidence includes previously missing input files; relocation does not reconstruct or certify them.",
            "Historical diagnostic scripts may require their recorded code revision or candidate patch; only syntax and root depth are checked here.",
            "Old compatibility paths read original document bytes; current readers should use workshop/README.md.",
            "No model/benchmark was run and no security/research gate status changed."
        ],
    }
    (OUT / "validation.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({key: value for key, value in result.items() if key in {
        "status", "document_count", "artifact_count", "moved_file_hashes_checked",
        "historical_documents_archived", "local_links_checked", "python_artifact_syntax_checked",
        "script_root_depths_checked", "runtime_changed", "raw_result_roots_moved"}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
