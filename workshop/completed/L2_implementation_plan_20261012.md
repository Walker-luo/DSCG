# L2 implementation plan

> Execution: use superpowers:executing-plans and test-driven-development inline. The user explicitly requested implementation of the reviewed design; do not ask for the same authorization again. Record progress and verification in `workshop/artifacts/20261012_l2_implementation/`.

**Goal:** Implement the reviewed L2 tool view, bounded authorization profiles and explicit task-file delegation without bypassing execution mediation.

**Architecture:** Keep the real runtime intact. The executor owns a task context and frozen catalogue, builds a separate authorized planning view and shares the effective task with the auditor. Trusted profiles optionally provide positive/negative authorization evidence and read-only prerequisite closure; unknown task types retain the existing compiler. Explicit delegated files use monitored preparation reads before one complete task compilation.

**Stack:** Existing Python/AgentDojo/Pydantic and dashboard JavaScript; no new dependencies or model training.

**Spec:** [L2_opt.md](../L2_opt.md), including the user exclusion of contamination of a confirmed delegated order.txt.

## Constraints and decisions

- Preserve mixed-batch atomic rejection, Monitor/tickets, read-deny exception, retries0/completionfalse and L3 default off.
- Stage A displays every valid authorized tool; no top-k, lazy discovery, dynamic grant retry or hot reload.
- Profiles are trusted host inputs, never selected by untrusted feedback. No profile means existing permission compiler; no mandatory external manifest.
- Tool-level authorization only; no parameter/data provenance, object ACL, obligation ledger, recovery or novelty claim.
- Default explicit delegation supports bounded, unambiguous execute-file requests and registered host adapters; summary/read requests stay ordinary. Reject incomplete/ambiguous task sources rather than guess.
- Use actual monitored bootstrap tool returns, preserve raw messages, no fake user turn. Planner and L3 share the effective task. One full compilation is possible only when preparation is host-deterministic; actual tool/audit/input costs still count.
- New model/version/config identity binds controls and L3 artifacts. Preserve original task IDs, attack selection, native baseline and historic outputs.
- Keep current checkout and existing documentation edits. No unsolicited commit/push. Final review may use one fresh-context reviewer as required by executing-plans.

## Review focus

- A hidden or fabricated tool remains rejected even if the planner invents its name.
- New user tasks replace old grants; catalogue mutation cannot retain task authority.
- Negative constraints conflicting with required reads do not silently grant downstream actions.
- Executing a named order differs from summarizing it; unrelated returns cannot become task instructions.
- Failed/blocked/oversized bootstrap reads do not grant writes or trigger unbounded retries.

## Task 1: Authorized tool view and task catalogue boundary

Files: create `dscg/l2_authorization.py`, test `tests/test_l2_authorization.py`; modify `dscg/pipelines/defended.py`.

Interfaces: `planning_runtime_view(runtime, allowed)` returns an isolated runtime view and counts; `catalog_fingerprint(runtime)` binds tools/schema/callables/dependencies/metadata. Executor options include `planning_tool_view` and owned task context.

- [x] Write tests proving only valid allowed tools appear, empty/error authority exposes none, real runtime remains intact, invented calls still block, new user grants replace old ones and in-place catalogue mutation invalidates a task.
- [x] Run the focused unittest file; record RED.
- [x] Implement the view/context/guard and necessary monitor integration; no partial execution.
- [x] Run focused and existing authorization/precheck/task-isolation checks; record GREEN.

## Task 2: Bounded positive/negative authorization profiles

Files: module above, test above, compiler in `defended.py`.

Interfaces: immutable `ToolAuthorizationProfile` with explicit request patterns, permitted seed tools and host read prerequisites; optional compiler profile. Compatible legacy `{tools}` protocol remains for non-profile tasks. Profile protocol records tools, prohibited_tools and evidence spans against the effective task.

- [x] Test profile apply versus unsupported-task fallback; valid condition/negative evidence; forged evidence, unknown tools, write prerequisites, dependency cycles and deny/required-read conflicts; preserve zero-call read-only paths.
- [x] Observe RED, implement validated profile/closure/compiler protocol and compatible contract diagnostics, then GREEN.
- [x] Keep semantic correctness limitations explicit; no model score or keyword absence grants permission.

## Task 3: Explicit delegated task files

Files: module/context/executor above; add `tests/test_delegated_tasks.py`.

Interfaces: immutable `DelegatedTaskSpec`, bounded explicit delegation matcher and trusted registered-reader adapter. Bootstrap calls traverse existing precheck/checker/Monitor/tickets; accept only their successful results. Effective task is used in planner view, audit packet and router binding.

- [x] Test clean order execute versus summarize, caller-provided trusted source adapter and installed AgentDojo file-reader adapter, unknown/ambiguous source, failed/blocked read, incomplete/oversized content, forged unrelated returns, later data instructions and explicit user restrictions.
- [x] Test one complete authorization call after deterministic bootstrap, raw history preservation and no task-context leakage across top-level calls.
- [x] Observe RED, implement bootstrap/expansion/context consistency, then GREEN. Do not test or claim defense of the excluded polluted confirmed task source.

## Task 4: Controls, configuration, traces and platform handoff

Files: factory/framework version, partial runner, dashboard app/evaluation/templates/JS, relevant Python/Node checks, README/docs/AGENTS/workshop indexes.

- [x] Test default/legacy controls, native baseline unchanged, manifest/cache binding and profile identity; web settings and V2 control match effective runtime.
- [x] Implement planning-view/delegation controls, bounded trace counters and actual architecture description. Host profiles are API-only unless real profiles are selected; do not invent a dashboard trained-model selector.
- [x] Update pending memo with shipped/remaining states, save completed report/plan and original bytes under the archival policy.

## Final validation and handoff

- [x] Offline full regression: `conda run -n ipi python -m unittest discover -s tests -v`; Node dashboard/history tests.
- [x] Reuse I3 fixtures with a fresh output under this task root; expected exit1/partial. E0 synthetic self-check does not establish the real gate.
- [x] Fresh-context branch review; fix actionable defects and rerun affected checks.
- [x] Scoped source/doc/link/state/hash checks and `git diff --check`; preserve results/download metadata and old manifests.
- [x] Report exact commands/exits/revision/dirty state/artifacts/hashes/denominators/limitations/next action to sibling implementation_status.md. No real-model benchmark or token improvement claim without measurement.

## Execution outcome

Completed 2026-10-12 in the current authorized checkout. See [report](./l2_implementation_20261012.md) and the task ledger for exact RED/GREEN, reviewer repairs, failed intermediate runs and final evidence. Real deployment/profile and matched cost/security/utility validation remain pending; this checklist marks engineering tasks only.
