"""Read-only validation of workshop relocation and compatibility paths."""

import argparse
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
STRUCTURE_MANIFEST = WORKSHOP / "artifacts/20261008_project_structure/structure_manifest.json"
REORGANIZATION_MANIFEST = WORKSHOP / "artifacts/20261008_workshop_cleanup/relocation_manifest.json"
PRESENTATION_MANIFEST = WORKSHOP / "artifacts/20261008_dashboard_defense_structure/presentation_manifest.json"
PROPOSAL_REVISION_MANIFEST = WORKSHOP / "artifacts/20261008_third_layer_redesign/proposal_revision_manifest.json"
LOW_COST_REVISION_MANIFEST = WORKSHOP / "archive/3_layer_low_cost_20261009/revision_manifest.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def local_links(path, text=None):
    for label, target in re.findall(r"\[([^\]]+)\]\(([^)]+)\)", text if text is not None else path.read_text()):
        if target.startswith(("https://", "http://", "#", "app://", "codex://")):
            continue
        target = target.strip("<>")
        yield label, target, (path.parent / target.split("#", 1)[0]).resolve()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Optional new JSON under workshop/artifacts/; default is read-only.")
    args = parser.parse_args()
    output = args.output.resolve() if args.output else None
    if output and (not output.is_relative_to(WORKSHOP / "artifacts") or output.exists()):
        parser.error("--output must be a new file under workshop/artifacts/; historical reports cannot be overwritten")
    manifest = json.loads((OUT / "migration_manifest.json").read_text())
    cleanup = json.loads(STRUCTURE_MANIFEST.read_text())
    reorganization = json.loads(REORGANIZATION_MANIFEST.read_text())
    proposal_revision = json.loads(PROPOSAL_REVISION_MANIFEST.read_text())
    revised = {entry["path"]: entry for entry in proposal_revision["entries"]}
    low_cost_revision = json.loads(LOW_COST_REVISION_MANIFEST.read_text())
    latest = {entry["path"]: entry for entry in low_cost_revision["entries"]}
    assert set(revised) == {
        "workshop/3_layer_opt.md", "workshop/3_layer_sources_20261008.json",
        "workshop/README.md", "AGENTS.md",
    }
    assert set(latest) == set(revised)
    assert low_cost_revision["previous_manifest_sha256"] == sha(PROPOSAL_REVISION_MANIFEST)
    for name, entry in latest.items():
        original = ROOT / entry["original_storage"]
        assert original.is_file() and not original.is_symlink(), original
        assert original.resolve().is_relative_to(WORKSHOP / "archive"), original
        assert sha(original) == entry["sha256_before"], original
        assert entry["sha256_before"] == revised[name]["sha256_after"], name
        assert sha(ROOT / name) == entry["sha256_after"], name
    for name, entry in revised.items():
        original = ROOT / entry["original_storage"]
        assert original.is_file() and not original.is_symlink(), original
        assert original.resolve().is_relative_to(WORKSHOP / "archive"), original
        assert sha(original) == entry["sha256_before"], original
        # The previous revision remains bound to its own archived result,
        # rather than accepting new bytes by changing a dated manifest.
        assert sha(ROOT / latest[name]["original_storage"]) == entry["sha256_after"], name

    def proposal_snapshot(name):
        # Keep dated migration assertions bound to their recorded bytes.
        return ROOT / (revised[name]["original_storage"] if name in revised else name)

    relocated = {e["old_path"]: e for e in reorganization["entries"]}
    for entry in reorganization["entries"]:
        current = ROOT / entry["new_path"]
        original = ROOT / entry["original_storage"]
        assert current.is_file() and not current.is_symlink(), current
        assert original.is_file() and not original.is_symlink(), original
        assert sha(current) == entry["sha256_after"], current
        assert sha(original) == entry["sha256_before"], original
        assert not (ROOT / entry["old_path"]).exists(), entry["old_path"]
    for entry in reorganization["updated_documents"]:
        assert sha(proposal_snapshot(entry["path"])) == entry["sha256_after"]
        assert sha(ROOT / entry["original_storage"]) == entry["sha256_before"]

    def historical_path(name):
        return (ROOT / relocated[name]["original_storage"]
                if name in relocated else proposal_snapshot(name))

    def current_path(name):
        return ROOT / (relocated[name]["new_path"] if name in relocated else name)

    retired = {e["legacy_read_path"]: e for e in cleanup["retired_aliases"]}
    entries = manifest["entries"]
    assert len(entries) == manifest["document_count"] + manifest["artifact_count"] == 293
    assert len({e["new_path"] for e in entries}) == len(entries)
    checked_links, old_missing, roots_checked, python_files = [], [], [], []
    for entry in entries:
        new = current_path(entry["new_path"])
        old = PROJECT / entry["legacy_read_path"]
        original = historical_path(entry["original_storage"])
        assert new.is_file() and not new.is_symlink(), new
        assert new.resolve().is_relative_to(WORKSHOP), new
        assert original.resolve().is_relative_to(WORKSHOP), original
        assert sha(historical_path(entry["new_path"])) == entry["sha256_after"], new
        assert sha(original) == entry["sha256_before"], original
        if entry["legacy_read_path"] in retired:
            record = retired[entry["legacy_read_path"]]
            assert not old.exists() and not old.is_symlink(), old
            assert record["original_storage"] == entry["original_storage"]
            assert record["sha256_before"] == entry["sha256_before"]
        else:
            assert old.is_file() and sha(old) == entry["sha256_before"], old
        assert not entry["old_path"].startswith(("DSCG/results/", "DSCG/download/"))
        if entry["kind"] == "document":
            assert old.is_symlink() or entry["legacy_read_path"] in retired, old
            if new.suffix == ".md":
                previous = {(label, str(dest)) for label, target, dest in local_links(old, original.read_text()) if not dest.exists()}
                for label, target, dest in local_links(new):
                    if not dest.exists() and (label, str(dest)) in previous:
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
    for path in [ROOT / "README.md", ROOT / "RESEARCH_STATUS.md", WORKSHOP / "README.md",
                 WORKSHOP / "completed/README.md", WORKSHOP / "original_framework_direction_20261008.md",
                 *sorted((ROOT / "docs").rglob("*.md")),
                 WORKSHOP / "archive/project_structure_20261008/README.md"]:
        if path.is_symlink():
            continue  # Original bytes are already checked; archived relative context is not a current guide.
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
    presentation = json.loads(PRESENTATION_MANIFEST.read_text())
    expected_presentation = {
        "dashboard/templates/index.html", "dashboard/templates/_header.html",
        "dashboard/static/css/style.css",
    }
    assert set(presentation["files"]) == expected_presentation
    for name, digest in presentation["files"].items():
        assert sha(ROOT / name) == digest, name
    changed_files = set(runtime_changes.splitlines())
    assert not changed_files - expected_presentation, runtime_changes
    assert not (ROOT / "System_TODO.md").exists(), "Restore of user's deletion is outside scope"
    catalog = json.loads((WORKSHOP / "3_layer_sources_20261008.json").read_text())
    doc = (WORKSHOP / "3_layer_opt.md").read_text()
    refs = dict(re.findall(r"^\[([^\]]+)\]: (https://\S+)$", doc, re.M))
    assert {s["id"]: s["primary_url"] for s in catalog["sources"]} == refs
    assert len(catalog["sources"]) == catalog["primary_paper_count"] == 21
    assert len({s["id"] for s in catalog["sources"]}) == len(catalog["sources"])
    result = {
        "status": "pass", "scope": "workshop material relocation, not benchmark efficacy",
        "document_count": manifest["document_count"], "artifact_count": manifest["artifact_count"],
        "moved_file_hashes_checked": len(entries), "original_bytes_and_legacy_hashes_checked": len(entries),
        "retired_legacy_aliases_checked": len(retired),
        "workshop_materials_reorganized": len(relocated),
        "completed_stage_documents": len([e for e in relocated.values() if e["kind"] == "completed_material"]),
        "reorganization_manifest_sha256": sha(REORGANIZATION_MANIFEST),
        "structure_manifest_sha256": sha(STRUCTURE_MANIFEST),
        "historical_documents_archived": manifest["historical_documents_archived_before_link_edits"],
        "local_links_checked": len(checked_links), "preexisting_missing_document_links": old_missing,
        "python_artifact_syntax_checked": len(python_files), "script_root_depths_checked": len(roots_checked),
        "runtime_changed": False, "research_route_changed": False, "raw_result_roots_moved": 0,
        "dashboard_presentation_changed": bool(changed_files),
        "dashboard_presentation_files": sorted(changed_files),
        "presentation_manifest_sha256": sha(PRESENTATION_MANIFEST),
        "proposal_revision_manifest_sha256": sha(PROPOSAL_REVISION_MANIFEST),
        "low_cost_revision_manifest_sha256": sha(LOW_COST_REVISION_MANIFEST),
        "proposal_revision_links_checked": 2,
        "proposal_revised_files_checked": len(revised),
        "new_model_calls": 0, "new_benchmark_samples": 0,
        "runtime_sha256": manifest["runtime_sha256"],
        "migration_manifest_sha256": sha(OUT / "migration_manifest.json"),
        "verifier_sha256": sha(Path(__file__)),
        "checked_links": checked_links, "root_depth_scripts": roots_checked,
        "limitations": [
            "Original evidence includes previously missing input files; relocation does not reconstruct or certify them.",
            "Historical diagnostic scripts may require their recorded code revision or candidate patch; only syntax and root depth are checked here.",
            "Retained compatibility paths read original bytes; four retired docs aliases are explicitly recorded in the structure manifest.",
            "No model/benchmark was run and no security/research gate status changed."
        ],
    }
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({key: value for key, value in result.items() if key in {
        "status", "document_count", "artifact_count", "moved_file_hashes_checked",
        "historical_documents_archived", "retired_legacy_aliases_checked", "workshop_materials_reorganized", "completed_stage_documents", "local_links_checked", "python_artifact_syntax_checked",
        "script_root_depths_checked", "runtime_changed", "raw_result_roots_moved", "proposal_revised_files_checked"}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
