# GrantBind Agent Instructions

## Working directories: workstation and test server

- `/home/yuxin_luo/DSCG` is the user's working directory on the test server (`user-PowerEdge-T640`: Ubuntu, 96 cores, 125 GB RAM, RTX 5090 + L20), where subsequent tests are run; the workstation checkout of the same repository is `/Users/luo/Desktop/AgentDefence/GrantBind`. Both copies of this file are kept byte-identical and updated through GitHub: edit it once, commit and push, then take the new version on the other side instead of hand-editing a second copy.
- The checkout root is the repository root: in-repo relative paths used below (`DV_STATE.md`, `docs/`, `workshop/`, `tests/`, `experiments/`) resolve against it, and the sibling research checkout `../research/` is `/home/yuxin_luo/research` on the server and `/Users/luo/Desktop/AgentDefence/research` on the workstation; both hold `technical_route.md` and `Qwen_API.md`. `/home/yuxin_luo/BaseIntent` is an unrelated repository and stays out of scope.
- Git differs per machine and must be checked per machine: the workstation is on `workshop` tracking `origin/workshop`; the server checkout has a detached HEAD at `6726cb0` plus an untracked `AgentDyn/` backend source clone, and its remote-tracking refs may be stale. Do not commit, switch or reset branches merely to reconcile the two checkouts; report the branch/HEAD a run actually used.
- Conda: the workstation uses `/opt/miniconda3` with `ipi` (AgentDojo) and `ipi-agentdyn` (AgentDyn); the server uses `~/miniconda3` with `DSCG` (AgentDojo; the `ipi` env named in the commands below does not exist there, substitute `DSCG`), `ipi-agentdyn` and `crawler`. On the server, conda is absent from the PATH of non-interactive shells: use `~/miniconda3/bin/conda run -n <env> ...` or source `~/miniconda3/etc/profile.d/conda.sh`. Verify the env actually used instead of assuming a name.
- Server storage: `/home` is about 93% full (~540 GB free). Keep new outputs in `workshop/artifacts/<YYYYMMDD>_<task>/`, pass `--results-dir` there, and avoid duplicated result trees, extra backend clones or copying large raw results between the two machines.
- Report every run with its host, conda env, exact command, exit code and artifact paths, in addition to the revision and usage facts required below.

## Scope and working rules

- Work in the GrantBind engineering checkout for indirect prompt-injection defense. Keep the sibling `../research/` repository separate; do not copy paper plans here or create a nested research checkout.
- Before research-driven changes, read `../research/technical_route.md` and follow its current implementation-status link. E0 remains pending, I3 partial (24 valid probes, 8 scope violations), and I2 locked. Do not reopen the closed provenance/source-to-sink route or add object/data/parameter authorization, recovery, or other locked mechanisms without a new research-side decision.
- Preserve existing dirty work, user moves/deletions, unrelated conflict markers, credentials, historical results and evidence. Do not stage or commit unless explicitly requested. Keep the filename `AGENTS.md`; do not create lowercase `agents.md`.
- Delegated subagents, including planning and review, may use only `gpt-6.1-sol` or `gpt-6.1-terra`. Default to Sol by inheritance or explicit selection; Terra may be selected when appropriate, especially for visual tasks. User model restrictions override skill model-selection/escalation advice. Do not select Astra or any other model unless the user explicitly requests it; report selected-model unavailability without automatic fallback.
- These rules describe the `workshop` branch as of 2026-10-27. Check current code before importing behavior from another branch. Dated reports and archived handoffs describe their own tasks; closed campaigns remain closed.

## Project State Management

Use the project-root [DV_STATE.md](DV_STATE.md) to maintain cross-session project state. Read or update it only when the current task involves project progress.

### Restore context

- At the start of a new development session or when resuming an interrupted task, read `DV_STATE.md` first.
- Check the current Git branch, HEAD, working-tree state and relevant code.
- Cross-check the state document against the current implementation; never treat stale records as facts.
- Identify completed work, unresolved issues and the next task. Do not repeat work already completed and verified.

### Update triggers

Update `DV_STATE.md` when:

- An important development stage is completed.
- The architecture or a key technical approach changes.
- A bug or limitation affecting subsequent work is discovered.
- An important experiment is completed and validation results are available.
- The user explicitly asks to preserve the current work state.

### Update rules

