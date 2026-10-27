# BaseIntent 文档

| 指南 | 内容 |
| --- | --- |
| [框架](framework.md) | L1/L2/L3、宿主进度、Monitor、公式与边界 |
| [模型与工具配置](model_tool_configuration.md) | 两个环境、凭证、配置优先级、工具元数据与默认值 |
| [评测入口](evaluation.md) | 离线检查、在线评测及证据口径 |
| [完整评测与公共参数](benchmark.md) | Full、baseline、clean、攻击、cohort、续跑 |
| [小批量评测](partial_benchmark.md) | 注册前缀范围与低成本对照 |
| [目标筛选](injection_precheck.md) | 单次 GOAL 预检、冻结名单与中断恢复 |
| [结果文件](result_files.md) | 原生评分、诊断附件、成本与失败索引 |
| [Dashboard](dashboard.md) | 启动、实际配置、历史比较与导出 |
| [迁移](migration.md) | BaseIntent 命名、环境兼容与历史读取 |
| [框架更新入口](framework_updates.md) | 当前协议、验收限制 |
| [Qwen 效用入口](qwen_utility.md) | 当前有限观察及后续对照要求 |

文档从当前源码及有效配置解释行为；历史结果保持原身份。新运行、日志和检查产物使用 `artifacts/<日期>_<任务>/`，不覆盖既有结果。维护记录见 [maintenance.md](maintenance.md)。
