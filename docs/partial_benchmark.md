# 小批量测试

当前代码为v3.5.4，后续保存为v3.6并作为优化基线；使用 `experiments.run_partial_benchmark`。安装、模型连接和公共参数见[完整指南](benchmark.md)及[配置](model_tool_configuration.md)。以下运行命令会调用真实模型。

## 默认任务范围

每个所选场景取**注册顺序前3用户×前3注入目标**，seed不改变该前缀。AgentDojo默认clean12、typical108组合；AgentDyn为clean9、typical81计划／72可执行，其dailylife的tool_knowledge组不支持。

`--suites`仅选当前后端场景。partial不能覆盖banking u11／u15、Slack u13／u17等后续任务，不能当作这些问题已验证。完整所选任务使用run_benchmark。

## 对照与输出

```bash
# 同一环境／主模型／范围，新名称
python -m experiments.run_partial_benchmark --baseline --name baseline_partial_01 --progress
python -m experiments.run_partial_benchmark --name v36_static_partial_01 --progress

# 显式单次授权对照；AgentDojo示例
python -m experiments.run_partial_benchmark --suites banking slack \
  --prompt-profile legacy --name v36_legacy_bs_01 --progress
```

默认static先抽任务视图再编译权限；单次授权用显式legacy。运行名不选择策略。static支持NoL2／NoChecker消融（路由设off），baseline仍原生legacy；其他历史候选要求L2／L3；详见[profile说明](qwen_utility.md)。

结果为 `results/partial_benchmark/<backend>/<model>_<name>/`。agent临时测试另设新的 `--results-dir workshop/artifacts/<YYYYMMDD>_<task>/partial_benchmark`。先看根summary和failure_cases，字段见[结果文件](result_files.md)。

## 干净任务对照

```bash
python -m experiments.run_partial_benchmark --baseline --clean --name baseline_partial_clean_01
python -m experiments.run_partial_benchmark --clean --name v36_partial_clean_01
```

无攻击／GOAL预检，ASR不适用；范围仍是前3用户，不代表全部97／60任务。

## 筛选injection目标

使用最小排除文件（格式见[预检指南](injection_precheck.md)）：

```bash
python -m experiments.run_partial_benchmark --baseline --suites banking slack \
  --fliter /absolute/path/to/fliter.json --name baseline_partial_filtered_01
python -m experiments.run_partial_benchmark --suites banking slack \
  --fliter /absolute/path/to/fliter.json --goal --name v36_partial_goal_01
```

先取原前3用户×原前3目标，再应用排除表；不补位。`--goal`默认关闭；开启后，每个保留目标按当前测量pipeline运行一次直接GOAL，跨攻击共享结果，只有通过目标进入计分。失败排除，错误单独跳过并退出1；均不计TSR／ASR，已开始GOAL不重试。全部剔除时不计分、指标N/A；baseline与DSCG的GOAL可能保留不同集合，配对比较须使用实际共同任务键。旧`--cohort`已拒绝，历史结果仍可读取，不迁移。

<a id="并发运行"></a>

## 按攻击并行运行

多个攻击分独立进程，攻击内顺序执行，单攻击／clean仍顺序；`--progress`只控制显示。默认CLI router shadow，但无sink非敏感读取在三模式均固定免审，off不关闭L3。攻击选择、配置、错误隔离和退出码共用[完整指南](benchmark.md)。

## 中断续跑

```bash
python -m experiments.run_partial_benchmark --reuse --name v36_static_partial_01
```

保留模型／profile／name／输出根及有效配置；未给攻击／场景恢复原计划，baseline／clean及fliter／goal仍需保留对应选项。reuse与force-rerun互斥，完整错误缓存不自动重试；策略变更使用新名称。详情见[续跑](benchmark.md#显式续跑示例)。

## AgentDyn低TSR／ASR只读诊断

```bash
python -m experiments.diagnostics.agentdyn_zero_rates \
  --run-dir /absolute/path/to/run --output-dir "workshop/artifacts/<YYYYMMDD>_<task>/diagnosis"
```

输出须新目录；只读原始标签、授权差集、阻挡、GOAL及注入文本重合。参考工具路径不是唯一完成路径，文本重合不证明模型遵循攻击。

## 工具参数JSON错误

当前任务整批不执行，记基础设施错误，后续任务继续；不修补参数或自动重发。有效TSR／ASR排除该例，GOAL错误另计，有错误退出1，详见[错误处理](benchmark.md#工具参数-json-解析错误)。
