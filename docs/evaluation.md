# 评测入口索引

从项目根执行，使用当前已激活的后端环境。当前代码为v3.5.4／static-task-v354，后续保存为v3.6并在此基础上优化；两阶段授权，legacy需显式选择；[配置](model_tool_configuration.md)与[运行参数](benchmark.md#可选控制与日志)共用。

| 目的 | 入口 | 范围／输出 |
| --- | --- | --- |
| 检查安装 | `python -m dscg.benchmark_catalog` | 离线检查实际后端与场景，无模型调用 |
| 完整任务对照 | [run_benchmark.py](../experiments/run_benchmark.py) | 所选场景全部注册用户／目标；默认results/benchmarks |
| 小批量排错 | [run_partial_benchmark.py](../experiments/run_partial_benchmark.py) | 每场景注册前3用户×前3目标；默认results/partial_benchmark |
| 生成目标排除表 | [run_injection_precheck.py](../experiments/run_injection_precheck.py) `screen` | 每目标一次无防御直接GOAL；未通过即排除，输出fliter.json；默认results/injection_precheck |
| 分阶段诊断 | [utility_stages.py](../experiments/diagnostics/utility_stages.py) | 离线导出／比较／轨迹信号，见[诊断指南](qwen_utility.md) |
| AgentDyn低成功率诊断 | [agentdyn_zero_rates.py](../experiments/diagnostics/agentdyn_zero_rates.py) | 只读已有原生轨迹、授权差集、阻挡与投递信号 |
| 检查／复制工具目录 | [generate_tool_metadata.py](../experiments/tools/generate_tool_metadata.py) | 无模型调用；不创建真实工具实现 |
| 汇总旧运行路由 | [summarize_results.py](../experiments/diagnostics/summarize_results.py) | 只读输入并新增路由报告，见[结果指南](result_files.md) |

完整任务、partial和目标排除分别见[full](benchmark.md)、[partial](partial_benchmark.md)、[screen](injection_precheck.md)。full保留全部所选用户；partial只排除原目标前缀，不补位。测量`--goal`默认关闭，开启后用当前测量pipeline逐目标检查；旧`--cohort`已拒绝，历史数据仍可读。计划数量集中在[任务范围](benchmark.md#1-使用哪个入口)。

新CLI结果统一为 `<results-dir>/<backend>/<model>_<name>/`；主JSON、sidecar、manifests与成本说明集中在[结果文件](result_files.md)。用户正式数据保留在results；agent检查显式指定新的 `workshop/artifacts/<YYYYMMDD>_<task>/` 输出根。

TSR／ASR使用原生标签，错误和缺失单列。合成诊断、离线通过与小样本均不证明完整防御效果；当前E0 pending、I3 partial、I2 locked。其他工具见[experiments索引](../experiments/README.md)。
