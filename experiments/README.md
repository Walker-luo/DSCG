# 实验工具索引

从DSCG目录执行，默认已激活ipi。主目录只保留三个日常运行入口，其他代码按用途归类。模型运行由用户显式启动。

## 日常测量

| 入口 | 用途 | 说明 |
| --- | --- | --- |
| `python -m experiments.run_injection_precheck screen` | 直接GOAL能力预检、恢复历史尝试、冻结injection名单 | [预检指南](../docs/injection_precheck.md) |
| `python -m experiments.run_partial_benchmark` | 默认每场景前三个用户×前三个注入 | [小批量指南](../docs/partial_benchmark.md) |
| `python -m experiments.run_benchmark` | 所选场景全部任务，或cohort冻结目标；默认四场景 | [完整任务指南](../docs/benchmark.md) |

两个测量入口均支持 `--suites travel banking slack` 跳过workspace。partial的cohort仅过滤原注入前缀，不补位，标记partial_screened；full的cohort保留全部用户，标记screened。DSCG CLI默认shadow；baseline/NoChecker默认off。任务前缀和结果目录保持不变。新typical为ignore_previous、important_instructions、tool_knowledge；injecagent保留显式/all选择。

## 目录分工

```text
experiments/
├── run_benchmark.py
├── run_partial_benchmark.py
├── run_injection_precheck.py
├── common/         # 任务选择、清单、报告、cohort与版本兼容
├── diagnostics/    # E0、I3与轨迹诊断；日常测量无需单独运行
├── calibration/    # L3独立标签数据与阈值校准
└── tools/          # 工具风险元数据检查与导出
```

| 模块 | 用途 |
| --- | --- |
| [common/partial_controls.py](./common/partial_controls.py) | full/partial任务选择、冻结清单、源码身份和缓存绑定 |
| [common/partial_reporting.py](./common/partial_reporting.py) | 测量报告、失败索引和成本统计 |
| [common/injection_cohort.py](./common/injection_cohort.py) | 冻结预检证据、恢复/复用与筛选测量；[兼容映射](./common/injection_cohort_compatibility.json)只允许已知源码集合 |
| [diagnostics/harness_audit.py](./diagnostics/harness_audit.py) | E0合成记录审计；也向runner/Dashboard提供原有评分辅助函数 |
| [diagnostics/i3_p0_stress.py](./diagnostics/i3_p0_stress.py) | I3状态/边界fixture；当前partial证据见 [研究交接](../../research/Experiments/implementation_status.md) |
| [diagnostics/trace_diagnostics.py](./diagnostics/trace_diagnostics.py) | 只读启发式轨迹标注，不改native评分，不作为独立安全oracle |
| [calibration/l3_router_dataset.py](./calibration/l3_router_dataset.py) | 从显式独立标注准备L3数据集 |
| [calibration/calibrate_l3_router.py](./calibration/calibrate_l3_router.py) | 使用独立分组数据生成冻结校准artifact |
| [tools/generate_tool_metadata.py](./tools/generate_tool_metadata.py) | 离线检查/导出注册工具风险目录 |

## 专项工具用法

新模块路径示例：

```bash
python -m experiments.diagnostics.harness_audit --help
python -m experiments.diagnostics.i3_p0_stress --help
python -m experiments.calibration.l3_router_dataset --help
python -m experiments.calibration.calibrate_l3_router --help
python -m experiments.tools.generate_tool_metadata --help
```

专项工具按需使用；I3仍为partial，E0合成自检不等于真实E0通过。L3准备与校准方法见 [L3方案](../workshop/L3_checker_opt.md)，元数据用法见 [配置指南](../docs/model_tool_configuration.md)。

旧顶层专项模块不保留转发壳；历史报告中的旧命令保留当时上下文，复跑使用上述新路径。原始字节及路径/哈希映射见 [本次归档](../workshop/archive/experiments_layout_20261017/README.md)。先前移除的专用诊断/绘图代码仍在 [早期归档](../workshop/archive/experiments_docs_cleanup_20261017/README.md)，不恢复到当前目录。

已知旧screen目录与cohort通过明确源码/脚本哈希绑定兼容，旧manifest、attempt与名单不改写；未知源码或任务变化仍拒绝。新的攻击测量使用新name，`--force-rerun`不绕过配置绑定。

用户实验仍默认写入results。Agent临时检查显式写入新的workshop/artifacts任务目录，不改写历史实验。

显式续跑：两个入口均支持 `--reuse --name <原名称>`，未指定attack/suites时恢复原计划，包括旧四攻击；与显式force-rerun互斥并覆盖环境强制设置。共享校验位于 [common/benchmark_reuse.py](./common/benchmark_reuse.py)，独立[测量兼容映射](./common/benchmark_reuse_compatibility.json)不等同于预检资格。规则与命令见 [公共续跑说明](../docs/benchmark.md#显式续跑示例)。
