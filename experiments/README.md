# 实验入口

从 BaseIntent 根目录激活 `ipi` 或 `ipi-agentdyn`。同一命令按实际 Python 导入路径、来源、版本和 revision 识别后端；环境名不决定后端，场景不能跨后端混选。

```bash
python -m baseintent.benchmark_catalog
```

该命令只做元数据检查，不调用模型。

| 入口 | 范围与指南 |
| --- | --- |
| `python -m experiments.run_benchmark` | 所选场景全部注册任务；[full/baseline/clean/cohort/reuse](../docs/benchmark.md) |
| `python -m experiments.run_partial_benchmark` | 每场景注册前 3 用户 × 前 3 目标；[partial](../docs/partial_benchmark.md) |
| `python -m experiments.run_injection_precheck screen` | 每个 GOAL 一次完整轨迹，冻结成功名单；[筛选](../docs/injection_precheck.md) |

默认 typical 为 ignore_previous、important_instructions、tool_knowledge。多个可运行攻击按独立进程运行，内部顺序保持；clean、单攻击和 screen 顺序执行。Full cohort 保留全部用户，partial 仅过滤原注入前缀、不补位。新 CLI 路径为 `<results-dir>/<backend>/<model>_<name>/`。

```text
experiments/
├── run_benchmark.py
├── run_partial_benchmark.py
├── run_injection_precheck.py
├── common/          # 范围、名单、reuse、计分与报告
├── diagnostics/     # 轨迹诊断与工程审计
├── calibration/     # 独立标签/历史路由校准工具
└── tools/           # 工具风险元数据核对与导出
```

专项入口按需查看 `--help`：

```bash
python -m experiments.diagnostics.harness_audit --help
python -m experiments.diagnostics.i3_p0_stress --help
python -m experiments.diagnostics.summarize_results --help
python -m experiments.calibration.l3_router_dataset --help
python -m experiments.calibration.calibrate_l3_router --help
python -m experiments.tools.generate_tool_metadata --help
```

工程自检或启发式诊断不改原生评分，也不证明真实评测/一般安全通过。历史阈值校准不控制当前固定 public/internal 读取免审。工具目录根据实际后端解析，不自动推断或弱化副作用。

新检查产物使用 `artifacts/<日期>_<任务>/`，full/partial 显式 `--results-dir`；默认用户测量根仍在 `results/`。现有历史结果、凭证和证据不覆盖、不迁移。配置见[模型与工具](../docs/model_tool_configuration.md)，报告/成本/原始回复见[结果文件](../docs/result_files.md)，框架解释见[BaseIntent](../docs/framework.md)。
