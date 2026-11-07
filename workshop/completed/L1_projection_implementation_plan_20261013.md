# L1 finite projection implementation plan

> Execute inline with executing-plans/TDD; user requested implementation of L1_opt.md. Current canonical workshop checkout is the user-designated writable implementation. No additional approval, worktree, commit, push, dependency install or real-model run is needed. Final fresh-context reviewer is required by the execution workflow.

Goal: change planning exposure through one native task-conditioned projection, keeping raw evidence and execution mediation intact.

Architecture: exact finite monthly-spending request matcher + native get_most_recent_transactions binding + complete strict Transaction YAML/JSON adapter. Render all rows, IDs, sender/recipient, amount, date, recurring; omit subject only. Keep original L1 wrapper and raw L3/logs. off means old marker, shadow computes but displays marker, projected applies qualified reductions. Default projected, nonqualifying inputs fallback.

Spec: [L1_opt.md](../L1_opt.md), scoped selection below. No parameter/object/provenance/obligation/recovery mechanism or novelty claim; formal route unchanged by workshop authorization.

## Frozen scope and review focus

- Supported full request: What's/What is my total spending in <English month> <year>?; Calculate my total spending in ...; finite Chinese equivalent. Full match only, no suffix/extra instructions, file-delegation T_eff not matched. Case insensitive, bounded user text.
- Actual native tool only: banking get_most_recent_transactions, native Python callable/code and parameter/schema binding. Metadata valid read/sink-none. Unknown custom same-name callable must fallback.
- Transaction output7 keys exact: id integer>=0, sender/recipient "me" or uppercase IBAN syntax, finite numeric amount, subject string, ISO date string, recurring bool. Inputmax32768 UTF8 bytes, max500 rows. Reject duplicates, YAML aliases/anchors/tags, unknown/missing fields, invalid types, nonfinite numbers. No attack keyword checks.
- Keep all parsed rows/order and6 retained values; no row selection/calculation/currency inference, strings remain untrusted. Valid corrupted facts/IBAN substitution can pass. Valid structural omission cannot be authenticated; claimed incomplete/error flags fallback.
- Nonempty error, nontext/mixed content, ambiguous call-ID mapping, mismatched tool_call or explicit truncation fallback to original marker. No original content in model-visible diagnostics.
- Raw user/tool/history stays immutable and L3 sees same original bounded return. Original wrapper rebuilt every turn, no stale raw subject reintroduction or nested rendering.
- Profile/mode/adapter/bounds affect config/pipeline/cache/L3 hash; input_isolation=false disables projection. No paid API/benchmark. Trace numeric counters separate actual from shadow/would, chars not Tokens.

## Tasks

- [x] T1 RED tests for native-view omission/all6values/allrows/order, raw/audit retention, marker/shadow/off, legit subject-dependent tasks, error/alias/duplicates/unknown/custom callable/truncation/retained-field attack/fact corruption. Build projection module and input view seam, GREEN.
- [x] T2 RED integration tests: effective task matching, factory mode/config/name and router compatibility, partial CLI forwarded/bound, native baseline unchanged; implement controls/version/counters, GREEN and full suite.
- [x] T3 characterization on actual native serialized transactions and current144 preserved histories; report supported/eligible/reasons/representation chars only. No trajectory reuse as efficacy and no model calls. Reuse I3/E0 under fresh task-root outputs.
- [x] T4 reviewer/read-only fresh context; fix verified blockers RED→GREEN; sync README, docs/candidate/index, completed report/plan, archival originals/state/hash/links; exact evidence append to sibling implementation_status.

All new logs/probes/output under workshop/artifacts/20261013_l1_projection/. Preserve baseline source/state, raw results/download, previous evidence/report bytes; pending candidate stays top-level, completed stage plan/report moves completed. Real four-arm/cost/security/utility and broader profiles remain pending.
