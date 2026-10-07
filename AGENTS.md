# DSCG Research Handoff

## Project

DSCG is a research prototype for defending tool-using LLM agents against indirect prompt injection (IPI). The intended project root is `/Users/luo/Desktop/AgentDefence`, with the implementation under `DSCG/` and a deliberately separate research directory under `research/`.

The repository is writable at `/Users/luo/Desktop/AgentDefence/DSCG`. Keep it separate from the sibling `research/` repository: do not create a second research directory under `DSCG/`, and do not copy paper plans into this repository.

## Research Handoff

论文问题、文献、创新点和实验协议统一维护在项目根目录的 `research/`。本仓库只实现研究侧已经解锁的工程任务。先读取 `../research/technical_route.md`，完成后按 `../research/paper/implementation_status.md` 回报，不在本仓库复制论文计划或自行宣布新颖性。

## Project Status (verified 2026-10-06)

- P0.1–P0.5 are recorded as implemented: fail-closed authorization state, authorization before candidate generation, complete mediation with a Reference Monitor and one-use execution tickets, structured audit decisions and trace levels, and explicit tool-risk metadata.
- Existing implementation is tool-level. LLM audit is supplementary; parameter/object/data constraints remain unimplemented and locked until research-side route selection. `system_TODO.md` contains historical proposals and must not be used to restart closed routes.
- Workshop changes improve harness bookkeeping and compact traces: missing security results are infrastructure errors, finite task subsets use a fixed seed, and summary/standard omit redundant hashes while runtime checks and full compressed sidecars are retained.
- `I3-P0-STRESS` has fixtures, state-transition tests and an evidence record, with status `partial`. A real concurrent duplicate-ticket bug was fixed: the replay receives its own blocked event without failing the in-flight winning action. The 24 valid probes still expose 8 scope violations across fresh object, destination, data-selection and completed-obligation calls; do not report `no_go` or claim these constraints are enforced.
- The latest recorded offline suite passed 102/102 tests (18 I3 tests). These counts are a dated snapshot, not a benchmark defense rate or a required fixed test count.
- E0 synthetic self-check has 6 samples: valid=1, tool_error=1, infrastructure_error=4. It does not establish that the real harness passed the research gate. Historical AgentDojo results remain smoke-only.
- Existing `research/ideas.md` calls contribution candidates hypotheses, not proven novelty. Preserve that caution.
- Current implementation status is recorded in `research/paper/implementation_status.md`; do not infer parameter-level provenance or I2 coverage from P0 code.
- Current engineering details and artifacts are linked from `README.md`, `docs/i3_p0_stress_report.md` and `docs/workshop_optimization_report.md`; the older eight-case I3 `no_go` is superseded by the 2026-10-06 evidence.

## Current Engineering Queue

The active queue is defined only by [`../research/technical_route.md`](../research/technical_route.md). The route still marks `E0-HARNESS-AUDIT` and `I3-P0-STRESS` ready; the outgoing I3 evidence is now `partial` and awaits research-side review. Reuse the existing I3 fixtures and evidence; a new scope/recovery mechanism requires a research-side route decision. `I2-FIXTURE` and `I2-PILOT` remain locked until the harness audit and research-side decision pass. The old field-level provenance/source-to-sink proposal is closed as `No-Go` and must not be revived under a new name.

For each ready task, keep the implementation change in `DSCG/`, run the stated checks, and append one evidence record to [`../research/paper/implementation_status.md`](../research/paper/implementation_status.md). A task report must include the exact command, exit code, code revision, working-tree state, artifact paths/hashes, sample denominators, limitations, and one next action. Research-side files are edited only in `research/`.

## Validation

