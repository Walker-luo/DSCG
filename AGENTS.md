# DSCG Research Handoff

## Project

DSCG is a research prototype for defending tool-using LLM agents against indirect prompt injection (IPI). The intended project root is `/Users/luo/Desktop/AgentDefence`, with the implementation under `DSCG/` and a deliberately separate research directory under `research/`.

The current Codex session is **not** mounted at that project root. Its shell falls back to `/private/tmp`; `/Users/luo/Desktop/AgentDefence` and its files are readable, but the project directory is not writable in this session. Do not create a replacement `research/` directory in a different location and imply that it is the project research directory. Recheck `pwd` and write permissions at the start of the next session.

## Current Research Direction

The user's goal is to pursue a top-tier research publication, prioritizing a defensible research contribution before further system polishing. The candidate question discussed so far is:

> Can provenance-aware, field-level authorization stop untrusted content from changing authority-bearing tool parameters (such as recipient, object, amount, or destination), while still allowing that content to be used as task data and preserving more utility than coarse whole-action blocking?

Treat this as a hypothesis, not an established novelty claim. Existing overlap is substantial: ACE covers trusted planning/capability barriers/information-flow constraints; IPIGuard studies tool dependency graphs; SkillGuard and ActGov are close to capability confinement and per-action policy validation; Ajar motivates measuring unnecessary open privileges. A literature matrix must identify exact differences before implementation or paper claims are fixed.

## Project Status (from readable `DSCG/TODO.md`)

- P0.1–P0.5 are recorded as implemented: fail-closed authorization state, authorization before candidate generation, complete mediation with a Reference Monitor and one-use execution tickets, structured audit decisions and trace levels, and explicit tool-risk metadata.
- Existing implementation is still primarily tool-level. Parameter/object-level Task Contracts and provenance-aware source-to-sink policy are future work (P1/P2 in `DSCG/TODO.md`).
- The TODO's own research hypotheses include parameter-level authorization, explicit provenance for sensitive-source-to-external-sink flows, and LLM audit as a supplemental signal rather than the security root.
- Existing `research/ideas.md` appropriately calls these contribution candidates, not proven novelty. Preserve that caution.
- `research/papers.md` says its search cutoff is July 2026. Recheck newer work and verify publication status from official proceedings; distinguish peer-reviewed papers, workshops, and preprints.
- Relevant research files include `research/papers.md`, `research/ours.md`, `research/ideas.md`, `research/Contrast.md`, and the ACE/IPIGuard/IntentGuard analysis notes.

## Next Requested Deliverable

When the project is mounted and writable, create a document under the existing project `research/` directory that fixes:

1. A paper comparison matrix: threat model, enforcement point, authorization granularity, provenance/data-flow model, refusal granularity, utility treatment, benchmark, and overlap/gap relative to DSCG. Include AgentDojo, InjecAgent, Adaptive Attacks, ACE, IPIGuard, MELON, SecFid, SkillGuard, ActGov, Ajar, and relevant detection baselines. Mark uncertain venue/status for verification.
2. A minimal staged experiment protocol that separates a cheap pilot from paper-grade evaluation. Include threat model, paired benign/attack cases, baselines/ablations, metrics, repeat policy, statistical analysis, cost controls, and explicit go/no-go criteria.
3. A reading sequence ordered by research decisions: benchmark/threat model first, nearest novelty overlaps next, evaluation/fidelity next, then mechanism and attack baselines.

Recommended candidate mechanism to test, without claiming it is novel yet: preserve field-level source/derivation labels through explicit transformations; distinguish content fields from authority-bearing fields; enforce at the sink; block only the affected field/action where possible; mark uncertain lineage as `unknown`, not as proven taint. The decisive comparison is whether this improves utility at a matched security level over coarse blocking, not merely whether it adds logs or reduces ASR by rejecting more tasks.

Suggested experiment arms: no defense; current DSCG P0.5; deterministic parameter contract without provenance; proposed provenance-aware field-level enforcement; coarse high-risk/untrusted-action denial as a conservative upper-bound baseline. Add reproducible ACE/IPIGuard comparisons if feasible. Use paired tasks across all four AgentDojo suites for confirmatory results; a small representative pilot is for debugging only and must not support paper claims.

Track task-level attack success and utility separately from action-level unauthorized side effects. Also measure benign utility, utility under attack, false refusals, unnecessary open privileges, provenance coverage/unknown rate, latency, token/API cost, and recovery attempts. Use task-paired statistics and confidence intervals; pre-register task selection and decision thresholds before the confirmatory run.

## Working Rules

- Do not claim "first", formal guarantees, complete taint tracking, or general defense without evidence.
- Do not treat capability-graph components, audit logs, or execution tickets alone as the paper's novel algorithm.
- Keep the first study to text-based, single-agent tool use and external-content-to-tool-action flows. Defer multimodal, multi-agent, MCP, and online learning extensions.
- Preserve existing project changes. Do not overwrite result data or local model/tool credentials.
- Once writing is authorized, use the existing project files as the source of truth and update only the requested research document unless the user asks for broader edits.

## Session Handoff

This handoff file is located at `/private/tmp/AGENTS.md`, not inside the repository. In the next conversation, first verify that the active workspace is `/Users/luo/Desktop/AgentDefence` and that `research/` is writable. If not, report the exact mount/permission state before writing anywhere else.
