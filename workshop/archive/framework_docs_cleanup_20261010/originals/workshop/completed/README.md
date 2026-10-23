# 已完成阶段的优化材料

这里收纳已完成实施、评估或整理阶段的方案与报告。**目录归属不代表方案内所有机制都已启用**；当前运行代码为three-layer-v1，复用V2编译/审计，重审和完成提示关闭。新候选见 [待优化索引](../README.md)。

| 材料 | 实际状态 |
| --- | --- |
| [三层基础实施](./three_layer_implementation_20261010.md) · [实施计划](./three_layer_implementation_plan_20261010.md) | L1来源视图与L2整批前置已实施，L3复用；真实模型增益未测 |
| [Partial 结果摘要与失败片段](./partial_reporting_20261010.md) | 运行级摘要/定位与有界片段已实施；原生指标不重评分，无模型调用 |
| [V2 后续报告](./framework_v2_followup_report.md) | stage1 审计补修保留；stage2 执行提示已评估并撤回 |
| [V2 实施记录](./framework_v2_report.md) | 两层优化已实施；历史试验参数不等于当前默认 |
| [V2 提案](./framework_optimization_v2_proposal_20261007.md) · [简化约束](./framework_optimization_direction_20261007.md) | 当时的设计依据，以后续报告记录的实现/撤回状态为准 |
| [初轮方案](./framework_optimization_20261007.md) · [报告](./framework_optimization_report.md) · [复核](./framework_optimization_review_20261007.md) | 已评估的早期阶段，部分方案被 V2 替代 |
| [早期工程计划](./2026-10-05-workshop-engineering-optimization.md) · [报告](./workshop_optimization_report.md) | harness/trace 阶段；旧八例 I3 no_go 已被 partial 证据取代 |
| [项目结构整理](./project_structure_20261008.md) | 文档分工与产物规则已落地；最新目录规则见 [AGENTS](../../AGENTS.md) |

阶段证据与诊断脚本保留在 [workshop/results/](../results/framework_optimization/)，新 agent 输出继续固定在 `workshop/artifacts/`。

旧稿件及 CFP：[投稿工作稿](../archive/legacy_submission/ALMML_sub.md)、[原附件](<../archive/legacy_submission/AIMLL WS.pdf>)。旧 docs 与图表见 [归档索引](../archive/project_structure_20261008/README.md)。历史内容可能含过期路径或结论，不能据此重开研究路线或覆盖旧输出。

搬迁只修正当前阅读链接；原文存于 [原始版本](../archive/workshop_cleanup_20261008/originals/)，路径与哈希见 [搬迁清单](../artifacts/20261008_workshop_cleanup/relocation_manifest.json)。正式论文路线与状态仍在兄弟 [research](../../../research/technical_route.md)。