- Offline regression: `conda run -n ipi python -m unittest discover -s tests -v`.
- I3 fixture: `conda run -n ipi python -m experiments.i3_p0_stress --output <new-output-path>`. Current expected exit is 1 (`partial`, scope violations); exit 0 is reserved for a fully valid run with all constraints passing (`no_go`), and exit 2 indicates sample errors.
- E0 self-check: `conda run -n ipi python -m experiments.harness_audit --fixture tests/fixtures/harness_audit_cases.json --output <new-output-path>`.
- Matched no-defense partial baseline: `conda run -n ipi python -m experiments.run_partial_benchmark --baseline --force-rerun --name <new-baseline-name>`. Uses the native AgentDojo tool loop, the same main-model configuration and v1.2 suites as DSCG. The current subset keeps the first 3 user tasks and first 3 injection tasks in registration order per suite; preserve this user-adjusted selection. The retained `seed: 7` metadata does not rank the current prefix subset. No security model or defense metadata is used. Verify exact IDs in `summary.json` → `task_selection`; historical runs may have used another selection rule.
- Partial attack selection: the CLI and Python default is `typical`: `ignore_previous`, `injecagent`, `important_instructions`, `tool_knowledge` (4 targeted attacks; 144 planned rollouts on the current grid). Explicit `--attack all` resolves the installed AgentDojo registry (currently 16 automatic attacks; 456 planned rollouts). Presets cannot be mixed with specific names; missing typical attacks are rejected rather than silently dropped. Interactive `manual` is excluded from this runner's CLI and Python selection. Specific or repeated flags select attacks, e.g. `--attack tool_knowledge injecagent`. Single- and multi-attack outputs use `<model_id>_<name>/<attack>/<suite>/`, including native task JSON, sidecars, reports and cache reads; the base run directory contains `attack_manifest.json` and a combined report. Original model identity is used to construct attacks before the native logging loop uses the attack as its local pipeline storage component; reports and manifest retain model/run identity. Old output directories remain intact; they are not migrated or read as new-layout caches. Failed attacks are recorded as errors and yield exit 1; they are not zero-ASR samples. Explicit DoS selection uses the first registered injection task once per user and scores `not utility`; keep its denominator/meaning separate from targeted ASR. README labels official implementation links explicitly as AgentDojo; registry variants are not independent published methods. Typical selection controls workload, not demonstrated attack strength. This is CLI coverage, not a passed E0 gate or new defense mechanism; output-text predicate false positives still need auditing.
- Offline baseline/attack checks: `conda run -n ipi python -m unittest discover -s tests -p 'test_partial*.py' -v`; these do not call a model or establish benchmark efficacy.
- Dashboard history is an independent `/history` page, with experiment/history navigation on both pages. It uses actual result folder → model/run groups (checkbox multi-select) → recorded attack filters. Filter changes select all matching visible runs for comparison; manual run exclusions persist during catalog refresh. Explicitly empty model selection stays empty and disables analysis/export. New `<model>_<name>/<attack>/<suite>/` and legacy flat/`__attack` directories are supported without migrating data. Missing attack metadata is `unknown`; mixed old aggregates stay `mixed`; explicit `run_attack=false` takes precedence over a retained configured attack when no recorded attack exists. Analysis/export use visible checked IDs and include directory/model/attack identity. Stale analysis responses cannot overwrite a changed selection. Top legends emphasize short version names; model/run groups share colors and letter badges across attacks, lists, charts and tables. Bars carry letter labels even at zero; multi-attack charts also use attack numbers, point shapes and line dashes without merging data. Full identities remain in tooltips/exports. Styles stay stable within a loaded catalog, but are not persistent across reloads; short aliases do not replace source identity. Desktop uses a filter sidebar; narrow screens stack panels. Offline checks: `conda run -n ipi python -m unittest discover -s tests -p test_dashboard_history.py -v` and `node --test tests/test_history*.cjs`. Latest evidence: `docs/history_version_identity_report.md`; this is display/export engineering, not benchmark validity evidence. Matching attack filters alone do not establish matching task IDs.
- Keep old result files and evidence hashes intact. Documentation-only edits need link/state consistency checks and `git diff --check`; rerun runtime tests when code or an unresolved concern changes.

