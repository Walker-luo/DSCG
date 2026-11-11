# L3 pure-algorithm implementation plan

User scope: finish `L3_checker_opt.md`, revised by the 2026-10-10 choice of a pure algorithm with no classifier training. Execute inline using executing-plans; preserve the existing dirty dashboard work. The written candidate and explicit implementation request supply authorization; no formal research route is unlocked.

Goal: opt-in local selective auditing with hard internal-read eligibility, a fixed score, grouped calibration, one-use host receipts and conservative fallback.

Spec: [L3 checker design](../L3_checker_opt.md). CPU-only Python standard library; no model, embeddings, trained weights, dependencies or API calls in routing/calibration.

Fixed score `max(1-cos(task, description), argument_novelty, untrusted_support_gain, recent_failure_fraction)`. Character trigrams use normalized channels separately. Novelty and support are lexical signals, not fact or provenance authentication. Empty argument values have novelty/support zero; empty task/description are ineligible. Unicode controls are rendered visibly; oversized/unsupported input cannot bypass. Gate single authorized registered internal idempotent sink-free reads only.

Calibration: freeze a finite threshold grid before calibration, aggregate any-selected/any-unacceptable per independent group, use one-sided Clopper–Pearson with delta/grid Bonferroni. Select the feasible threshold with largest frozen estimated audit cost. Missing/insufficient evidence yields null. Require independent label sources and disjoint development/calibration/test groups; no auditor labels. Calibration certifies only the supplied reference distribution under its assumptions.

Review focus: forged public bypass JSON; stale task/catalog/schema/args/config; input truncation flags; correlated copies and split leakage; baseline/cache/mode compatibility. Unknown cost stays unknown. Existing read-deny exception is preserved.

- [x] 1. `dscg/audit_router.py`, `tests/test_audit_router.py`: bounded input, fixed features, numeric artifact validation, eligibility, grouped calibration and host receipt verifier. RED then GREEN.
- [x] 2. `dscg/pipelines/defended.py`, `tests/test_selective_audit.py`: off/shadow/selective routing, receipt validation before Monitor issues tickets, compact events/counters and actual audit costs. RED then GREEN.
- [x] 3. `experiments/l3_router_dataset.py`, `experiments/calibrate_l3_router.py`: explicit JSONL labeled input validation, group manifests, new artifact only, offline scoring/calibration reports. No classifier training CLI.
- [x] 4. `experiments/run_partial_benchmark.py`, relevant tests: opt-in CLI/API modes, manifest/digest and native cache identity, reject baseline/no-checker incompatibility. Keep current task/attack selection.
- [x] 5. Full offline regression, I3/E0 isolated fixtures, microbenchmark, one independent final review with fixes verified RED→GREEN; update README/AGENTS/platform handoff and workshop status. Archive original bytes and a new revision mapping without changing old hashes. Append exact evidence to sibling research status.

Completion means engineering paths and tooling verified; real independent calibration data, selective pilot and end-to-end savings remain evidence requirements. No production threshold is manufactured from unit fixtures.

Final review ledger: Critical0, Important5 fixed. Marker downgrade and ordinary-audit forging authenticated by host handoffs; action history bound (review reproduction and isolated omitted-binding failure); execution flags/policies/bounds frozen; row/manifest sources/groups/counts rechecked; complete flags required. Full suite after fixes244/244. No re-review dispatched. Minor(deferred): assess latency name excludes receipt/Monitor overhead. Minor(deferred): outstanding receipt cleanup after exceptions at task boundary. Declined judgments: off ordinary-audit authentication inherited; read-deny override preserved by user scope; label truth/group independence/grid chronology require external evidence; no real security/utility/cost claim; unrelated dirty dashboard preserved. No contribution or deployment approval inferred.
