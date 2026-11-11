# 已完成阶段的优化材料

当前运行代码为 **three-layer-v1**。这里收纳工程、评估或整理阶段已完成的文件；每个阶段的实验目标、备选机制与研究闸门分别列示。历史原文中的“尚未实施”描述属于当时设计，当前状态以本表和后续实施报告为准。

| 材料 | 已完成 / 当前保留 | 未完成、撤回或仅为设计 |
| --- | --- | --- |
| [三层基础方案](./3_layer_opt.md) · [实施报告](./three_layer_implementation_20261010.md) · [实施计划](./three_layer_implementation_plan_20261010.md) | L1来源视图、L2整批前置、原L3、平台架构；离线实施验收完成 | §5总成本目标与§7匹配模型消融尚未正式验收；CSA、DRV、LLM净化、自动恢复未启用 |
| [本次文档与交接核查](./framework_docs_cleanup_20261010.md) | README流程/例子、归档状态和平台交付核对 | 文档核查不证明ASR/TSR改善 |
| [实验配置与工作台](./dashboard_framework_ui_20261010.md) | 三层配置/预设、实际配置与路由统计、有效分母/成本口径、响应式验收 | 无新模型实验、CSA 或失败片段浏览器；旧 trace 缺失不重建 |
| [Partial结果报告](./partial_reporting_20261010.md) | 运行级摘要、位置索引、有界失败片段 | 无新评分oracle；平台独立失败片段浏览器未实施 |
| [V2后续报告](./framework_v2_followup_report.md) | Stage1宿主描述与准备读取判断保留；重放方法已纠正 | Stage2执行提示已评估并撤回，completion_prompt默认false；重复控制和真实E0仍待完成 |
| [V2实施记录](./framework_v2_report.md) | 任务隔离、授权简化、有限工具上下文等保留 | 当时试验参数不等于当前默认；不认定动态扩权/完整scope已实现 |
| [V2提案](./framework_optimization_v2_proposal_20261007.md) · [约束](./framework_optimization_direction_20261007.md) | 授权/审计主线已由后续报告落实；新三层由用户另行选用 | 原§5局部LLM工具返回处理未采用；当前L1是来源封装，不能称等价净化已完成 |
| [初轮方案](./framework_optimization_20261007.md) · [报告](./framework_optimization_report.md) · [复核](./framework_optimization_review_20261007.md) | 任务隔离、风险元数据与误拒问题已进入后续V2修正 | 有界重审/完成提示不作为默认；原重复模型验证矩阵不是全已执行清单 |
| [早期工程计划](./2026-10-05-workshop-engineering-optimization.md) · [报告](./workshop_optimization_report.md) | harness bookkeeping、紧凑trace与I3 fixtures | E0合成自检不等于真实闸门；旧八例I3 no_go被24valid/8scope的partial证据取代 |
| [项目结构整理](./project_structure_20261008.md) | 文档分工、路径与产物规则 | 既有历史输入缺失不重建，完整迁移存在已记录限制 |

仍待实现的 [L3 Checker](../L3_checker_opt.md) 与 [授权对照校准](../original_framework_direction_20261008.md) 留在 [顶层索引](../README.md)。正式E0/I3/I2状态以 [研究路线](../../../research/technical_route.md) 和 [I3报告](../../docs/i3_p0_stress_report.md) 为准。

旧稿件与CFP：[投稿草案](../archive/legacy_submission/ALMML_sub.md)、[原附件](<../archive/legacy_submission/AIMLL WS.pdf>)；旧docs/图表见 [归档索引](../archive/project_structure_20261008/README.md)。旧证据位于 [workshop/results/](../results/framework_optimization/)，所有新输出放 `workshop/artifacts/`。

本次移动前的原始字节与哈希单独保留；历史报告的路径更新只改变当前阅读入口，不重写原样本或测量。完整存放规则见 [AGENTS.md](../../AGENTS.md)。
