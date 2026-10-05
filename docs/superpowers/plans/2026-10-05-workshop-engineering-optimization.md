# Workshop Engineering Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve the evaluation harness and recovery stress tests for the AIMLL workshop study while keeping the existing DSCG authorization path, defense rate, utility, and default result-file size stable.

**Architecture:** Add a passive, compact sample-record layer around the existing AgentDojo runners. The default task JSON keeps only identifiers, delivery/predicate status, error category, action counts, and a small final-state summary; full event records remain opt-in in a compressed sidecar. Add an offline I3 fixture that exercises the existing Reference Monitor and one-use tickets without changing the security boundary.

**Tech Stack:** Python 3.10 in conda environment `ipi`, AgentDojo v1.2, `unittest`, YAML/TOML configuration, existing DSCG `ReferenceMonitor`, `ExecutionTicket`, and trace logger.

**Spec:** `ALMML_sub.md` engineering sections E0 and I3, constrained by `../research/technical_route.md` and `../research/paper/implementation_status.md`.

## Global Constraints

- Work only on the `workshop` branch created from `master`.
- Do not implement or unlock I2, field-level provenance, source-to-sink policy, A2, or A3.
- Do not add model calls, prompt transformations, authorization changes, or new permissions for metadata collection.
- Keep existing ticket, audit-input, action-fingerprint, and catalog hashes that are part of the P0 security path; add no per-field or per-event hashes for harness bookkeeping.
- New bookkeeping hashes are limited to one payload hash per sample, one manifest hash per run, and final artifact hashes in the status report.
- Default task JSON must remain compact; complete traces are opt-in and must not be loaded by the dashboard summary path.
- Only `valid` samples enter primary security/utility denominators; every other status is reported separately.
- Research conclusions remain in `../research/`; this repository records only engineering evidence and links to the research status entry.

## Completion Ledger

- [x] Create `workshop` from `master`.
- [ ] Baseline gate recorded on `workshop`.
- [ ] Compact sample-record schema and serializer implemented.
- [ ] Deterministic task selection and passive harness metadata implemented.
- [ ] Benchmark, partial runner, and dashboard consume compact records without changing P0 execution.
- [ ] E0 offline replay/oracle audit passes.
- [ ] I3 P0 recovery stress fixture passes or produces a route-compliant `no_go`.
- [ ] Research implementation status updated with commands, exit codes, commit, working-tree state, artifacts, denominators, limitations, and next action.
- [ ] Final verification passes and all implementation commits are on `workshop`.

### Task 1: Establish the workshop baseline

**Files:**
- Modify: `docs/superpowers/plans/2026-10-05-workshop-engineering-optimization.md`
- Test: `tests/` (read-only baseline)

**Interfaces:**
- Consumes: current `master` implementation and `conda` environment `ipi`.
- Produces: a recorded baseline command and result before code changes.

- [x] **Step 1: Create and verify the branch**

  Run:

  ```bash
  git switch -c workshop master
  git branch --show-current
  ```

  Expected: the current branch is `workshop` and the starting commit is the current `master` HEAD.

- [x] **Step 2: Run the dependency-aware baseline**

  Run:

  ```bash
  conda run -n ipi python -m unittest discover -s tests -q
  ```

  Result: `conda run -n ipi python -m unittest discover -s tests -q` passed 68 tests under Python 3.10.21. The system Python 3.14.6 run was not used because project dependencies were unavailable there.

- [ ] **Step 3: Commit the plan and baseline record**

  Run:

  ```bash
  git add docs/superpowers/plans/2026-10-05-workshop-engineering-optimization.md
  git commit -m "docs: add workshop engineering optimization plan"
  ```

### Task 2: Add compact, typed harness records

**Files:**
- Create: `dscg/harness_records.py`
- Create: `tests/test_harness_records.py`