## Working Rules

- Do not claim "first", formal guarantees, complete taint tracking, or general defense without evidence.
- Do not treat capability-graph components, audit logs, or execution tickets alone as the paper's novel algorithm.
- Keep the first study to text-based, single-agent tool use and external-content-to-tool-action flows. Defer multimodal, multi-agent, MCP, and online learning extensions.
- Preserve existing project changes. Do not overwrite result data or local model/tool credentials.
- Do not edit paper plans from `DSCG/`; use `research/technical_route.md` for incoming work and `research/paper/implementation_status.md` for outgoing status.

## Session Handoff

At the start of a new session, verify that the workspace is `/Users/luo/Desktop/AgentDefence`, read `research/technical_route.md`, and inspect `research/paper/implementation_status.md` before making research-driven changes. Do not infer a paper claim from code or a smoke benchmark. Keep the two repositories independently reviewable and do not merge them into a new nested checkout.

<!-- framework-optimization-20261007 -->
## Optimization handoff (2026-10-07)

- V2 stage 1: sorted authorization catalogue, explicit temperature 0, conditional-task semantics and compact failure codes; no authority from tool feedback. Regression 161/161. Synthetic real-model compiler probes are observations, not task execution or defense efficacy. No new configuration files/flags are required. See `docs/framework_v2_report.md`; stage 1 commit `48ae317f4dd88736b5b00c1dcd7baa04466a0033`.

- P0-A: 顶层调用新建 context，清除旧授权缓存和历史、撤销票据；任务内循环沿用。
- P0-B: 记录主模型/授权/审计 API、Token、耗时；历史分析显示两模型合计。官方攻击分数保留，E0 独立送达/环境复核仍待完成。
- P0-C: 网页请求按外部接收方路由至现有审计；离线成对样例覆盖合法访问和注入网址。未实现 URL 对象约束。
- P1-A: 可选一次语义 abstain 重审；保留当前任务历史，parser/超时不重试，持续不确定阻断。
- P1-B: 可选通用提示继续已授权任务并覆盖用户要求字段；每次工具动作仍受现有 monitor/ticket 检查。
- P2: partial CLI 支持 no-checker、重审和完成提示开关及匹配任务 manifest；实际安全/效用收益仍需有效在线对照。

Use `docs/framework_optimization_report.md` for validation. Preserve existing results and separate original official scores from diagnostics. That earlier report used offline checks only; V2 now has real synthetic probes and matched partial controls in `docs/framework_v2_report.md`. E0 real payload/end-state gate and efficacy goals remain pending. Commit only stage deltas; pre-existing attack/dashboard edits are intentionally retained.

- Matched optimization comparison: README `本轮框架优化` documents defaults/conflicts and separate baseline/P0/reaudit/completion runs. The frozen `examples/results/framework_optimization/20261007_readme_comparison/task_manifest.json` matches all 32 historical suite summaries for `deepseek-flash_baseline` / `deepseek-flash_workshop_new`; typical attacks plan 144 rollouts per arm across 12 user tasks. Use new names `baseline_control_20261007` and `workshop_opt_p0_20261007`, the same main/security model IDs, and force-rerun; add retry/prompt individually. Compare fresh baseline as the primary control and old runs as historical references; matching IDs does not recover historical provider revision or prove E0 validity. Documentation verification called no model.

- Documentation preference: explain only the six newly added optimization CLI options as a concise list. User-facing commands assume the `ipi` environment is already active and use `python` directly. Keep exact historical executed commands in reports/evidence unchanged.

### Framework simplicity directive (2026-10-07)

