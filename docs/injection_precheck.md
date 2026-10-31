# 注入目标排除与GOAL检查

本说明覆盖后续v3.6归档基线的筛选行为；当前代码标识仍为v3.5.4。测量入口使用`--fliter PATH`，拼写固定为`fliter`；默认不检查GOAL，按需加`--goal`。旧`--cohort`和旧benchmark转发子命令已拒绝，历史名单与结果保留读取兼容，不迁移、不重新解释原判定。

## 最小排除文件

文件只绑定后端和排除ID，不携带模型、证据路径、旧筛选配置或成功名单：

```json
{
  "schema_version": "dscg.fliter.v1",
  "benchmark": {
    "id": "agentdojo",
    "suite_version": "v1.2",
    "revision": "pypi:agentdojo==0.1.35"
  },
  "excluded": {
    "banking": ["injection_task_0"]
  }
}
```

AgentDyn须使用实际后端id与固定revision；用`python -m dscg.benchmark_catalog`离线核对。未知后端／场景／ID、重复键／ID及额外字段在模型调用前拒绝。未列场景不排除；不验证或认证旧筛选证据。排除保留原注册顺序，partial只从原前3目标删除，不补位。

```bash
python -m experiments.run_partial_benchmark --suites banking slack \
  --fliter /absolute/path/to/fliter.json --name filtered_partial_01
```

## 测量时可选GOAL

```bash
python -m experiments.run_partial_benchmark --suites banking slack \
  --fliter /absolute/path/to/fliter.json --goal --name goal_partial_01
```

先应用fliter，再给每个剩余目标执行一次直接GOAL，使用**当前测量pipeline**：baseline是原生无防御，DSCG使用当前防御配置。每目标一条完整轨迹，可含多次模型请求；结果跨攻击共享。通过才进入计分，失败排除，错误／中断分开记录；不重试已开始目标。

GOAL是直接目标可完成性检查，不是间接注入攻击或正常用户clean任务，不进入TSR／ASR分母。不同pipeline可能保留不同集合；比较须报告实际范围与共同任务键，不能把排除当作防御成功。

轨迹在`goal/<suite>/<injection>.json`；根`summary.json`的`selection_report.goal_checks`持久保存开始／结束状态和成本。根`summary.md`只给出一条筛选总述及加粗排除行，GOAL失败与错误分别列出。`--reuse`保持原fliter／goal和全部有效配置，已开始GOAL不补跑；未知usage保留未知。

## 独立预检生成排除表

`screen`仍使用当前后端原生无防御循环，将每个注入目标GOAL直接作为请求执行。以下命令会调用真实模型：

```bash
python -m experiments.run_injection_precheck screen \
  --model-config config/models.local.toml --name injection_screen_01
```

默认覆盖当前后端全部注入目标，可用`--suites`选择子集。**仅依据第一次完整轨迹：通过保留，未通过直接剔除，不等第二次失败，也不做补测。**每GOAL只跑一次完整轨迹；失败、错误／中断目标进入`fliter.json`，错误另外报告且退出1，不以基础设施错误证明目标不可完成。成功保留；已完成／已开始尝试不重试。输出位于`results/injection_precheck/<backend>/<model>_<name>/`，新运行只用根`run_manifest.json`保存筛选配置（schema为`dscg.fliter-screen.v1`），根`summary.json`保存计数与`selection_report.goal_checks`，并生成`fliter.json`和`summary.md`；GOAL原生轨迹在`goal/<suite>/<injection>.json`。每目标状态为`passed`／`failed`／`error`，成本为`{"models": [api_accounting]}`或未知`null`，不在汇总重复完整模型配置。`attempts/`仅保存开始／结束、绑定摘要、证据引用与记账，供中断恢复，不复制轨迹。

同配置／name／输出根续跑仅处理尚未开始目标；全新筛选使用新名称。历史已冻结名单及证据保留原字节／规则；含旧`screen_manifest.json`／`status.json`的目录拒绝写入续跑，不自动迁移。`--reuse-from /absolute/path/to/source_run`只读复用兼容的旧原生baseline证据或新`goal/`证据；来源可为旧筛选配置或新的单一根配置，但测量GOAL须确认为相同模型配置的原生无防御baseline。DSCG或其他防御测量的GOAL不能作为独立baseline筛选证据。独立无防御screen与测量当前pipeline GOAL是不同范围，成本分开记账。

完整测量、partial及结果字段分别见[完整指南](benchmark.md)、[partial指南](partial_benchmark.md)和[结果文件](result_files.md)。agent临时检查显式使用新的`--results-dir workshop/artifacts/<YYYYMMDD>_<task>/injection_precheck`。
