# Workshop 工程索引

当前代码为 **DSCG_v3.5.4 / static-task-v354**。本目录保存工程方案与阶段记录；运行方法和机制以[项目README](../README.md)、[当前框架](../docs/framework_updates.md)、[配置指南](../docs/model_tool_configuration.md)为准，进行中问题和验证状态见 [DV_STATE.md](../DV_STATE.md)。

## 当前工作入口

| 材料 | 用途 |
| --- | --- |
| [v3.5.4专项分析](../analysis/v3-5-4.md) | 本轮同键对照、实际收益与未解决问题 |
| [v3.5.4优化报告](completed/v354_optimization_20261028.md)／[已执行计划](completed/v354_implementation_plan_20261028.md) | 实际调用、错误、源码与验证边界 |
| [v3.5.3正式结果分析](../analysis/v3-5-3.md) | 当前配对结果、效用退步、错误与限制 |
| [重点失败案例](../analysis/details.md) | 保留的逐案例证据；按其记录版本解读 |
| [后续工作](../analysis/plan.md) | 当前未解决问题，不重开历史campaign |
| [v3.5.3优化报告](completed/v353_optimization_20261027.md) | 已完成在线范围、实际调用／用量及遗留问题 |
| [v3.5.3实施计划](completed/v353_implementation_plan_20261027.md) | 已执行阶段的计划记录，不作为新的调用授权 |
| [benchmark日志定位](completed/benchmark_task_log_ids_20261027.md) | 当前任务／GOAL错误控制台定位 |

## 保留的研究候选

[L1投影余项](L1_opt.md)、[L2授权余项](L2_opt.md)、[L3路由余项](L3_checker_opt.md)只记录现有实现边界与未验证方向，不自动解锁新机制、放宽权限或改变当前默认。

## 历史材料

完整阶段目录见 [completed](completed/README.md)，原始方案和迁移字节在 `archive/`。以下顶层日期化方案保留其原阶段上下文，不是当前待执行交接：

- [2026-10-22 L2／L3方案](L2_L3_optimization_20261022.md)：v3.4阶段，已由后续版本替代。
- [2026-10-23 v3.5迭代](L2_L3_v35_live_iterations_20261023.md)与[后续campaign](L2_L3_v35_followup_20261023.md)：均已关闭。
- [2026-10-19 Qwen诊断方案](qwen_utility_20261019.md)：历史候选与固定输入诊断。
- [v3.4实施计划](v34_utility_optimization_20261025.md)、[v3.5实施计划](v35_optimization_20261026.md)、[v3.5.1后续候选](v351_next_optimization_20261026.md)：阶段设计记录；采用、撤回和实际验证以各阶段报告及当前代码为准。

历史文件里的“当前”“默认”、预算和测试数字只适用于记录阶段。不得据此覆盖当前代码、重新执行已完成计划或追加关闭campaign的模型调用。

## 存放与验证

- `workshop/`：待讨论或仍有未验收部分的工程方案；不复制正式论文计划。
- `completed/`：阶段计划、实施／诊断报告；完成工程不等于通过研究或安全门槛。
- `artifacts/<YYYYMMDD>_<task>/`：新agent日志、检查、临时测量、快照和验证记录，使用新目录。
- `archive/`及旧`results/`：历史原始材料，保持字节与证据身份，不作为当前操作规则。

测试源在 `tests/`，可复用入口在 `experiments/`；用户正式结果与导出保持在项目 `results/`、`download/`。在线只用Qwen3.7-Flash及既有授权规则，详见 [AGENTS.md](../AGENTS.md)。

`python workshop/verify_migration.py`是早期目录迁移的历史核验工具，不能证明当前框架正确或完整历史证据齐全；既有缺失路径／哈希问题不得补造为通过。
