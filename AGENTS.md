# BaseIntent Agent Instructions

## Scope and state

- Work only in this `BaseIntent/` checkout. Do not inspect or modify sibling projects unless the user explicitly asks. This project has its own code, docs and development state.
- The user chose to retain the existing Git linked-worktree, branch history and remote. Do not detach it, change remotes, stage, commit, reset or push without an explicit request.
- Preserve credentials, dirty work, historical result identities and raw evidence. Never rewrite old labels, source hashes, native messages, arguments or grades to fit new names or outcomes.
- Read `DV_STATE.md` first when resuming development; verify branch, HEAD, status and actual code. Update it at significant stages, distinguishing implemented, tested, unverified and planned work. Keep it concise.
- Delegated subagents may use only `gpt-6.1-sol` or `gpt-6.1-terra`; default to Sol. Terra is available when appropriate, especially visual work. Report unavailability; never silently use another model.

## Current source map

| Area | Files |
| --- | --- |
| Pipeline and execution mediation | `baseintent/pipelines/defended.py` |
| L1 planning views | `baseintent/input_isolation.py`, `baseintent/l1_projection.py` |
| L2 and intent progress | `baseintent/l2_authorization.py`, `baseintent/intent_flow.py` |
| L3 and failure/trace contracts | `baseintent/audit_router.py`, `baseintent/decision_schema.py`, `baseintent/failure_policy.py`, `baseintent/task_diagnostics.py` |
| Models, backend, tools, legacy readers | `baseintent/model_config.py`, `baseintent/request_compatibility.py`, `baseintent/benchmark_catalog.py`, `baseintent/tool_metadata.py`, `baseintent/compat.py` |
| Measurement and screening | `experiments/run_benchmark.py`, `experiments/run_partial_benchmark.py`, `experiments/run_injection_precheck.py`, `experiments/common/` |
| Platform and tests | `dashboard/`, `tests/` |

Current usage starts at `README.md` and `docs/README.md`. `docs/framework.md` describes the implemented framework, `docs/migration.md` the naming boundaries, and `docs/maintenance.md` the engineering verification. Do not use historical analysis as current defaults.

## Defense contracts

- Default factory/profile `legacy` is the current **BaseIntent** implementation. A run name is only an output label. Explicit historical profiles retain their original behavior, not compatibility with old measurement caches.
- L1 rebuilds a planning view from raw history. Source wrappers are guidance, not fact authentication. Only the bounded banking monthly-spending profile projects structure; invalid/unsupported inputs fall back to wrapping. Raw returns remain available for native traces and audit. AgentDyn has no extra projection profile.
- L2 has two main-client calls: bounded intent/goal-kind decomposition, then global tools and fixed-ID-key progress associations. The host losslessly folds adjacent facts/condition prefixes into the following outcome before assigning IDs. Independent effects and trailing preparations remain distinct.
- Merge automatic reads and freeze global grants/catalogue within the task. Progress associations cannot grant or forbid tools. Invalid/unauthorized candidates reject the whole batch before audit. No dynamic grants, task-ID rules, argument repair or missing-tool recovery.
- Explicit bounded delegated task sources keep existing mediated preparation and fail-closed rules. Ordinary tool returns cannot create task authority or recursive delegation. User-confirmed contaminated task files remain outside the supported scope. Trusted bounded profiles retain their own protocols.
- Host progress owns IDs, revision, state and actual facts/effects/final-answer observations. Semantic output is only satisfaction/evidence_ids. Require exact successful ledger/message matching; blocked/error returns and assistant claims are not execution evidence. Effects belong to the intent bound before execution.
- Mapped preparation reads may be observed locally. Complex goals, answers, conditions and unknown tools retain semantic checks. Automatic completion is confined to the reviewed bounded direct single-invite request, one effect goal, actual valid audit and native successful None contract. Never generalize this to arbitrary tools or multiple objects.
- Ambiguous needs the actual final clarification; unknown conditions are not false. condition_false is only for conditional_effect with successful evidence and cannot erase an observed effect. Advance serially, never guess dependency skips. Keep existing bounded continuation/stopping; no re-execution to fill evidence.
- L3 audits current intent under complete original constraints using native schemas/effects and bounded evidence. Source injection alone does not invalidate aligned facts. Preserve strict finite decision/violations/confidence/reason_code output; no parser repair, retries, default allow or semantic fallback.
- Registered, authorized, schema-valid public/internal reads bypass L3 in all modes. This is not sink, URL, internal-host or object-privacy filtering; internal tools can read private channels. Personal/secret reads and effects remain audited. A valid deny/abstain is enforced. Final text has no separate action audit gate.
- Monitor preserves native order, whole-batch one-use receipts and execution tickets bound to intent/catalogue/authorization/context. Mixed batches audit only the nonexempt subset without bypassing whole-batch mediation. NoL2 disables intent flow; NoChecker keeps L2/progress without invented audit evidence.
- CLI router defaults to shadow; API/factory defaults to off. Thresholds are diagnostic/configuration-bound and do not tune the fixed exemption scope. Preserve native generation sampling and record actual settings. Shared provider adapters/accounting remain in use; never patch installed backends or add fallback requests.