- Record facts, important decisions and their reasons; omit lengthy conversation history.
- Distinguish implemented, tested, unverified and planned work.
- Retain unresolved issues and relevant historical decisions.
- Record the corresponding branch, commit and validation results.
- Keep the file concise; revise existing entries instead of appending redundant updates.
- Never commit, switch or reset a Git branch merely to update the state document.

## Code and documentation map

| Area | Entry points |
| --- | --- |
| Pipeline factory and execution mediation | `dscg/pipelines/defended.py` |
| L1 planning views | `dscg/input_isolation.py`, `dscg/l1_projection.py` |
| L2 and static task views | `dscg/l2_authorization.py`, `dscg/task_view.py` |
| L3 and failure/trace contracts | `dscg/audit_router.py`, `dscg/decision_schema.py`, `dscg/failure_policy.py`, `dscg/task_diagnostics.py` |
| Model/provider and backend/tool metadata | `dscg/model_config.py`, `dscg/request_compatibility.py`, `dscg/benchmark_catalog.py`, `dscg/tool_metadata.py` |
| Measurements, reuse, cohorts and reports | `experiments/run_benchmark.py`, `experiments/run_partial_benchmark.py`, `experiments/run_injection_precheck.py`, `experiments/common/` |
| Dashboard and regression sources | `dashboard/`, `tests/` |

Use [README.md](README.md) for the framework, [model/tool configuration](docs/model_tool_configuration.md) for setup, and [evaluation](docs/evaluation.md), [benchmark](docs/benchmark.md), [partial](docs/partial_benchmark.md), [screening](docs/injection_precheck.md) and [result files](docs/result_files.md) for operations. Historical reports describe their dated configurations; verify against current code before changing behavior.

## Current framework: GrantBind v3.7 (recorded as DSCG_v3.7) / static-task-v354

- Default `static-task-v354` runs both v3.7 input forms: compact L2 catalogue input (`authorization_input=v3`) and expanded single-pass audit evidence (`audit_presentation=v3`, 32,768/8,192 character bounds). Both are bound into the run identity and recorded in `run_manifest.json`; `DSCG_AUTHORIZATION_INPUT=v2` and `DSCG_AUDIT_PRESENTATION=v2` exist only for ablation.
- Full, partial, cohort and Dashboard share the production factory. Default `static-task-v354` uses two-stage L2; explicit `legacy` is the single-authorization control. Baseline defaults to legacy and uses the native loop. Select profiles from the current registry; experiment names do not select strategies.
- **L1:** rebuild an isolated planning view from raw history, preserving original returns for audit/native traces. The existing banking monthly-spending projection preserves every row/order and six structural fields, omitting subject only under its bounded profile. Unsupported, ambiguous or invalid inputs fall back to source wrapping. AgentDyn has no additional projection profile. No extra model call, fact authentication or provenance enforcement.
- **L2:** static-task-v354 first extracts a static task view with literal references, order and conditions, then compiles global action permissions from the complete trusted request and native definitions/schemas. Merge automatic reads and freeze grants/catalogue within the task. The view assists planning and auditing; it does not verify conditions or completion. Show authorized definitions without mutating the execution catalogue. No dynamic grants, missing-tool repair or task-ID rules; invalid/unauthorized candidates reject the whole batch before L3.
- **Delegated tasks:** explicitly delegated bounded txt/md task sources use existing mediated preparation reads, then compile the complete effective task shared by planner/L2/L3. Preserve raw roles; ordinary tool results cannot create task authority or recursive delegation. Retain existing size/grammar limits and fail-closed behavior. User-confirmed contaminated task files remain outside the approved scope. Trusted bounded host profiles retain their original protocols and ceilings.
- **L3:** audit current actions against the complete trusted request, actual native schema/effects and bounded evidence, using the strict four-field verdict. Source injection alone is not a violation; task-linked discovery and derived parameters are allowed, while off-task effects, wrong targets and unrequested forwarding are denied. Outbound body and destination both matter. Final text has no separate action-audit gate.
- `sink-free-read-v4` exempts only registered, authorized, schema-valid `effect=read`, public/internal, `sink=none` calls in off/shadow/selective. Reads with external sinks, personal/secret reads and effects remain audited; valid deny/abstain block. Tool labels do not enforce object privacy or authenticate facts and query parameters.
- **Monitor:** preserve native batch order, one-use whole-batch receipts and execution tickets bound to the task, candidates, catalogue, authorization and context. Audit only the nonexempt subset without weakening whole-batch mediation. Static supports NoL2/NoChecker with router off; nonoff routing still requires L2/L3. Do not import an intent-progress FSM, completion gate or recovery loop from another branch.
- CLI router default is shadow; API/factory default is off. CLI L1 projection defaults off; factory/API retain projected. Fixed read exemptions apply in all modes; thresholds do not tune that scope. No automatic schema fallback, semantic retry, permission expansion or parser repair. Keep native generation sampling unchanged and report actual outbound settings rather than assuming native temperature 0 was sent.
- Count actual authorization, static-view extraction (`authorization_intents`), tool compilation (`authorization_tools`), generation and audit usage. Disable SDK retries while preserving adapters/accounting; native generation can still retry, so do not claim end-to-end single transmission. Use the shared DashScope role adapter for Qwen tests. Preserve historical provider compatibility without using DeepSeek for live evaluation or patching installed backends.