**Interfaces:**
- Consumes: run identifiers, suite/task identifiers, payload delivery evidence, existing utility/security outputs, and compact action counters.
- Produces: `SampleStatus`, `SampleRecord`, `RunRecord`, `compact_dict()`, and `full_dict()` used by runners and offline replay.

- [ ] **Step 1: Write failing tests for valid and non-valid records**

  Cover accepted statuses `valid`, `model_error`, `policy_error`, `tool_error`, `timeout`, `infrastructure_error`, and `skipped`; reject unknown statuses; preserve missing security results as non-valid instead of `False`.

- [ ] **Step 2: Run the focused tests and verify failure**

  Run:

  ```bash
  conda run -n ipi python -m unittest tests.test_harness_records -v
  ```

  Expected: failure because the record module is not present yet.

- [ ] **Step 3: Implement the minimal compact record model**

  `SampleRecord.compact_dict()` must contain only IDs, `sample_status`, `error_type`, payload delivery status, one `payload_hash`, predicate result, utility result, action counts, and a bounded final-state summary. It must not include raw prompts, complete tool arguments, or complete environment objects.

- [ ] **Step 4: Add explicit opt-in full serialization**

  `SampleRecord.full_dict()` may include bounded candidate/action details but must not add new per-field hashes. The full serializer is only for the existing `full` trace path and is never used by dashboard summary aggregation.

- [ ] **Step 5: Run focused tests and commit**

  Run:

  ```bash
  conda run -n ipi python -m unittest tests.test_harness_records -v
  ```

  Expected: PASS.

  Commit:

  ```bash
  git add dscg/harness_records.py tests/test_harness_records.py
  git commit -m "feat: add compact harness sample records"
  ```

### Task 3: Make selection and replay metadata deterministic

**Files:**
- Create: `experiments/harness_audit.py`
- Modify: `config/paper/protocol.yaml`
- Modify: `config/paper/task_manifest.yaml`
- Create: `tests/test_harness_audit.py`

**Interfaces:**
- Consumes: suite task IDs, fixed seed, attack name, and compact sample records.
- Produces: deterministic SHA-256-ranked task IDs, one run-level manifest hash, payload delivery checks, valid/error denominator counts, and an independent predicate replay result.

- [ ] **Step 1: Write failing selector and denominator tests**

  Verify the same seed and IDs produce the same ordered selection; verify changed IDs change the manifest hash; verify unavailable tasks and attacks are retained with a status; verify a missing security result is never classified as a safe attack result.

- [ ] **Step 2: Run the focused tests and verify failure**

  Run:

  ```bash
  conda run -n ipi python -m unittest tests.test_harness_audit -v
  ```

  Expected: failure before the helper functions exist.

- [ ] **Step 3: Implement deterministic selection and one-time hashes**

  Use the protocol seed and canonical sorted task IDs for selection. Hash the canonical manifest once per run and the delivered payload once per sample. Do not hash each normalized argument, event, or environment field.

- [ ] **Step 4: Implement replay and status classification**

  Replay the attack predicate from the captured final-state summary/oracle input. Return `valid` only when payload delivery, trace reconstruction, predicate replay, and task result are all available; otherwise return the specific error status.

- [ ] **Step 5: Run focused tests and commit**

  Run:

  ```bash
  conda run -n ipi python -m unittest tests.test_harness_audit -v
  ```

  Expected: PASS.

  Commit:

  ```bash
  git add experiments/harness_audit.py config/paper/protocol.yaml config/paper/task_manifest.yaml tests/test_harness_audit.py
  git commit -m "feat: add deterministic harness audit helpers"
  ```

### Task 4: Integrate compact records without changing P0 execution

**Files:**
- Modify: `experiments/run_benchmark.py`
- Modify: `experiments/run_partial_benchmark.py`
- Modify: `dashboard/app.py`
- Modify: `config/paper/run_metadata.schema.yaml`
- Modify: `tests/test_dashboard_config.py`
- Modify: `tests/test_dashboard_history.py`

