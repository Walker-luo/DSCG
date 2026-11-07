# 实验工具索引

从项目根目录执行，默认已激活 `ipi`。以下是当前保留的入口；模型运行需用户显式启动。

## 日常测量

| 入口 | 用途 | 说明 |
| --- | --- | --- |
| `python -m experiments.run_injection_precheck screen` | 直接GOAL能力预检、恢复历史尝试、冻结 injection 名单 | [预检指南](../docs/injection_precheck.md) |
| `python -m experiments.run_partial_benchmark` | 框架优化；每场景前三个用户×前三个注入 | [partial场景与cohort用法](../docs/partial_benchmark.md#对照与输出) |
| `python -m experiments.run_benchmark` | 所选场景全部注册任务，或显式 `--cohort` 的全用户筛选测量；默认四场景 | [全量指南](../docs/benchmark.md) |

两个入口均可用 `--suites travel banking slack` 跳过workspace。partial加 `--cohort PATH` 只过滤原前三个注入目标，不补位、不扩大用户任务，标记 `partial_screened`；full的 `--cohort` 保留所选场景全部用户，标记 `screened`。场景子集记录 `suite_scope=selected`，不能标成四场景全量。新配置使用新 `--name`，不覆盖历史实验。

## 校准、元数据与离线审计

| 模块 | 用途 |
| --- | --- |
| [l3_router_dataset.py](./l3_router_dataset.py) | 从现有trace准备L3数据集；独立标签和分组仍需审核 |
| [calibrate_l3_router.py](./calibrate_l3_router.py) | 使用独立分组数据生成冻结路由校准artifact |
| [generate_tool_metadata.py](./generate_tool_metadata.py) | 检查/导出注册工具风险目录，不调用模型 |
| [harness_audit.py](./harness_audit.py) | E0记录/fixture审计；合成自检不等于真实E0通过 |
| [i3_p0_stress.py](./i3_p0_stress.py) | 已有I3状态/边界fixture；当前partial证据见 [报告](../../research/Experiments/implementation_status.md) |
| [trace_diagnostics.py](./trace_diagnostics.py) | 只读启发式标注，保留原生评分，不作为独立安全oracle |

L3数据与校准步骤见 [L3实施报告](../workshop/completed/l3_algorithm_implementation_20261010.md)，工具配置见 [配置指南](../docs/model_tool_configuration.md)。

## 共享实现

`partial_controls.py` 负责任务选择/清单/缓存绑定；`partial_reporting.py` 负责报告；`injection_cohort.py` 与 `injection_cohort_compatibility.json` 负责冻结证据、明确版本兼容和筛选测量。这些不是需要单独启动的实验。

2026-10-17已移除当前目录中的硬编码旧数据绘图和10月12日专用模型诊断脚本，原始字节及路径/哈希映射见 [归档](../workshop/archive/experiments_docs_cleanup_20261017/README.md)。它们不是当前benchmark入口。

用户实验仍默认写入 `results/`。Agent临时运行须显式写入新的 `workshop/artifacts/<YYYYMMDD>_<task>/`；不在docs保存新测试图或诊断输出。