## Failure scoring and diagnostics

- Derive efficacy from native grades and the shared outcome projection; retain actual effects and raw labels. L2 protocol failures fail authorization closed; they do not activate an intent-progress/native-Abort scoring policy. Treat blocking, task failure and infrastructure errors separately instead of forcing a fixed False/False outcome.
- API/timeouts, input/catalogue/internal/I/O failures and malformed main-model tool-argument JSON remain infrastructure errors with null efficacy labels. Never repair arguments, execute a malformed batch, rescore errors as successful defense, or let blocked/error returns count as execution evidence.
- Native task traces keep interactions, grades, errors, time and a diagnostic reference. Append compact v2 metadata/costs/final audit/action occurrences to per-trace `.dscg.jsonl`; deduplicate immutable public configuration by attack/suite.
- Save complete L3 content or refusal to `.dscg.responses.jsonl` before parsing, including malformed/incomplete replies. Bind relative path, attempt/response IDs and byte offsets. Whitelist finish/usage/latency/call fields; L2 stores parsed authorization/task views only. Never store hidden reasoning, SDK/header/credential data or duplicate prompts/tool bodies.
- L1 records isolation/projection/fallback only. Preserve safe original error codes and field/rule subcodes; label new blocks as L2, L3 or Monitor. Shared readers/reuse must support old inline/v1/gzip and `DSCG_BLOCKED`, merge bound attempts/offsets, and expose missing/corrupt/incomplete evidence without fabricated replies, zero costs or efficacy labels.
- Cache hits do not rewrite old files or invent responses; real reruns append fresh attempts. Policy/schema/effective model/defense changes bind identities and require fresh run names, never historical cache/cohort migration. Full/partial/cohort/Dashboard share scoring, projections, costs and failure indices. Recorded failures followed by native generation retries are a known projection gap; preserve their errors and unknown usage instead of claiming that gap is fixed.

## Benchmark, screening and reuse contracts

- Detect the actual imported backend via installation origin/version/revision/path, not conda name or directory labels. `ipi` normally supplies AgentDojo 0.1.35/v1.2 (workspace/travel/banking/slack); `ipi-agentdyn` supplies AgentDyn v1.2 pinned to `5353cf7615b135cace8d07c8f12dac53a16b6db3` (shopping/github/dailylife). Current verification is metadata-only; do not scan runtime source hashes or claim source/service certification.
- Resolve tool metadata through existing explicit/env/backend-local/recognized-generic/builtin priority. Unknown or incompatible catalogues fail before calls; do not reclassify native effects, fabricate missing schemas/placeholder arguments or overwrite local configuration. AgentDyn dailylife tool_knowledge groups lacking placeholder_args are unsupported, excluded from efficacy denominators.
- Full uses all registered tasks in selected suites; partial keeps registration-prefix 3 users x 3 targets. Cohort filtering never backfills the prefix. Typical attacks are ignore_previous, important_instructions and tool_knowledge; manual is excluded. Full/cohort suite subsets and screened scope must remain explicit; use actual task IDs and valid/error denominators rather than planned grid totals.
- Measurements run separate attack processes when multiple attacks are runnable, with native order within each attack. Single attack, clean and screening remain sequential. Parent validates bindings/owns locks and reports; children write only their attack subtree. Keep interruption cleanup, native preflights and cost scopes; no new concurrency flags or retries.
- Screening gives each injection GOAL one complete native trajectory: success keeps, failure excludes, error/interruption skips separately; no second-chance same-run/resume/historical retries. Historical reuse selects the first compatible path; resume only unstarted goals. Freeze success-only cohorts even with errors and retain exit 1. Existing frozen two-failure cohorts retain their original bytes/semantics.
- Frozen-cohort measurement validates main model ID/provider, actual backend, suites and task IDs/order, then reads/digests the list once. Do not re-read screening traces/manifests, verify original screening evidence, compare adapters/GOAL or reconstruct decisions during list consumption. Screening creation/resume/evidence reuse retains its evidence checks; list reuse does not recertify screening conclusions.
- Explicit measurement reuse validates complete effective configuration/task/attack/suite/cohort bindings before writes/calls, restores original omitted selections, snapshots aggregates/incomplete traces, and preserves native cache decisions. No automatic retry or source-equivalence claim. CLI new paths are `<results-dir>/<backend>/<model>/<name>/`; legacy `<backend>/<model>_<name>` stays readable in place and is never migrated. Do not move old outputs.
- Reports keep compact suite rows plus complete native evidence/failure indices. Separate GOAL from scored tasks, invocation from cached/whole-run costs, and potential from actual savings. Missing usage remains unknown; clean ASR is not applicable. Dashboard comparisons use recorded identities and actual selected task keys without rewriting historical data.

