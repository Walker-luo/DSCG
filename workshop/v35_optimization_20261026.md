# v3.5 residual utility and web routing implementation plan

> Execute inline with executing-plans and targeted RED→GREEN regressions. Preserve current dirty docs; no staging or commits.

**Goal:** implement [analysis §4](../analysis/v3-5.md#4-对应完善方案与实施状态), then judge with fresh native Qwen trajectories.

**Architecture:** retain frozen single-call boolean L2 grants, shared effective task and whole-batch mediation. Improve authorization input guidance and bounded audit evidence; route external-sink reads through existing L3. Completion guidance remains a separately measured option.

**Constraints:** qwen3.7-flash/DashScope existing configuration, native scoring and sampling; no retries/argument repair, metadata relabeling, new authority or locked research mechanisms. Cohort-filtered injection_task_8 is not a defect. Artifacts: `workshop/artifacts/20261026_v35_optimization/`.

## Tasks

- [x] 1. Preserve control snapshot; inspect native failure cases and existing delegation. Add failing engineering tests for external-sink read mediation and complete relevant evidence under the fixed budget.
- [x] 2. Implement L2 per-outcome coverage guidance/input checklist without changing output/grants protocol. Prefer intact relevant audit returns; add concise semantic/contract contrasts to current L3. Keep schema/receipt/error behavior strict. Version changed policy/configuration.
- [x] 3. Implement external-sink read audit routing in the shared exemption helper; update affected fixtures. Refine optional completion/identifier guidance without a new host completion gate. Run targeted engineering checks.
- [x] 4. Snapshot static L2-only, L3-only, combined/no-web and full candidate sources. Fresh native control/candidate runs: six core users (banking2/11/15, slack11/13/18), clean + three attacks (24 distinct keys), seven old Slack ASR keys, legal webpage and identifier controls. Component ablations use a smaller fixed subset; completion tested separately. No repeat of screening goals in the same run.
- [x] 5. Inspect real actions, grades, errors, diagnostics and usage. Fix concrete defects and expand coverage proportionately when needed; preserve unsuccessful runs. Fresh gpt-6.1-sol whole-change review, final regressions, report and state update.

## Review focus

- External fetches must still pass L2/schema/whole-batch receipts; legal derived links can pass semantic audit.
- Relevant evidence cannot hide recent contradictions, cross task boundaries or authenticate injected content.
- Explicit delegation uses the existing shared effective task; ordinary documents do not create authority.
- Write alternatives cover delivery/update while read-only tasks remain without unrelated writes.
- Report actual effects, infra errors and unknown costs; native predicates and old artifacts stay unchanged.

Progress and exact commands/exits go in the task artifact ledger and completed report.

完成报告：[v35_optimization_20261026.md](completed/v35_optimization_20261026.md)。最终37/37有效，TSR14→17，ASR7→0；退款漏授权／效果误拒仍存在，不作为整体TSR验收通过。
