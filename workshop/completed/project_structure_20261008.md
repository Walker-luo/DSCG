# DSCG Project Structure Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans for inline execution. Steps use checkboxes. This documentation-only plan uses consistency/hash verification rather than new runtime unit tests; user-selected artifact paths override skill scratch locations.

**Goal:** 精简当前文档入口，归档历史材料，固定 workshop 优化计划和 agent 测试产物的归属。

**Architecture:** README 说明当前两层框架和使用入口；docs 保留现行指南与 I3 报告；workshop 收纳优化计划、历史报告及诊断产物。迁移保存原始字节和哈希，不改防御逻辑或研究闸门。

**Tech Stack:** Markdown、Python 标准库、Git。

**Spec:** 本次用户的项目整理要求；[工程规则](../../AGENTS.md)；[研究路线](../../../research/technical_route.md)。

## Global Constraints

- 所有优化计划放在 workshop/；正式论文路线与 evidence record 仍在 ../research/。
- 新 agent 测试产物固定为 workshop/artifacts/<YYYYMMDD>_<task>/，不得写入根 result/ 或 results/。
- 保留既有 results/、download/、examples/ 和 workshop/results/ 数据；不回写历史 evidence。
- 不改变两层运行框架、I3 partial、E0 待验证或 I2 锁定状态；不增加模型调用。
- 保留用户原有 System_TODO.md 删除和 research 工作树修改。

## Review Focus

- 当前说明是否把对象/数据约束、三层候选或工程组件误写成已验证创新。
- 归档后的旧证据字节与原哈希是否一致；兼容链接退役是否显式记录。
- README、docs 和 AGENTS 的入口、命令、产物归属是否一致。
- 历史报告中的过期结论是否被误当成当前默认行为。
- 命令是否真实支持输出覆盖，特别是 full runner 尚无 --results-dir。

## Task 1: 当前入口与归档

**Files:** README.md、AGENTS.md、RESEARCH_STATUS.md、.gitignore、docs/README.md、docs/evaluation.md、docs/dashboard.md、docs/figures/README.md、workshop/README.md、workshop/verify_migration.py；历史材料归档于 workshop/archive/project_structure_20261008/。

**Interfaces:** 沿用历史迁移清单；新的清理清单显式补充退役旧路径；保持 workshop/3_layer_opt.md 所需的 follow-up 兼容链接。

- [x] 保存迁移前哈希和工作树；移动过期报告、项目介绍、图表及根目录 workshop 材料；删除冗余入口和缓存。
- [x] 精简 README，将详细评测和 dashboard 说明拆入当前指南；同步 AGENTS 和 workshop 索引。
- [x] 迁移检查默认只读；可用 --output 将新报告写入固定 artifact 根，禁止覆盖旧报告。
- [x] 运行结构/哈希/链接检查、迁移检查和 git diff --check，预期全部退出 0。
- [x] 一次最终独立只读审查；修正必要问题，提交 DSCG，向 ../research/paper/implementation_status.md 追加本次 evidence。

## Execution Ledger

- 2026-10-08: Base45583495382fe218b5911d477ea897082ed6175f；原有 System_TODO.md 删除保留。当前直接使用既有 workshop 分支与用户指定 checkout。
- Pre-flight: 清理会移除历史迁移验证依赖的旧符号链接；用本次显式 retirement 清单验证原始存储，不修改原清单/报告。三层方案引用的 follow-up 链接继续保留。

- Task 1 verification: 21/21材料、6/6快照、4/4退役别名、67/67受保护文件、5/5原迁移证据、293/293迁移文件；89个当前链接；CLI帮助2/2及输出拒绝负例2/2通过。最终独立只读审查：ready=yes，无实质问题。
- Final review: fresh-context read-only review passed; no fixes or deferred minors.
- Final: Ruling: 模型效果/创新/真实E0不在本次文档验收范围；保持待验证状态，不将结构整理写成防御增益。误用成本：会产生不受数据支持的结论。
- Final: Ruling: 原始大结果不重新全量哈希，只检查文件名/大小/mtime清单并明确限制；本轮不运行模型或修改结果。遗漏风险：相同大小/mtime的外部内容变化不由此检查发现。
- Final: Ruling: 既有ignored历史输入依赖维持现状；不补造缺失数据。代价：fresh clone仍不能完整核验本地历史证据。
- Final: Ruling: 用户既有System_TODO删除及research修改保留；只暂存本轮变更，状态记录追加采用选择性index补丁。代价：完成后工作树仍有用户原有修改。
- Task 1: complete — fresh structural verification exit0; document/layout commit and outgoing evidence tracked by PROJECT-STRUCTURE-CLEANUP-20261008 in research/paper/implementation_status.md.
- Postcommit: 发现两个结果目录的外部路径变动；冻结results快照检查退出1，迁移/文档/归档独立检查仍通过。原校验记录不覆盖；新增postcommit_observation.json，保留用户目录新名称。结果全量内容身份未独立证明。
