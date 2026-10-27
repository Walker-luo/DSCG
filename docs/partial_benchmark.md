# 小批量评测

`experiments.run_partial_benchmark` 保留每场景注册顺序前 3 个用户与前 3 个注入目标，默认当前后端全部场景。AgentDojo 计划 clean 12 / typical 108，AgentDyn 计划 9 / 81；不支持、错误与 GOAL 单列，实际分母以输出为准。`--suites` 可缩小场景，不能跨后端混选。

## 对照与输出

从 BaseIntent 根目录激活 `ipi` 或 `ipi-agentdyn`。以下命令会调用真实模型，两个对照保持相同环境、任务、攻击、模型配置和新名称：

```bash
python -m experiments.run_partial_benchmark --baseline --suites banking slack \
  --attack ignore_previous --name baseintent_partial_baseline_01 \
  --model-config config/models.local.toml \
  --results-dir artifacts/20261027_example/partial_baseline --progress

python -m experiments.run_partial_benchmark --suites banking slack \
  --attack ignore_previous --name baseintent_partial_01 \
  --model-config config/models.local.toml \
  --results-dir artifacts/20261027_example/partial --progress
```

clean 用 `--clean`，原生 clean 再加 `--baseline`。冻结目标用 `--cohort PATH`，只过滤原前 3 目标，不补位，标记 `partial_screened`；保留前三用户。Full cohort 则保留全部注册用户，两种范围不能合并。

共享参数、攻击、进程调度、baseline 和 reuse 规则见[完整指南](benchmark.md)。默认输出分类根为 `results/partial_benchmark`，新 CLI 路径均为 `<results-dir>/<backend>/<model>_<name>/`。代理检查显式写入新的 `artifacts/<日期>_<任务>/`。

可用 `--task-manifest PATH` 固定 partial 任务 ID，或用 `--write-task-manifest PATH` 离线导出后退出。新 profile、投影、请求格式、进度或审计策略必须新 name，旧测量缓存不跨策略复用；冻结名单不因此重筛。诊断与评分口径见[结果文件](result_files.md)，有限在线观察见[框架](framework.md)。