## Records and compatibility

- New code uses `baseintent`, `BASEINTENT_*`, `baseintent_*`, `.baseintent.jsonl` and `.baseintent.responses.jsonl`. There is no old-package import shim.
- Old metadata/sidecars are read through the explicit compatibility boundary only. Keep original identity strings, schemas, hashes, native payloads and file bytes. New/old environment aliases may coexist with the same value; conflicting values fail without revealing credentials.
- Save audit/progress content or refusal before parsing, with exact attempt/response/offset binding. Never save hidden reasoning, SDK/header/credential data or duplicate prompts. Host events have no invented or stale model response ID.
- Input/API/timeouts/catalogue/internal/I/O and malformed main tool-argument JSON are infrastructure errors with null efficacy labels. Known received-output defects and bounded no-progress stops use native stopping/predicates, preserving real effects, prior answers and successes. Never count errors as successful defense.
- Full/partial/cohort/Dashboard share native outcome projection, cost scopes and failure indices. Separate actual invocation from cached/whole-run costs and GOAL preflight from scored tasks. Missing usage remains unknown; clean ASR is not applicable.
- No automatic migration of old caches/cohorts or source-equivalence claims. Reuse requires complete actual configuration/task/attack/backend binding. Use fresh names for changed identities. Historical comparisons require recorded backend and actual selected task keys.

## Benchmarks and validation

- Detect actual imported backend metadata, not conda name. `ipi` normally supplies AgentDojo 0.1.35/v1.2 (four suites); `ipi-agentdyn` supplies AgentDyn pinned by the local lock (three suites). Metadata-only checks do not certify source or service behavior.
- Tool metadata follows explicit/env/backend-local/recognized-generic/builtin priority. Unknown/incompatible catalogues fail before calls. Never fabricate schemas, placeholder arguments or risk classifications. Unsupported AgentDyn tool_knowledge goals remain excluded from efficacy denominators.
- Full selects all registered tasks; partial keeps registration-prefix 3 users x 3 targets and cohort filters never backfill. Screening gives each injection GOAL one trajectory; failure excludes, errors/interruption skip separately, resume starts only unstarted goals. Do not retry completed screening or rewrite frozen decisions.
- Measurements keep native attack order and existing separate attack processes. Do not introduce concurrency flags or retries. Full benchmark execution requires an explicit request.
- Real Qwen evaluation is the default for behavior changes under the user's standing authorization; use existing model/provider and shared runners. At least 9 distinct completed scored cases, appropriate clean/attack controls, and proportionate expansion for substantial changes. Respect any current explicit cap/offline restriction; closed campaigns remain closed.
- Mocks/authored replies are deterministic engineering checks only. Report actual attempted/completed/valid/error/incomplete counts, exact case IDs, calls and known/unknown usage. Never replace unavailable real calls with mocks or infer general efficacy from small samples.
- Offline full commands: `conda run -n ipi python -B -m unittest discover -s tests -v`, same in `ipi-agentdyn`, plus `node --test tests/*.cjs`. Preserve known pre-existing failures and explicit backend skips; no full-green claim without evidence.

## Storage

- Current tests and runtime must work when retired engineering material is absent. Do not introduce imports, fixture inputs or documentation links to that material or sibling repositories.
- New validation outputs/plans/snapshots go under fresh ignored `artifacts/<YYYYMMDD>_<task>/`; reusable tests/fixtures stay in `tests/`, reusable runners in `experiments/`. Test scratch parents are created by `tests/artifact_support.py`.
- User results stay in `results/`; exports in `download/`. The retired historical engineering directory remains physically untouched pending a separate deletion request. `archive/` holds inert historical materials, not current operating instructions.
- Record stage commands/exits, source identity, scopes/costs, limitations and next action in maintenance evidence. Code availability or passed engineering tests is not paper novelty, an object/parameter authorization guarantee or an independent coverage oracle.
