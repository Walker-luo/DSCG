"""Replay this fixture against the recorded P0 revision without moving HEAD."""
import json
from pathlib import Path
import subprocess
import sys
import types
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from experiments import i3_p0_stress

REVISION = "354cdf54ff1190d443ff3859b600c30ddf068c46"
source = subprocess.run(
    ["git", "show", f"{REVISION}:dscg/pipelines/defended.py"],
    cwd=ROOT, check=True, capture_output=True, text=True,
).stdout
previous = types.ModuleType("dscg.pipelines.i3_before_fix")
sys.modules[previous.__name__] = previous
exec(compile(source, f"{REVISION}:dscg/pipelines/defended.py", "exec"), previous.__dict__)
with patch.multiple(i3_p0_stress, **{
    name: getattr(previous, name) for name in (
        "PermissionSandbox", "OurFrameExecutor", "ReferenceMonitor",
        "TicketedToolsExecutor", "ActionSecurityChecker",
    )
}):
    report = i3_p0_stress.audit_i3()
report["p0_revision"] = REVISION
output = Path(__file__).with_name("before_fix.json")
i3_p0_stress.write_report(report, output)
print(json.dumps({"output": str(output), "status": report["status"], "counts": report["counts"]}))
raise SystemExit(2 if report["counts"]["error"] else 0)
