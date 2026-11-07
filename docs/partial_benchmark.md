# v3.7 小批量测试

使用 `experiments.run_partial_benchmark`，默认 `static-task-v354 / DSCG_v3.7`。模型、攻击、错误处理及运行控制与 [完整测试](benchmark.md) 共用，以下命令会调用真实模型。

## 默认任务范围

每场景固定取注册顺序前 3 用户 × 前 3 注入目标，seed 不改变前缀。AgentDojo 四场景 clean 计划 12 例，typical 计划 108 例，筛选后按实际范围报告。

先取前缀，再应用 fliter 和可选 GOAL；被排除目标不补位。partial 无法覆盖后续用户任务，专项问题须选择真正包含它们的评测范围。

## 对照与输出

使用同一环境、主模型与范围，选择未使用的运行名。

```bash
python -m experiments.run_partial_benchmark --baseline --clean \
  --results-dir results/workshop --name baseline_partial_doc01_clean
python -m experiments.run_partial_benchmark --clean \
  --results-dir results/workshop --name v3.7_partial_doc01_clean
```

无攻击时不运行 GOAL，ASR 不适用。默认框架自动启用两阶段 L2，无需额外传 profile。消融入口与已知 NoL2 干扰见 [配置](model_tool_configuration.md#消融与默认值)。

默认输出为 `results/partial_benchmark/<backend>/<model>/<name>/`；上述命令写入 `results/workshop/<backend>/<model>/<name>/`。agent 临时验证指定新的 workshop/artifacts 任务目录。根 summary 和失败索引说明见 [结果文件](result_files.md)。

## 筛选注入目标

先用 [独立预检](injection_precheck.md) 生成名单，baseline 和 v3.7 使用同一文件。

```bash
python -m experiments.run_partial_benchmark --suites banking slack \
  --fliter /absolute/path/to/fliter.json \
  --results-dir results/workshop --name v3.7_partial_doc01 --progress
```

仅传 fliter 不重做预检。需要当前测量框架筛选时再加 `--goal`，每目标一条完整轨迹，跨攻击共用判定；失败排除，错误另列且非零退出，已开始目标不重试。全被筛除时指标为 N/A。clean／DoS 不接受这两个参数。

<a id="并发运行"></a>

## 按攻击并行运行

多个攻击各用独立进程，攻击内顺序执行，单攻击和 clean 顺序执行。`--progress` 只控制显示；有效／错误／未完成数量以报告为准。CLI router 默认 shadow，off 仍审计非免审批次。

## 中断续跑

```bash
python -m experiments.run_partial_benchmark --reuse \
  --fliter /absolute/path/to/fliter.json \
  --results-dir results/workshop --name v3.7_partial_doc01
```

保留有效配置和输出根，未给场景／攻击时恢复原计划；baseline／clean／goal 仍需原参数。完整错误缓存不自动重试，配置变化使用新名称。主模型参数 JSON 错误会终止当前任务并排除有效分母，后续任务继续，详见 [完整测试](benchmark.md)。