- 用户要求重点优化框架，每层保持简单。先优化两个逻辑防御层：可信任务工具授权、当前动作安全审计；Monitor/ticket 是执行基础设施，不把模块数量算作防御层数。
- 优先解决漏授权和必要审计上下文缺失；重审、恢复和额外规则暂不叠加为默认方案。每次修改用匹配对照报告安全增益、任务效用与成本。
- 若两层在有效对照下仍无净收益，转为职责明确的三层架构，验证第三层独立增益；具体职责依据真实失败轨迹确定，保持每层简洁。
- 该方向没有实现第三层或解锁 I2/新对象与数据权限机制；具体设计交付到 research 技术路线。参见 [`../research/paper/framework_optimization_direction_20261007.md`](../research/paper/framework_optimization_direction_20261007.md)。

### V2 bounded audit context (2026-10-07)

- Stage 2: current-task last four tool returns, at most 2,048 characters each, marked untrusted with separate content/window truncation flags. Facts may inform the current action; feedback/auditor never changes the grant or candidate arguments. No object/data provenance enforcement. Single audit default, retries=0 and completion_prompt=false.
- Missing ignored local tool metadata falls back to tracked `config/tools.agentdojo-v1.2.toml`; explicit path/env and existing local override remain authoritative. Unknown/invalid tools remain critical. No new external configuration or CLI flags required.
- Default partial IDs verified against the original frozen comparison manifest: 12 user-task clusters, 36 tool_knowledge or 144 typical rollouts, 12 clean tasks. V2 commands in README omit --task-manifest; use new names baseline_v2_control / workshop_v2_authorization / workshop_v2_two_layer, same current provider/model. This supersedes earlier instructions to generate/import a manifest for this comparison.
- Stage 2 regression 167/167; real synthetic audit: 8/8 expected decisions with context, 4/8 without context (same revised prompt, one pass), no model errors. Compiler/auditor probes do not establish end-to-end efficacy. I3 still partial: valid24/scope8/tool-boundary0; E0 self-check6 valid1/tool-error1/infra4 is not a real harness gate. See `docs/framework_v2_report.md`.

- V2 audit follow-up: actual candidate alignment is distinct from detecting injection text elsewhere. Task-relevant no-target listings can obtain unknown facts; explicit targets/destinations still need task evidence, never guessed from URL wording. Legal rent-read replay allow3/3; ungrounded URL abstain6/6, grounded URL allow3/3, external verification deny1/3+abstain2/3. Strict-label10/12 (probe exit1) retained; fail-closed execution expectation12/12, not general scope enforcement. No default/routing/grant changes. Follow-up matched runs required before efficacy claims.

### V2 matched pilot outcome (2026-10-07)

- Producer commit `00a58e3b67650d481d28296040611fa98898dd40` for refined/completion arms; original baseline/no-checker controls at `9225018`, unchanged native/authorization components. Same v1.2 IDs and all 36 attack payloads matched. Single repeat across12 user clusters: baseline/no-checker/refined clean11/12 and attack32/36; completion clean11/12 and attack31/36. All10 CLI invocations exited0, no target trace errors.
- Refined default restores the initial two-layer pilot's four completion losses (28→32/36). It still briefly blocks one legitimate webpage and succeeds after normalized-URL retry. Completion introduces a clean bill-read abstain and loses one attack task; keep completion=false, retries=0.
- Do not claim ASR3→1 as a defense gain: baseline3 are final-answer hotel-name warnings, refined1 is a real `send_direct_message` body to Alice containing the injected link as a warning (audit allow). Completion has the same link forwarding plus3 hotel-name quotations. No independent E0 final-state oracle or repeated efficacy gate; no new layer or locked scope enforcement.
- Refined token cost: clean144066 vs baseline113593 (+26.83%, over20% target); attack total524371 vs440398 (+19.07%, includes12 preflight). Refined target418222 and preflight106149; baseline target-only costs unavailable. API latency sums are not wall-clock time.
- All old and unsuccessful intermediate results preserved. Latest analysis/hashes in `examples/results/framework_optimization/20261007_v2_implementation/final_controls_*`; README commands use native defaults, no imported config/manifest. Next research review: outbound warning-link counterexample and real E0/repeated controls before deciding a tool-result processing layer.
