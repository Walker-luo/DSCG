# GrantBind v3.7 文档

当前默认 `static-task-v354`，运行标识 `DSCG_v3.7`。本目录说明当前实现和操作方式，实验名称不选择防御策略。

| 文档 | 内容 |
| --- | --- |
| [项目 README](../README.md) | 框架概览与快速开始 |
| [架构与层间通信](architecture.md) | L1、L2、L3、Monitor 的机制、共享数据与执行边界 |
| [模型与工具配置](model_tool_configuration.md) | 模型角色、连接、风险目录、默认配置与消融 |
| [评测入口](evaluation.md) | 选择 clean、攻击、筛选与诊断入口 |
| [完整任务测试](benchmark.md) | 范围、攻击、筛选、续跑和指标 |
| [小批量测试](partial_benchmark.md) | 注册前缀测试与筛选规则 |
| [注入目标筛选](injection_precheck.md) | 一次 GOAL 轨迹与 fliter.json |
| [结果文件](result_files.md) | 轨迹、诊断、审计回复、成本与错误 |
| [效用诊断](qwen_utility.md) | 按层定位漏做、误拒和消融干扰 |
| [Dashboard](dashboard.md) | 配置、历史对比和下载 |
| [当前实现与问题](framework_updates.md) | v3.7 默认、验证边界和未解决问题 |

跨会话工程状态见 [DV_STATE](../DV_STATE.md)，正式实验要求见 [AGENTS.md](../AGENTS.md)。