## Validation and model-call budgets

- Ship behavior changes switched on. A framework change is delivered as the new default, not behind a flag the user must remember; keep only an opt-out for ablation and name it in the report.
- Test-only CLI parameters are allowed (2026-11-06 update): they may select an ablation or measurement control (for example `--no-checker` for L3 or `--no-sandbox` for L2), but they must not enable, modify or be required by the optimized framework. The shipped default path must stay testable with `experiments/run_benchmark.py` alone, without such parameters, and the switch must not change the framework design. Each switch binds to an existing configuration path, is recorded in `run_manifest.json` (for example `profile`, `authorization_precheck`, `input_isolation`), and is named in the report. Do not use prompt-profile-like switches to redefine the validated framework.

- Use only the real `qwen3.7-flash` API for Online Evaluation, the default for validating behavior changes. All live test requests, including component probes, baseline, GOAL preflights, generation, task extraction, authorization, progress judgments and audits, must use `qwen3.7-flash`. DeepSeek and all other test models are prohibited, even if existing credentials or local defaults select them, unless the user explicitly authorizes that model for the round: with explicit user approval, online evaluation may run on `deepseek-flash` using its own configuration and the same runners, scoring and scopes; no other model is authorized by this exception. Verify effective model settings before sending requests; report the model actually used, and report a mismatch or unavailable service without issuing disallowed calls or falling back. This evaluation-model restriction is separate from the Codex subagent model policy.
- The user grants standing authorization to start and complete permitted online evaluations, including necessary model calls and proportionate sample expansion, without asking for permission again. Reuse existing Qwen model/API configuration, shared runners and native scoring; do not change providers or models to obtain a pass.
- Evaluate at least 9 distinct scored task cases, spanning affected behavior, suites and attacks where applicable. Count task cases, not API requests, component probes or GOAL preflights. Report attempted/completed/valid/incomplete/error counts separately; fewer than 9 completed cases does not satisfy the minimum coverage, and errors never become successful-defense samples.
- For framework optimization or other substantial changes to L1/L2/L3, intent state, Monitor, scoring or shared execution, autonomously increase task counts and coverage beyond 9 according to the change's scope and observed failures. Include relevant clean/attack controls, affected suites/backends and fresh named follow-up batches when needed. State the scope and reason in progress updates, respect explicit limits, and stop expanding when the relevant validation is complete; do not seek renewed approval merely because more than 9 cases are needed.
- This standing authorization covers fresh task-specific evaluations; it does not reopen closed campaigns, reuse their remaining balances, waive a current stop/offline-only instruction, or override an explicit request/token/cost limit. No new per-run budget approval is needed when the current task sets no such limit. Full AgentDojo/AgentDyn benchmarks still require an explicit request.
- Documentation-only changes need link/state consistency checks and `git diff --check`, with no model calls.
- Mocks/authored replies/interception are for deterministic unit/error/engineering regression only. They cannot replace fresh online judgments or establish L2/L3/progress quality, defense efficacy, TSR/ASR or general safety. Explicitly report unavailable APIs, zero/failed real calls and cache-only replay; never silently substitute.
- Label Online Evaluation and Offline Regression separately. Report actual attempts/successful calls, known usage/unknown reserves, valid/error denominators, exact task/attack IDs and scope. Preserve raw native traces/grades/replies, immutable public configuration and errors under diagnostic/privacy rules. Do not change models, algorithms, native predicates, labels or selection just to make checks pass.
- Run targeted offline checks appropriate to code changes, respecting current-task restrictions. Broader commands, when warranted, are `conda run -n ipi python -B -m unittest discover -s tests -v`, the same in `ipi-agentdyn`, and `node --test tests/*.cjs`. Backend-specific skips are explicit. Known pre-existing Python failures/errors remain; do not claim the full suite is green or alter unrelated defenses to hide them.
- I3/E0 diagnostics live at `experiments.diagnostics.i3_p0_stress` and `experiments.diagnostics.harness_audit`; pass a fresh artifact `--output`. I3 partial exit 1 and synthetic E0 self-checks do not pass research gates. Small samples, overlapping regression signals, audit explanations and engineering tests do not prove causal/general safety or novelty.

