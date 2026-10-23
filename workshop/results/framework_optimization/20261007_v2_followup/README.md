# V2 follow-up artifacts

Stage1 code is committed as337bca6. Stage2 execution guidance was sampled in a dirty working tree, then withdrawn after matched controls. Final default source equals stage1. `stage2_candidate.patch.gz` and `test_execution_policy_candidate.py` preserve the exact historical candidate; the archived test's default-guidance assertion does not apply to final runtime.

Immutable stage1 files are listed by`stage1_sha256.json`. New stage2 files are listed by`stage2_sha256.json`; original benchmark data remain under`results/partial_benchmark/`, with276 raw input hashes in`controls_input_sha256.json`. Never regenerate original results in place when reviewing this evidence.

- `controls.json`: three arms, matched12clean/36important_instructions each,12extra preflights per attacked arm. Original native scores and token totals preserved.
- `audit_patch_comparison.json`: paired final-runtime comparison to fresh baseline.
- `executor_{control,candidate,shipped}.json`: original next-step probes; names refer to historical phases, not current deployment. They lack resolved-model configuration metadata.
- `executor_rescored.json`: strict derived scoring; retains10/12,12/12,11/12. `rescore_executor.py` reads raw outputs without model calls.
- `history_diagnosis_v2.json`: corrected native predicate stack, all320proposals;144outcomes unchanged,8native errors reproduced,6Monitor blocks distinguished. Supersedes original methodology without changing original artifacts/hashes.
- `denial_probe.json`: authored denied-action prefix,4/4; simulated feedback and no tool execution, not a general guarantee. This artifact includes public model metadata.
- `verification.json`: exact candidate patch reconstructs recorded source hash; final source equals audit-only controls; main model/user queries align,20stage1 and276raw hashes verified. Initial failed preflight filename check is retained separately.
- `final_regression.log`:169tests after candidate withdrawal. Candidate's earlier172test log is historical.
- `final_i3.json`: still partial,8scope violations in24valid probes; `final_e0.json` is only the six-case synthetic self-check.

Offline review commands (with ipi active):

```bash
python examples/results/framework_optimization/20261007_v2_followup/rescore_executor.py
python examples/results/framework_optimization/20261007_v2_followup/diagnose_history_v2.py
python examples/results/framework_optimization/20261007_v2_followup/verify_followup.py
python -m unittest discover -s examples/results/framework_optimization/20261007_v2_followup -p test_evidence_scoring.py -v
```

The model probe commands are live API evaluations. Proposed tools are never executed by those probes. `executor_probe.py shipped` requires the archived candidate patch; it is intentionally not a command for final runtime. Original scripts remain historical evidence, including their superseded scorers.
