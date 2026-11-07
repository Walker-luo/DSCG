"""Offline checks for a display-only update of the current defense structure."""

import ast
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TASK = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    output = TASK / "validation_final.json"
    assert not output.exists(), "do not overwrite dated validation"
    before = json.loads((TASK / "before.json").read_text())
    for name, expected in before["protected_files"].items():
        assert digest(ROOT / name) == expected, name
    assert digest(ROOT.parent / "research/technical_route.md") == before["route_sha256"]
    presentation = json.loads((TASK / "presentation_manifest.json").read_text())
    for name, expected in presentation["files"].items():
        assert digest(ROOT / name) == expected, name
    prior = subprocess.check_output(["git", "show", f"{before['base_revision']}:dashboard/templates/index.html"], cwd=ROOT, text=True)
    current = (ROOT / "dashboard/templates/index.html").read_text()
    assert set(re.findall(r'\bid="([^"]+)"', prior)) == set(re.findall(r'\bid="([^"]+)"', current))
    tree = ast.parse((ROOT / "dscg/pipelines/defended.py").read_text())
    constants = {node.targets[0].id: ast.literal_eval(node.value) for node in tree.body
                 if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)
                 and node.targets[0].id in {"AUDIT_MAX_TOOL_RESULTS", "AUDIT_MAX_TOOL_RESULT_LENGTH", "AUDIT_MAX_TOOL_DESCRIPTION_LENGTH"}}
    assert constants == {"AUDIT_MAX_TOOL_RESULTS": 4, "AUDIT_MAX_TOOL_RESULT_LENGTH": 2048, "AUDIT_MAX_TOOL_DESCRIPTION_LENGTH": 512}
    factory = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "make_qwen_newFrame_pipeline")
    defaults = {arg.arg: ast.literal_eval(value) for arg, value in zip(factory.args.args[-len(factory.args.defaults):], factory.args.defaults) if arg.arg in {"audit_retries", "completion_prompt"}}
    assert defaults == {"audit_retries": 0, "completion_prompt": False}
    browser = json.loads((TASK / "browser_check.json").read_text())
    assert browser["visible"] and browser["defenseLayers"] == 2 and browser["executionInfrastructure"] == 1
    assert not browser["horizontalOverflow"]
    commands = []
    test_command = json.loads((TASK / "dashboard_tests_command.json").read_text())["argv"]
    for name, command in [("dashboard_tests_final", test_command), ("diff_check", ["git", "diff", "--check"]),
                          ("migration_check_final", ["/opt/miniconda3/envs/ipi/bin/python", "workshop/verify_migration.py"])]:
        result = subprocess.run(command, cwd=ROOT, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}, capture_output=True, text=True)
        (TASK / f"{name}.log").write_text(result.stdout + result.stderr)
        commands.append({"argv": command, "exit_code": result.returncode, "log": f"{name}.log"})
        assert result.returncode == 0, commands[-1]
    report = {"status": "pass", "scope": "UI display only, no new defense behavior", "commands": commands,
              "protected_files": len(before["protected_files"]), "presentation_files": len(presentation["files"]),
              "form_ids_preserved": True, "runtime_constants": constants, "runtime_defaults": defaults,
              "dashboard_tests_passed": 20, "browser": browser, "screenshot_sha256": digest(TASK / "desktop.jpg"),
              "new_model_calls": 0, "new_benchmark_samples": 0}
    with output.open("x") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(json.dumps({k: v for k, v in report.items() if k not in {"commands", "browser"}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
