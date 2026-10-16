# 当前文档

| 入口 | 内容 |
| --- | --- |
| [项目 README](../README.md) | 当前three-layer-v3.1三层框架、使用命令和能力边界 |
| [模型、工具与运行参数](./model_tool_configuration.md) | 配置字段、信息获取、工具schema/风险分类、默认控制及排错 |
| [评测指南](./evaluation.md) | 模型配置、全部可选攻击、对照与日志口径 |
| [全量测试指南](./full_benchmark.md) | 当前框架与原生无防御 baseline、全部任务/攻击规模、运行命令、缓存及结果核对 |
| [框架与平台交接](./framework_updates.md) | 当前L2默认/可选能力、L1/L3后续修订、网页已接线与待办 |
| [Dashboard 指南](./dashboard.md) | 历史筛选、多版本对比及分析导出 |
| [I3 P0 压力测试报告](./i3_p0_stress_report.md) | 当前 `partial` 证据；未实现对象/数据范围约束 |
| [图表目录说明](./figures/README.md) | 用户绘图的默认位置与历史图表归属 |
| [Workshop 索引](../workshop/README.md) | 优化计划、调研、当前报告和历史归档 |

阶段验收报告、旧版项目介绍、旧图表及提示词草稿已移至 [历史归档](../workshop/archive/project_structure_20261008/README.md)。归档保留原始字节，不作为当前框架说明。

`framework_v2_followup_report.md` 仅保留为兼容链接，供已有三层调研引用原版本；当前阅读使用 [workshop 中的报告](../workshop/completed/framework_v2_followup_report.md)。其余旧入口退役情况与原哈希见[清理清单](../workshop/artifacts/20261008_project_structure/structure_manifest.json)。

本目录不存优化计划或 agent 测试产物；测试源码在 `tests/`，新产物固定在 `workshop/artifacts/<YYYYMMDD>_<task>/`。
