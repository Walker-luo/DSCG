# v3.7 注入目标筛选与 GOAL 检查

测量入口使用 `--fliter PATH`，拼写固定为 fliter。默认按名单筛选而不检查 GOAL；需要当前测量框架预检时显式添加 `--goal`。

## 最小排除文件

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

文件仅保存后端身份和排除 ID。名单读取一次，未知后端／场景／ID、重复键或 ID、额外字段在调用前拒绝。未列场景不排除，原输入文件不修改；partial 从原前 3 目标中删除，不补位。

消费名单只核对后端及目标绑定，不重读筛选证据或重新认证原判定。旧 `--cohort`／cohort.json 输入已拒绝，已有结果的读取兼容保留。

## 独立生成名单

screen 使用原生无防御循环，把每个注入目标的 GOAL 直接作为请求。先配置同一 main 模型，再运行以下真实在线命令。

```bash
python -m experiments.run_injection_precheck screen \
  --model-config config/models.local.toml \
  --results-dir results/workshop --name v37_screen_doc01
```

默认覆盖全部后端注入目标，`--suites` 可选子集。每个 GOAL 只运行一条完整轨迹，可以包含多次模型请求。首次成功保留，失败直接排除；错误／中断同样从计分集合中跳过，但单列状态，不能用来证明目标不可完成。有错误退出 1，续跑只处理尚未开始目标，不补测已开始或完成目标。

输出位于 `<results-dir>/<backend>/<model>/<name>/`，包含根 run_manifest.json、summary.json／summary.md、fliter.json、goal/<suite>/<injection>.json。summary 的 goal_checks 保存判定、轨迹引用和成本；attempts/ 保存一次执行及恢复所需状态。

baseline 与防御攻击测试使用同一份冻结名单，仅添加 `--fliter` 即可，详见 [完整测试](benchmark.md)。不同模型分别生成名单，并报告实际任务集合。

## 测量时可选 GOAL

```bash
python -m experiments.run_partial_benchmark --suites banking slack \
  --fliter /absolute/path/to/fliter.json --goal \
  --results-dir results/workshop --name v3.7_goal_doc01
```

先按名单排除，再用当前测量 pipeline 对剩余目标各执行一条 GOAL 轨迹。baseline 为原生无防御，v3.7 为当前防御配置，所有攻击共享判定。只有成功目标进入计分；失败排除，错误跳过且非零退出，中断保存进度，已开始目标不重试。

GOAL 轨迹存于 goal/<suite>/<injection>.json，根 summary.json 的 selection_report.goal_checks 用于恢复。GOAL 新排除项不合并进输入 fliter.json。GOAL 成本单列并进入总报告，不进入 TSR／ASR；全部排除时计分指标为 N/A。

不同框架参与 GOAL 筛选可能产生不同测试集合，比较须使用共同任务键。clean／DoS 不接受 fliter 和 goal。筛选本身不能计作防御成功。

## 续跑与证据复用

相同 name、输出根和配置的续跑仅处理未开始目标。`--reuse-from /absolute/path/to/source_run` 可只读复用兼容的原生无防御证据；配置和证据须通过 screen 的校验，防御 GOAL 不能作为 baseline screen 证据。

新运行仅生成单一根 manifest 和汇总。旧筛选目录保留原格式，拒绝写入迁移式续跑。成本、错误和恢复细节见 [结果文件](result_files.md)。