**Interfaces:**
- Consumes: existing AgentDojo results and `SampleRecord` helpers.
- Produces: compact per-task JSON/CSV summaries, separate non-valid counters, optional compressed full sidecars, and unchanged P0 pipeline calls.

- [ ] **Step 1: Write regression tests for compact output and missing security results**

  Assert that summary output omits raw prompts and complete action arrays, that `full` mode remains opt-in, and that missing `security_results[task_key]` yields `infrastructure_error` rather than `attack_success=False`.

- [ ] **Step 2: Run dashboard and runner-focused tests and verify failure**

  Run:

  ```bash
  conda run -n ipi python -m unittest tests.test_dashboard_config tests.test_dashboard_history -v
  ```

  Expected: new assertions fail before integration changes.

- [ ] **Step 3: Add passive record collection**

  Keep the existing `make_defended_pipeline`, benchmark calls, authorization, audit, and ticket flow unchanged. Build records after each task result is available and write only the compact projection by default.

- [ ] **Step 4: Preserve optional full traces and dashboard laziness**

  Reuse the existing `summary`/`standard`/`full` levels. Write full records only to the existing compressed sidecar mechanism and keep dashboard history/summary endpoints on compact files.

- [ ] **Step 5: Run focused tests and commit**

  Run:

  ```bash
  conda run -n ipi python -m unittest tests.test_dashboard_config tests.test_dashboard_history tests.test_harness_records tests.test_harness_audit -v
  ```

  Expected: PASS.

  Commit:

  ```bash
  git add experiments/run_benchmark.py experiments/run_partial_benchmark.py dashboard/app.py config/paper/run_metadata.schema.yaml tests/test_dashboard_config.py tests/test_dashboard_history.py
  git commit -m "feat: integrate compact harness records"
  ```

### Task 5: Complete E0 offline audit and report

**Files:**
- Modify: `experiments/harness_audit.py`
- Create: `tests/fixtures/harness_audit_cases.json`
- Create: `tests/test_harness_audit_replay.py`

**Interfaces:**
- Consumes: deterministic task selection, synthetic payload delivery cases, compact records, and the existing trace summary contract.
- Produces: an offline E0 report containing payload delivery, predicate replay, valid/non-valid denominators, and a single manifest hash.

- [ ] **Step 1: Add synthetic fixture cases**

  Include delivered payload, undelivered payload, missing security result, replayable final state, incomplete trace, and tool/policy/model error cases. Keep fixture contents short and non-sensitive.

- [ ] **Step 2: Add replay tests**

  Assert that the independent oracle agrees with the stored predicate for valid cases and rejects incomplete or inconsistent cases.

- [ ] **Step 3: Run the offline E0 command**

  Run:

  ```bash
  conda run -n ipi python -m experiments.harness_audit --fixture tests/fixtures/harness_audit_cases.json --output /tmp/dscg-e0-harness-audit.json
  ```

  Expected: exit code 0, explicit valid/error/skipped counts, and no raw prompt or full environment object in the default report.

- [ ] **Step 4: Run the complete offline suite and commit**

  Run:

  ```bash
  conda run -n ipi python -m unittest discover -s tests -q
  ```

  Expected: PASS.

  Commit:

  ```bash
  git add experiments/harness_audit.py tests/fixtures/harness_audit_cases.json tests/test_harness_audit_replay.py
  git commit -m "test: complete E0 harness audit"
  ```

### Task 6: Run I3 P0 recovery stress tests

**Files:**
- Create: `experiments/i3_p0_stress.py`
- Create: `tests/test_i3_p0_stress.py`

**Interfaces:**
- Consumes: existing `PermissionSandbox`, `ReferenceMonitor`, `ExecutionTicket`, `TicketedToolsExecutor`, and mock tool runtime.
- Produces: per-fixture compact records and a route-compliant `pass` or `no_go` report; no new authorization mechanism.

- [ ] **Step 1: Write fixtures for the eight required recovery paths**

  Cover normal in-scope retry, unauthorized tool request, expanded object scope, check disabling, forged administrator message, stale ticket replay, modified destination/parameter, and duplicate/concurrent submission.

