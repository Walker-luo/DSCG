# DSCG Research Handoff

## Project

DSCG is a research prototype for defending tool-using LLM agents against indirect prompt injection (IPI). The intended project root is `/Users/luo/Desktop/AgentDefence`, with the implementation under `DSCG/` and a deliberately separate research directory under `research/`.

The repository is writable at `/Users/luo/Desktop/AgentDefence/DSCG`. Keep it separate from the sibling `research/` repository: do not create a second research directory under `DSCG/`, and do not copy paper plans into this repository.

## Research Handoff

论文问题、文献、创新点和实验协议统一维护在项目根目录的 `research/`。本仓库只实现研究侧已经解锁的工程任务。先读取 `../research/technical_route.md`，完成后按 `../research/paper/implementation_status.md` 回报，不在本仓库复制论文计划或自行宣布新颖性。

## Project Status (from readable `DSCG/System_TODO.md`)

- P0.1–P0.5 are recorded as implemented: fail-closed authorization state, authorization before candidate generation, complete mediation with a Reference Monitor and one-use execution tickets, structured audit decisions and trace levels, and explicit tool-risk metadata.
- Existing implementation is still primarily tool-level. Parameter/object-level Task Contracts and provenance-aware source-to-sink policy are future work in `DSCG/System_TODO.md`, and are locked until research-side route selection.
- The TODO's own research hypotheses include parameter-level authorization, explicit provenance for sensitive-source-to-external-sink flows, and LLM audit as a supplemental signal rather than the security root.
- Existing `research/ideas.md` calls contribution candidates hypotheses, not proven novelty. Preserve that caution.
- Current implementation status is recorded in `research/paper/implementation_status.md`; do not infer parameter-level provenance or I2 coverage from P0 code.
- Relevant research files include `research/technical_route.md`, `research/paper/implementation_status.md`, `research/paper/Paper_TODO.md`, `research/papers.md`, `research/ideas.md`, `research/contrast.md`, and `research/related_papers.md`.

## Current Engineering Queue

The active queue is defined only by [`../research/technical_route.md`](../research/technical_route.md). As of `route-2026-09-30`, `E0-HARNESS-AUDIT` and `I3-P0-STRESS` are ready; `I2-FIXTURE` and `I2-PILOT` remain locked until the harness audit and research-side decision pass. The old field-level provenance/source-to-sink proposal is closed as `No-Go` and must not be revived under a new name.

For each ready task, keep the implementation change in `DSCG/`, run the stated checks, and append one evidence record to [`../research/paper/implementation_status.md`](../research/paper/implementation_status.md). A task report must include the exact command, exit code, code revision, working-tree state, artifact paths/hashes, sample denominators, limitations, and one next action. Research-side files are edited only in `research/`.

## Working Rules

- Do not claim "first", formal guarantees, complete taint tracking, or general defense without evidence.
- Do not treat capability-graph components, audit logs, or execution tickets alone as the paper's novel algorithm.
- Keep the first study to text-based, single-agent tool use and external-content-to-tool-action flows. Defer multimodal, multi-agent, MCP, and online learning extensions.
- Preserve existing project changes. Do not overwrite result data or local model/tool credentials.
- Do not edit paper plans from `DSCG/`; use `research/technical_route.md` for incoming work and `research/paper/implementation_status.md` for outgoing status.

## Session Handoff

At the start of a new session, verify that the workspace is `/Users/luo/Desktop/AgentDefence`, read `research/technical_route.md`, and inspect `research/paper/implementation_status.md` before making research-driven changes. Do not infer a paper claim from code or a smoke benchmark. Keep the two repositories independently reviewable and do not merge them into a new nested checkout.
