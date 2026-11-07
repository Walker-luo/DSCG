# v3.7 评测入口

从项目根执行。当前默认 `static-task-v354 / DSCG_v3.7`，本轮实验以 AgentDojo 为范围。模型与工具设置见 [配置](model_tool_configuration.md)，机制见 [架构](architecture.md)。

| 目的 | 入口 | 范围 |
| --- | --- | --- |
| 检查安装 | `python -m dscg.benchmark_catalog` | 离线读取实际后端身份与场景 |
| clean／完整攻击 | [run_benchmark.py](../experiments/run_benchmark.py) | 所选场景全部注册任务 |
| 小批量排错 | [run_partial_benchmark.py](../experiments/run_partial_benchmark.py) | 注册前 3 用户 × 前 3 目标 |
| 生成 fliter.json | [run_injection_precheck.py](../experiments/run_injection_precheck.py) `screen` | 每目标一次无防御 GOAL，成功保留 |
| 分阶段诊断 | [utility_stages.py](../experiments/diagnostics/utility_stages.py) | 离线导出、比较与轨迹信号 |
| 检查／复制工具目录 | [generate_tool_metadata.py](../experiments/tools/generate_tool_metadata.py) | 离线生成当前后端风险配置 |
| 路由报告 | [summarize_results.py](../experiments/diagnostics/summarize_results.py) | 从已有轨迹生成报告 |

建议顺序为匹配 baseline clean 与 v3.7 clean → 生成同模型 fliter.json → 使用同一名单运行 baseline 与 v3.7 攻击 → 按实际共同任务键比较。生成名单和测量中的 `--goal` 是不同步骤；测量 GOAL 默认关闭，详见 [筛选](injection_precheck.md)。

正式 workshop 运行指定 `--results-dir results/workshop`，产物追加 `<backend>/<model>/<name>/`。agent 临时验证改用新建 `workshop/artifacts/<YYYYMMDD>_<task>/` 输出根。运行范围、续跑和错误处理见 [完整指南](benchmark.md)，文件及成本口径见 [结果指南](result_files.md)。

TSR／ASR 按原生有效标签统计，GOAL、错误和缺失另列。clean ASR 不适用。组件诊断和小样本结果不等于完整任务效果。NoL2 消融当前存在元数据缺失干扰，见 [当前问题](framework_updates.md)。
