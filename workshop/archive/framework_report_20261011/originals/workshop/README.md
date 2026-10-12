# Workshop 优化状态索引

当前运行框架为 **three-layer-v1**。目录按工程落实状态管理：基础方案已实施的文件归入 completed；仍需实现的新机制留在顶层。完成工程不等于实验目标或研究闸门全部通过。

## 已完成与归档

| 方案 / 阶段 | 已完成 | 尚未完成或未采用 |
| --- | --- | --- |
| [三层基础方案](./completed/3_layer_opt.md) · [实施报告](./completed/three_layer_implementation_20261010.md) | L1来源视图、L2整批前置、原L3与平台架构同步 | 匹配四臂消融、总成本目标、引用保真和独立终态验证；CSA/DRV不在已实施范围 |
| [Partial报告优化](./completed/partial_reporting_20261010.md) | Markdown运行摘要、逐场景指标与有界失败片段 | 不改变原生评分，不提供新的安全oracle；尚未在平台增加独立失败片段浏览器 |
| [V2与其他历史阶段](./completed/README.md) | 各阶段已完成项及证据已归档 | Stage2执行提示撤回；旧方案里的重审/恢复、LLM净化等不能当作当前默认能力 |
| [本次文档与交接核查](./completed/framework_docs_cleanup_20261010.md) | README解释、方案归属和平台交付清单 | 真实实验结论仍由原始结果/独立核查决定 |
| [L3纯算法实现](./completed/l3_algorithm_implementation_20261010.md) | 固定评分、硬条件、分组校准工具、一次性路由交接和CLI成本账 | 独立真实数据、部署阈值、selective收益验收及网页专门控件 |
| [实验配置与工作台更新](./completed/dashboard_framework_ui_20261010.md) | 三层控件与预设、响应式布局、有效分母与两类模型成本、trace 统计覆盖 | 无新模型评测；CSA 与独立失败片段浏览器未实施 |

## 待完成验收的方案

| 方案 | 已落实的关联基础 | 未实施内容 / 当前决定 |
| --- | --- | --- |
| [L3 Checker优化](./L3_checker_opt.md) | 三层基础、公开读取免审、确定性权限前置 | 纯算法路由、分组校准工具、off/shadow/selective、受信交接已实现；真实独立数据/部署阈值与端到端验收仍待完成，不训练分类器 |
| [授权对照校准（历史归档）](./archive/framework_docs_cleanup_20261010/originals/workshop/original_framework_direction_20261008.md) | 原可信任务授权和当前动作审计 | 原候选入口已不在当前树；按保留归档阅读。机制未实施且暂停，不叠加到三层默认 |

[21篇来源目录](./3_layer_sources_20261008.json)保留在顶层供待优化项引用。旧 [DRV方案](./archive/3_layer_low_cost_20261009/originals/workshop/3_layer_opt.md)及[更早三层方案](./archive/3_layer_redesign_20261008/originals/workshop/3_layer_opt.md)仅作历史参考。方案中的样本数、成本算例和验收目标属于设计，不能当成已经运行的结果。

## 平台交接

[docs/framework_updates.md](../docs/framework_updates.md)列出逐项核查：三层架构展示、历史分析下载与多指标分图已交付。后续工作台更新补齐独立 L1 与 L2 前置控件、三层消融 / V2 对照和统计面板；CSA API/partial CLI模式已接入；网页CSA专门控件与独立失败片段浏览器仍未实施。

## 存放规则

| 路径 | 内容 |
| --- | --- |
| `workshop/*.md` | 待实施机制方案；README为索引 |
| [completed/](./completed/README.md) | 已完成工程/评估阶段的方案与报告，明确剩余项/撤回项 |
| `artifacts/<YYYYMMDD>_<task>/` | 所有新agent测试产物，日志与诊断固定放在此处 |
| `archive/` | 历史方案、原始字节及日期化迁移/修订清单 |
| [results/](./results/framework_optimization/) | 已有历史证据与脚本，不新增运行输出 |

正式论文路线/计划在兄弟 [research](../../research/technical_route.md)。测试源码在tests，用户正式结果/导出留在 [results/](../results/) 和 [download/](../download/)。Agent partial实验必须显式传新 `--results-dir workshop/artifacts/<YYYYMMDD>_<task>/partial_benchmark`。其余规则见 [AGENTS.md](../AGENTS.md)。

`python workshop/verify_migration.py` 默认只读，不改旧证据。完整历史检查仍受研究侧既有兼容路径删除影响；本次当前文件、原字节和链接检查记录于本次阶段报告，不能把局部通过称为完整迁移通过。