## Test-run conventions (2026-11-06 onwards)

- **Backend and version scope.** AgentDojo only (server `DSCG` conda env); do not run AgentDyn or `ipi-agentdyn` unless explicitly asked. All new measurements use the v3.7 framework. v3.8 is abandoned: its recorded probe results stay as dated evidence, but no new v3.8 runs are started.
- **Naming.** Follow the existing per-model directory convention: clean arms end in `_clean`; attack arms are named after the measured configuration (`baseline`, `v3.7`, `v3.7-plus-2026-05-26`). Never reuse a name that already exists inside the same model directory, and give ablations an explicit label (for example `ablation_workspace_full`).
- **Results.** Pass `--results-dir /home/yuxin_luo/DSCG/results/workshop` on every run so outputs land in `results/workshop/<backend>/<model>/<name>/`. Logs, launchers, manifests and frozen lists go to `workshop/artifacts/<YYYYMMDD>_<task>/`.
- **Ablation archive.** Completed ablation arms are grouped per variant at `results/workshop/agentdojo/ablation/<variant>/<attack>/<suite>/` (variants `full`, `noL3`, `noL2`; switch probes under `ablation/probes/`), mirroring `<backend>/<model>/<name>/`. Arm root files are preserved under `<variant>/_arms/<suite>/` with a `.arm.` suffix so the dashboard never indexes them as suite summaries, and the variant carries `README.md` + `derived_provenance.json` + a `summary.json` aggregate marked `derived: true`. Do not synthesise `run_manifest.json` for a merged variant. The runner still writes new runs to `<backend>/<model>/<name>/`; move an arm into the archive only after it is complete and record its original model/name in the report. Archived arms cannot be resumed by their old path.
- **Derived reference arms.** A reference arm may be extracted from an existing real run instead of re-run (for example `ablation/full/banking`, copied from the qwen3.7-flash v3.6.3 banking subset). Such a directory is not a new run: it must carry `README.md` and `derived_provenance.json` naming the source path, commit, copied keys and file hashes, and the version/L1-marker caveat; reports and dashboard labels must call it derived. Keep the per-suite `summary.json` + `detailed_results.csv` layout inside the owning variant so the dashboard catalog indexes it as `model=ablation`, `run_name=<variant>`.
- **tmux reuse.** Reuse the sessions recorded below instead of creating new ones. When a new session is unavoidable, add a row with its purpose and remove the row after `tmux kill-session`. Long lanes are plain shell scripts under the artifact directory so a dropped SSH connection cannot stop them.
- **Concurrency.** At most three model-calling processes at a time; lanes must write disjoint result directories and must not share an active `--name` in the same model directory.
- **Comparison arms.** External comparison arms are test-only entry points and never change the default path.
  - Server outbound network: GitHub/pip only through the workstation reverse tunnel (`ssh -f -N -R 127.0.0.1:7890:127.0.0.1:7890 yuxin_luo` from the workstation); server `git config --global http.proxy/https.proxy` point at `http://127.0.0.1:7890`. If the tunnel drops, git fails closed; fall back to workstation download + scp. Parallel DSH ssh sessions print "remote port forwarding failed for listen port 7890" — expected, the persistent tunnel owns the port.
  - Tier A (`spotlighting_with_delimiting`, `tool_filter`) runs via `experiments/run_external_defense.py` on the partial-scope 108-key grid; split lanes are allowed for slow arms as long as per-suite results are merged by the aggregation script and each split run keeps its own name.
  - Tier B runs live outside this repo: `/home/yuxin_luo/MELON` (AgentDojo 0.1.35 port, DashScope `text-embedding-v4`) and `/home/yuxin_luo/IPIGuard` (vendored AgentDojo 0.1.23 fork, suite version v1.1.2, model registry patched for qwen3.7-flash). Both use only qwen3.7-flash and keep their own provenance/README. AgentDojo built-in defenses (`spotlighting_with_delimiting`, `tool_filter`) run through `experiments/run_external_defense.py` on the origin loop (manifest records `agentdojo_defense`) and store results under `results/workshop/agentdojo/<model>/<arm>/`. Tier B reproductions (MELON, IPIGuard) live outside this repository under `/home/yuxin_luo/{MELON,IPIGuard}` and are aggregated only in `workshop/artifacts/<YYYYMMDD>_comparison/`, never by synthesising DSCG run manifests.
