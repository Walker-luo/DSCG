# 当前文档

新实验同时支持AgentDojo（ipi）与AgentDyn（ipi-agentdyn），只切换环境即可自动选择。安装、自检、两套full/partial/clean和baseline命令从[完整测试指南](./benchmark.md)开始。旧结果可读，本次不迁移旧缓存/cohort，跨基准不混用分母。

| 入口 | 内容 |
| --- | --- |
| [项目 README](../README.md) | 当前three-layer-v3.3三层框架、使用命令和能力边界 |
| [实验工具索引](../experiments/README.md) | 当前测量、校准、元数据与审计入口；区分入口与共享实现 |
| [模型、工具与运行参数](./model_tool_configuration.md) | 配置字段、信息获取、工具schema/风险分类、默认控制及排错 |
| [测试文件索引](./evaluation.md) | 测试指南、主要入口、配置与结果文件的用途 |
| [完整任务测试指南](./benchmark.md) | run_benchmark的baseline/DSCG、clean、场景/cohort、公共攻击与指标口径 |
| [结果文件与L3汇总](./result_files.md) | 精简报告、完整失败索引、shadow/selective统计、旧目录离线补充与未知值口径 |
| [小批量测试指南](./partial_benchmark.md) | run_partial_benchmark的3×3前缀、场景/cohort、shadow与续跑 |
| [Injection 目标预检](./injection_precheck.md) | 实时进度、失败复测、同基准状态续跑与冻结名单；full/partial各自支持cohort |
| [框架与平台交接](./framework_updates.md) | 当前L2默认/可选能力、L1/L3后续修订、网页已接线与待办 |
| [Dashboard 指南](./dashboard.md) | 历史筛选、多版本对比及分析导出 |
| [Workshop 索引](../workshop/README.md) | 优化计划、调研、当前报告和历史归档 |

阶段验收报告、旧版项目介绍、旧图表及提示词草稿已移至 [历史归档](../workshop/archive/project_structure_20261008/README.md)。归档保留原始字节，不作为当前框架说明。

硬编码旧数据绘图和阶段专用模型探针已从experiments退役，见 [2026-10-17清理归档](../workshop/archive/experiments_docs_cleanup_20261017/README.md)。当前文档只保留配置、评测、预检、平台说明，阶段过程与历史统计从workshop查阅。

V2历史报告从 [workshop报告](../workshop/completed/framework_v2_followup_report.md)查阅。已移除的旧docs报告与兼容别名不恢复，也不列作当前入口。

本目录不存优化计划或 agent 测试产物；测试源码在 `tests/`，新产物固定在 `workshop/artifacts/<YYYYMMDD>_<task>/`。
