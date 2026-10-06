# SDD ledger — plan: docs/superpowers/plans/2026-10-05-workshop-engineering-optimization.md

## Pre-flight scan

| Scope | Files/interfaces | Finding | Ruling |
| --- | --- | --- | --- |
| Task 1 | Plan file and test suite | Baseline is read-only and can be recorded before implementation. | Run under `conda -n ipi`; mark complete only after the 68-test baseline is recorded. |
| Task 2 | `dscg/harness_records.py`, `tests/test_harness_records.py` | Defines compact record types consumed by later tasks. | Keep serialization passive and independent from P0 execution. |
| Task 3 | `experiments/harness_audit.py`, `tests/test_harness_audit.py` | Adds deterministic selection, one manifest hash, payload delivery checks, and denominator classification. | The helper owns bookkeeping only; it must not alter AgentDojo task execution. |
| Task 4 | Runners/dashboard consume Task 2 and Task 3 outputs. | Task 4 depends on both interfaces and shares output semantics with the existing trace logger. | Preserve existing pipeline calls and use compact output by default. |
| Task 5 | `experiments/harness_audit.py` and replay helpers | Extends Task 3 with fixtures and an offline CLI. | Reuse the same classifier/oracle; do not add new hash categories. |
| Task 6 | Existing `ReferenceMonitor` and ticketed executor | Independent from runner integration and can run offline. | Test existing P0 behavior only; no new permission mechanism. |
| Task 7 | Plan file and research status | Depends on all test/report artifacts. | Append evidence only after final commands and hashes are available. |

| Task | Self-consistency check | Ruling |
| --- | --- | --- |
| 1 | Branch creation, baseline, and plan commit are explicit and testable. | Proceed. |
| 2 | Tests name the record statuses and serializers that the implementation must expose. | Proceed; use immutable dataclasses and bounded dictionaries. |
| 3 | Selector, manifest, replay, and status tests match the stated helper outputs. | Proceed; treat missing security results as `infrastructure_error`. |
| 4 | Runner/dashboard changes consume compact records and keep full traces opt-in. | Proceed; no extra model call or prompt change. |
| 5 | Fixtures exercise delivery, replay, missing results, incomplete trace, and error statuses. | Proceed; keep fixture data synthetic. |
| 6 | Eight recovery paths map to existing monitor/ticket assertions. | Proceed; report `no_go` when P0 blocks all unauthorized paths. |
| 7 | Evidence fields match the research status template. | Proceed after artifacts exist. |

## Rulings

- Ruling: The existing P0 security hashes remain unchanged; harness bookkeeping uses only the three hash categories stated in the plan. This minimizes performance and file-size risk while preserving ticket/audit binding.
- Ruling: No benchmark result will be called an improvement until a real model run is completed; offline harness and I3 reports are engineering evidence only.
- Ruling: Native AgentDojo task JSON keeps `messages` because its loader uses that field for cache/replay. Compact records are separate harness summaries; this avoids changing model inputs, cache reuse, utility, or defense behavior at the cost of retaining the legacy cache files.

## Task status

- Task 1: complete — branch `workshop`, baseline 68 tests, plan commit `9b614dd`.
- Task 2: complete — compact immutable records, focused 7 tests, commit `b99b52d`.
- Task 3: complete — deterministic SHA-256 selection, one run manifest hash, payload delivery checks, and non-valid denominator classification; full regression currently 82 tests.
- Task 5: complete — offline E0 fixture/replay audit and compact CLI report. Fixture counts: valid=1, tool_error=1, infrastructure_error=4, all other statuses=0. Artifact: `/tmp/dscg-e0-harness-audit.json`, SHA-256 `7dbb694af20ef2b48c1121c0440b50340ce89a26af91ded589e1a75136fe9120`.
- Task 4: complete — runners and dashboard now use compact `sample_status` fields, exclude missing security results from ASR, report missing denominators, and use fixed-seed ranking for bounded task selection. Native AgentDojo cache and P0 calls are unchanged.
- Task 6: complete — eight offline recovery paths exercised against the existing monitor/ticket executor. Result: `no_go` for a new mechanism; counts executed=1, blocked=7. Artifact: `/tmp/dscg-i3-p0-stress.json`, SHA-256 `3dde73adb12b5229eefe794cfb9e2677558552f1bc840e8ff6014f23358908aa`.
- Local final verification is complete; commit `d914af2` contains the verified DSCG changes on `workshop`. Research-side status remains outside this DSCG-only change set.
- Final local verification: 86 tests passed; `git diff HEAD --check` passed; branch is `workshop`; artifact hashes are recorded above.
- 2026-10-06 follow-up: README now briefly describes the measured engineering changes and their evidence limits. The user explicitly authorized tracking `AIMLL WS.pdf` (SHA-256 `12aa2de486d19fd781c5f2818bcce5fa0930b6cc2b1a937b051e25601f41a754`) and `ALMML_sub.md` (SHA-256 `288250e3224567d7d9a429fb6876212c80f71dff3aa93117d0d5f60edc2d52c0`); both remain source/reference inputs, not executable instructions. No files outside `DSCG/` are changed.