- Keep reporting host, commit, exact command, exit code, model/settings and usage denominators as required above.

| tmux session | Purpose | Created | State |
| --- | --- | --- | --- |
| `gb-plus-atk` | Qwen3.7-Plus snapshot: GOAL screen then attack arms — baseline finished 18:17; **v3.7 arm interrupted 20:00 by user** (workspace partial, resumable with `--reuse`) | 2026-11-06 | ended |
| `gb-nol2` | Qwen3.7-Flash workspace NoL2 rerun via `--no-sandbox` (finished 15:37) | 2026-11-06 | ended |
| `gb-plus-cln` | Qwen3.7-Plus snapshot: clean arms (finished) | 2026-11-06 | ended, session closed |
| `gb-ablate` | Qwen3.7-Flash workspace full + NoL3 ablation (finished) | 2026-11-06 | ended, session closed |
| `gb-slack-abl` | Qwen3.7-Flash slack ablation: full then NoL3, new L1 marker (both arms finished 16:56) | 2026-11-07 | ended |
| `gb-bank-abl` | Qwen3.7-Flash banking NoL3 ablation, 432 keys, finished 20:19 (full reference from the v3.6.3 run; no banking_full arm) | 2026-11-07 | ended |
| `gb-travel-abl` | Qwen3.7-Flash travel NoL3 ablation, 360 keys (358 valid, 2 task errors), finished 14:43; full reference from the v3.6.3 travel subset (summary-only derivation) | 2026-11-08 | ended |
| `cmp-tf-a` | Tier A tool_filter (workspace+banking) then clean | 2026-11-09 | active |
| `cmp-tf-b` | Tier A tool_filter (travel+slack) then clean | 2026-11-09 | active |
| `cmp-melon` | MELON comparison arm, 108-key grid, attack then clean | 2026-11-09 | active |
| `cmp-ipiguard` | IPIGuard comparison arm (v1.1.2 grid intersection), attack then clean | 2026-11-09 | active |

## Storage, reports and historical context

- Put pending engineering plans in `workshop/`, completed stage reports in `workshop/completed/`, and original/superseded material in `workshop/archive/`. Do not create competing plan directories; formal paper work stays in `../research/`.
- All new agent-generated test outputs/logs/probes/plots/manifests go to fresh `workshop/artifacts/<YYYYMMDD>_<task>/`. For partial/full checks explicitly set `--results-dir` under that root. `tests/` holds test/fixture sources; `experiments/` holds reusable runners. Keep raw artifacts ignored by default without overwriting external ignore changes.
- Preserve user formal `results/` and `download/`, old `workshop/results/` evidence and all original hashes. Do not restore them from protection snapshots, move/delete them, fabricate missing history, or attribute concurrent changes without evidence. User-specific output instructions override defaults.
- Task reports record exact commands/exits, revision/dirty state, artifact paths/hashes, calls/usage/denominators, limitations and one next action. Research-driven handoff follows technical_route.md's current status link; never infer paper claims from implementation status or directory membership.
- Current behavior and open issues are maintained in [framework updates](docs/framework_updates.md), [DV_STATE.md](DV_STATE.md) and the [v3.5.3 analysis](analysis/v3-5-3.md); validation sources are linked there. Historical campaign budgets and withdrawn candidates stay in their dated reports, not this instruction file. Do not append experiment diaries or copy another branch's operating contracts here.
