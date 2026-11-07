# Benchmark compatibility/reporting simplification — 2026-10-20

User-authorized behavior-preserving refactor using Ponytail. Only `experiments/run_partial_benchmark.py` changes at runtime: 1,049 → 1,005 lines (44 fewer; 62 removed, 18 added).

- Reuse the already-bound base directory; remove redundant path resolution and directory creation.
- Copy host-built error/unsupported results once, retaining manifest field order and error-before-unsupported record order.
- Build CSV records directly; delete unused imports, variables, obsolete report comments and dead post-cache token reads.

Native scoring, denominators, unsupported-group detection, model settings, validation, cache binding, diagnostic filtering and defense behavior remain unchanged. Existing staged/unstaged work was preserved; this task makes no commit and does not target user result directories.

## Verification

All commands exited 0. Full Python logs: [AgentDojo](../artifacts/20261020_ponytail_benchmark/tests_ipi.log), [AgentDyn](../artifacts/20261020_ponytail_benchmark/tests_agentdyn.log); [Node log](../artifacts/20261020_ponytail_benchmark/tests_node.log).

| Command | Outcome |
| --- | --- |
| `conda run -n ipi python -B -m unittest discover -s tests -p 'test_serial_runner.py' -v` | Before refactor: 10 passed |
| `conda run -n ipi python -B -m unittest discover -s tests -v` | 581 total: 572 passed, 9 skipped |
| `conda run -n ipi-agentdyn python -B -m unittest discover -s tests -v` | 585 total: 584 passed, 1 skipped |
| `/Users/luo/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node --test tests/*.cjs` | 47 passed |
| `conda run -n ipi python -B workshop/artifacts/20261020_ponytail_benchmark/compare_outputs.py before` and same command with `after` | 3 scenarios / 25 matching artifacts |
| `conda run -n ipi-agentdyn python -B workshop/artifacts/20261020_ponytail_benchmark/compare_outputs.py before` and same command with `after` | 3 scenarios / 25 matching artifacts |
| `git diff --check` | clean |

Comparisons cover clean baseline, clean defended and mixed completed/error/unsupported groups. They compare JSON content, Markdown and CSV after normalizing temporary roots, source metadata, invocation IDs, timing and diagnostic source line numbers. Existing regression tests additionally exercise full/cohort selection, interruption, cache reuse, Dashboard, provider adapters and diagnostic redaction. The final field-order-only edit was checked by rerunning both comparisons after the full suites. Independent review found no actionable issues.

## Evidence and limits

Revision at start: `0235fbf5b6af22e4fd88c8d02f9d4e25a713c533`; changes remain uncommitted. [Isolated patch](../artifacts/20261020_ponytail_benchmark/simplification.patch), [start status](../artifacts/20261020_ponytail_benchmark/start_status.txt), [validation and hashes](../artifacts/20261020_ponytail_benchmark/validation.json), and [runnable comparison](../artifacts/20261020_ponytail_benchmark/compare_outputs.py).

New model calls / real rollouts / efficacy samples: **0 / 0 / 0**. This verifies offline behavior, with no provider recovery, efficacy or research-gate claim. E0 pending; I3 partial (24 valid / 8 scope violations); I2 locked.

Next action: review the isolated patch and continue normal user measurements with their existing configuration.