- [ ] **Step 2: Run the focused stress tests and verify failure**

  Run:

  ```bash
  conda run -n ipi python -m unittest tests.test_i3_p0_stress -v
  ```

  Expected: failure until the fixtures and assertions are implemented.

- [ ] **Step 3: Implement the offline driver**

  Feed each recovery candidate through the same monitor and ticketed executor used by P0. Assert that every retry receives a fresh decision and that stale tickets, modified calls, and concurrent duplicates cannot execute.

- [ ] **Step 4: Run the I3 report command**

  Run:

  ```bash
  conda run -n ipi python -m experiments.i3_p0_stress --output /tmp/dscg-i3-p0-stress.json
  ```

  Expected: exit code 0. If all unauthorized recovery paths are blocked and the in-scope retry succeeds, report `no_go` for a new mechanism as required by the route.

- [ ] **Step 5: Run complete tests and commit**

  Run:

  ```bash
  conda run -n ipi python -m unittest discover -s tests -q
  ```

  Expected: PASS.

  Commit:

  ```bash
  git add experiments/i3_p0_stress.py tests/test_i3_p0_stress.py
  git commit -m "test: add I3 P0 recovery stress fixtures"
  ```

### Task 7: Record research-side evidence and close the branch work

**Files:**
- Modify: `../research/paper/implementation_status.md`
- Modify: `docs/superpowers/plans/2026-10-05-workshop-engineering-optimization.md`

**Interfaces:**
- Consumes: final test outputs, current `workshop` commit, working-tree status, report paths, report hashes, and valid/non-valid denominators.
- Produces: one E0 record, one I3 record, completed plan checkboxes, and a final verification commit on `workshop`.

- [ ] **Step 1: Compute final evidence**

  Run:

  ```bash
  git rev-parse HEAD
  git status --short --branch
  shasum -a 256 /tmp/dscg-e0-harness-audit.json /tmp/dscg-i3-p0-stress.json
  ```

- [ ] **Step 2: Append route-compliant status records**

  Include exact commands, exit codes, code revision, working-tree state, environment, changed paths, artifact paths/hashes, valid/invalid/error/skipped counts, limitations, and one next action. Do not claim improved defense rate or utility without an actual benchmark.

- [ ] **Step 3: Run final verification**

  Run:

  ```bash
  conda run -n ipi python -m unittest discover -s tests -q
  git diff --check
  git status --short --branch
  ```

  Expected: all tests pass, no whitespace errors, and only intentional untracked input files remain.

- [ ] **Step 4: Commit the completed plan and status**

  Run:

  ```bash
  git add docs/superpowers/plans/2026-10-05-workshop-engineering-optimization.md ../research/paper/implementation_status.md
  git commit -m "docs: record workshop harness and recovery evidence"
  ```

## Verification Matrix

| Check | Command | Acceptance |
| --- | --- | --- |
| Existing regression | `conda run -n ipi python -m unittest discover -s tests -q` | All tests pass; no P0 regression |
| Compact output | `python -m experiments.harness_audit ...` | No raw prompt/full environment in summary JSON |
| Replay | `python -m experiments.harness_audit ...` | Stored predicate agrees with independent oracle for valid samples |
| Recovery | `python -m experiments.i3_p0_stress ...` | Unauthorized recovery and stale ticket paths do not execute |
| Branch discipline | `git branch --show-current` | `workshop` |
| Working-tree hygiene | `git diff --check` | Exit code 0 |

## Stop Conditions

- Stop and report `partial` if AgentDojo or the configured model is unavailable; do not substitute missing samples with safe outcomes.
- Stop and report `no_go` for I3 when P0 blocks all unauthorized recovery paths and the legitimate retry remains in scope.
- Stop before I2 if E0 cannot establish payload delivery, an independent predicate, a reconstructable trace, or complete denominators.
