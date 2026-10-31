# v3.5.4 Utility and Protocol Implementation Plan

> Execute inline with executing-plans/TDD and one independent gpt-6.1-sol final review. No commits/staging. User explicitly requested implementation and Qwen online evaluation of analysis/v3-5-3.md section5.

**Stage status:** Engineering implementation and scoped validation completed; banking TSR gain was not achieved and remains open. Final outcome: analysis/v3-5-4.md and workshop/completed/v354_optimization_20261028.md.

**Goal:** Improve banking/Slack task completion while preserving measured ASR and travel utility.
**Architecture:** Keep the existing two upfront L2 calls, frozen global capabilities, strict current-action L3 and native loop. Add a separately versioned anchored task-view protocol; repair shared error classification; improve existing planning/audit presentation after checking actual evidence. No completion gate, recovery, dynamic grants, argument repair, object/parameter authorization or date invention.
**Tech:** Python/stdlib, existing AgentDojo/AgentDyn adapters, DashScope qwen3.7-flash main/security roles.
**Spec:** analysis/v3-5-3.md sections4–5; current AGENTS.md; research/technical_route.md and linked status read. E0 pending/I3 partial/I2 locked unchanged.

## Constraints and review focus

- Preserve dirty AGENTS/DV/analysis edits and formal results/download. Work on existing workshop checkout as in the approved session; immutable source snapshots isolate evaluations. No worktree/branch/commit operations.
- Fresh artifacts: workshop/artifacts/20261028_v354_optimization; no local model credentials copied. Both actual role configs verified qwen3.7-flash/dashscope, SDK retries0. No other evaluation model.
- Original profile static-task-v352 and its protocol remain available. New protocol gets distinct name/hash, old records readable; no automatic parser fallback or repair. Defaults change only after scoped validation.
- Dates missing in native schema stay missing; useful independent updates can proceed only in original permitted order/conditions. Legitimate clarification may remain native utility=False.
- Literal request references certify only request membership; never semantic completeness, condition truth, fact authenticity or extra authority. Unknown IDs/malformed branches fail before grant compilation.
- Current-attempt API failures exclude derived efficacy but retain raw labels/effects/costs. Never let an older attempt contaminate a new one.
- L3 retains actual destination/body, untrusted returns, recent corrections, four-field verdict, bounded evidence and read exemption/Monitor.
- Online control/candidates use identical explicit L1 off, native sampling, frozen task keys/payload checks and fresh names. At least24 distinct scored cases; increase to affected suites/attacks/clean/safety coverage. Not a full benchmark. ASR/travel are acceptance checks, not universal guarantees.

## Task 1 — shared API error projection

Files: dscg/task_diagnostics.py; experiments/common/benchmark_outcomes.py and shared historical readers only if required; tests/test_agentdyn_outcomes.py, tests/test_task_diagnostics.py and dashboard regressions.
Interface: load_task_trace(path) continues to return merged current-attempt data; positive recorded failed_calls yields safe infrastructure metadata, preserving raw JSON and native labels. project_outcomes keeps null derived efficacy for infrastructure failures.
- [x] Reproduce two recorded retry-failure cases and follow all projection readers.
- [x] RED tests: failed call followed by native success; new successful attempt after old failure; missing usage remains unknown; protocol failure alone not infrastructure.
- [x] Minimal shared fix, GREEN, relevant suite and baseline comparison.

## Task 2 — separately versioned anchored task view

Files: new dscg/anchored_task_view.py; prompt_profiles.py; pipelines/defended.py; shared runner/dashboard validators; tests/test_anchored_task_view.py and static/default/native tests.
Interfaces: request_anchors(request) -> ordered literal {id,start,end,text}; schema/policy select known anchor IDs with intent and mutually exclusive relation branch; parse(value, request) -> same internal tuple (intent,relation,condition,start,end); public static view remains original span references. No grants or model-dependent repair.
- [x] RED exact Unicode/whitespace/spans, duplicate text, unknown ID, branch mismatch, bounded schema, original-profile unchanged and two-call integration tests.
- [x] New profile static-task-v354, own binding/schema; default remains v352 during protocol evaluation. Main/audit/NoL2/NoChecker semantics shared without new calls.
- [x] GREEN both backends; native freeze/schema/Monitor tests; freeze protocol candidate.
- [x] Fresh Qwen control/protocol same-selection evaluation, actual provider preflight and cost/status recording; preserve all attempts.

## Task 3 — banking planning and Slack audit evidence

Files: anchored_task_view.py policy only; audit_context.py/defended.py only where actual audit packet demonstrates a gap; tests for any changed evidence-selection behavior.
- [x] Inspect original u11 deny inputs; distinguish missing from ignored facts. Add RED test before any host evidence-selection change.
- [x] Scoped planning guidance: native required vs optional update fields, independent authorized progress, narrow clarification; original order/conditions and unknown dates retained.
- [x] Scoped L3 current-vs-previous operation contrasts; existing successful evidence, no new allow exception. Keep restored u13/u17 as regressions.
- [x] Travel delivery remains anchored in existing successful returns; keep existing policy unless regression evidence justifies a small change. No new verification calls.
- [x] Freeze final candidate and evaluate same task/control set. Expand when needed for observed gaps; no resampling errors into wins.

## Task 4 — acceptance, review and delivery

- [x] Targeted Offline Regression, backend/default/CLI/Dashboard/Node checks; full Python run and named old-I3 failure index. No unrelated changes to make it green.
- [x] One fresh gpt-6.1-sol independent review; resolve meaningful findings with tests, retain minor/ruling evidence in report.
- [x] Adopt candidate default only with measured security/travel non-regression and banking/Slack evidence; if partial, preserve explicit candidates and state limits.
- [x] Update README/docs, DV_STATE and completed stage report: exact commands/exits, source/data hashes, all arm results, paired gains/losses, API/GOAL/component/scored costs and error denominators, residual dates/protocol/semantic limits.
- [x] Verify unchanged raw evidence/dirty work/index/branch and git diff --check. No full benchmark or research-gate claims.

Ledger: workshop/artifacts/20261028_v354_optimization/progress.md.
