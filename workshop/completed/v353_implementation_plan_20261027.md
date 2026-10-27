# v3.5.3 Implementation Plan

> Execute inline with executing-plans/TDD; one independent gpt-6.1-sol review at completion. User explicitly requested implementation and fresh Qwen evaluation; no additional approval or commit.

**Goal:** Enable static-task-v352 by default and implement the eight recommendations in analysis/details.md within the existing tool-level framework.
**Spec:** [details.md](../../analysis/details.md), current user request, AGENTS.md and research technical_route.md.
**Architecture:** Reuse the two existing main-model authorization calls and share the fallible task view with planning/audit. Improve existing prompts and evidence presentation; keep original requests, frozen global grants, schema, Monitor and native predicates.
**Tech:** Python, current AgentDojo/AgentDyn adapters, real configured DashScope qwen3.7-flash.

## Constraints and review focus

- Preserve dirty work and all historical evidence; no stage/commit/branch changes. Artifacts and frozen sources under workshop/artifacts/20261027_v353_optimization.
- Baseline must remain native; defaults must agree across factory/full/partial/cohort/Dashboard, explicit legacy retained. Static ablations must not silently restore L2/L3.
- Preserve literal quote validation, original-request authority, batch checks/read exemptions/tickets. No completion ledger/gate, automatic recovery, dynamic grants, argument repair or parameter/object authorization.
- No extra model phase beyond the existing static extraction; native generation sampling and scoring unchanged. Missing date/year must remain unresolved rather than guessed.
- Do not repeat withdrawn L1 timing/marker/risk-removal arms. Preserve existing partial CLI L1 default off, use explicit same setting for comparisons.
- Online cases cover banking refunds/compound payments/false completion/address, Slack channels/DM/sequential reads, travel missing fields/independent recommendations/cost/calendar/text contamination/final delivery. Keep errors and unknown costs separate.

## Tasks

- [x] 1. Add failing default/entry-point/ablation tests; implement shared default resolution and v3.5.3 identity in prompt_profiles, factory, runners/cohort and Dashboard; verify baseline remains legacy/native.
- [x] 2. Add meaningful boundary tests for static sharing and original authority; update static extraction/planning guidance for independent choices, requested fields, cost basis and actual execution; align L3 static numbered/read examples with current default and present relevant user/fact context without extra authorization.
- [x] 3. Run targeted offline tests, update directly affected stale version/example assertions, request one fresh gpt-6.1-sol whole-change review and resolve findings. Freeze a named selection and sources; run fresh online controls and optimized arm using shared runners/native scoring. Expand only for observed gaps; no full benchmark.
- [x] 4. Record attempted/completed/valid/error/incomplete, exact task IDs, actual calls/usage, paired gains/losses and residual failures; update README/docs and DV_STATE with actual default and limitations. git diff --check and source/evidence verification.

Execution ledger and exact commands: workshop/artifacts/20261027_v353_optimization/progress.md.

Completed 2026-10-27. See [stage report](v353_optimization_20261027.md); all native batches and evidence preserved, residual failures explicitly retained.
