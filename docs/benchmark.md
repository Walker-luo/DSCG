# 完整评测与公共运行规则

从 BaseIntent 根目录激活 `ipi` 或 `ipi-agentdyn`，用 `python -m baseintent.benchmark_catalog` 离线确认实际后端。配置见[模型与工具](model_tool_configuration.md)。下列测量命令会调用真实模型，全量运行需用户明确启动；替换示例名称和日期，保留独立输出根。

## 范围

| 入口 | 用户 / 注入目标 | 默认输出分类根 |
| --- | --- | --- |
| `experiments.run_benchmark` | 所选场景全部注册任务 | `results/benchmarks` |
| `experiments.run_partial_benchmark` | 每场景注册前 3 用户 × 前 3 目标 | `results/partial_benchmark` |
| `experiments.run_injection_precheck screen` | 所选目标的直接 GOAL | `results/injection_precheck` |

`--suites` 只能选择当前后端场景。AgentDojo：workspace/travel/banking/slack；AgentDyn：shopping/github/dailylife。Full 清单不能缩小实际注册任务集；partial 可使用冻结任务 ID 清单。

| 计划组合 | AgentDojo | AgentDyn |
| --- | ---: | ---: |
| Full clean | 97 | 60 |
| Full 每目标型攻击 | 949 | 560 |
| Full typical 三攻击 | 2847 | 1680 |
| Partial clean / typical | 12 / 108 | 9 / 81 |

这些不是有效评分分母或 API 请求数。AgentDyn dailylife 中缺 `placeholder_args` 的 `tool_knowledge` 目标不支持，单列并排除。

## 命令

```bash
# 原生 baseline；默认 typical 攻击
python -m experiments.run_benchmark --baseline \
  --model-config config/models.local.toml --name baseintent_full_baseline_01 \
  --results-dir artifacts/20261027_example/full_baseline --progress

# BaseIntent；可用 --suites 选择当前后端子集
python -m experiments.run_benchmark --suites banking slack \
  --model-config config/models.local.toml --name baseintent_full_01 \
  --results-dir artifacts/20261027_example/full --progress

# 无攻击效用控制；baseline clean 加 --baseline
python -m experiments.run_benchmark --clean \
  --model-config config/models.local.toml --name baseintent_clean_01 \
  --results-dir artifacts/20261027_example/clean --progress

# 读取已经冻结的目标名单；保留所选场景全部用户
python -m experiments.run_benchmark --cohort artifacts/20261027_screen/agentdojo/MODEL_screen_01/cohort.json \
  --model-config config/models.local.toml --name baseintent_cohort_01 \
  --results-dir artifacts/20261027_example/cohort --progress
```

cohort 路径为占位示意，使用 screen 实际输出路径。cohort 不能与 clean、task-manifest 或清单导出组合，且必须有新 name。添加 `--baseline` 可作同名单原生对照。默认当前框架见[框架](framework.md)，历史 profile 必须显式指定，`--name` 不选策略。

## 攻击选择

默认 `--attack typical` 展开为 `ignore_previous important_instructions tool_knowledge`。可用 `--attack NAME [NAME ...]` 或 `--attack all`，`injecagent` 为显式选择，manual 排除。DoS 等其他攻击按实际注册表与其原生评分口径读取，不能混用目标型攻击分母。GOAL 预检与计分任务分别统计。

## 按攻击并行与准备信息

Full/partial/cohort 在多个可运行攻击时使用每 attack 独立进程，各进程内保持原生顺序。clean、单攻击、screen 顺序执行。父进程负责配置校验、目录锁与总报告，子进程只写自身攻击目录；无新增并发/重试参数。`--progress` 展示 GOAL 与计分进度，缓存命中也计完成，不代表有效评分或请求数。

## 显式续跑示例

同配置中断后保留原 name、结果根和其余有效控制，使用 `--reuse`：

```bash
python -m experiments.run_benchmark --reuse --name baseintent_full_01 \
  --model-config config/models.local.toml \
  --results-dir artifacts/20261027_example/full --progress
```

省略攻击/场景时恢复原名单。reuse 与 force-rerun 互斥，且覆盖环境强制重跑；不自动重试原生已接受的错误缓存。先核对完整模型/provider、实际后端、任务/攻击/cohort、工具元数据与有效防御配置，再写入或调用。快照保留原汇总/未完成轨迹，缓存按原生规则处理。

新 CLI 路径为 `<results-dir>/<backend>/<model>_<name>/`；仅当新路径不存在才查旧布局。旧结果不移动，新命名或策略变化不自动迁移缓存。冻结名单的消费验证模型/provider、实际后端、场景、任务 ID/顺序及名单摘要，不重读筛选轨迹或重新证明筛选结论；创建/续跑筛选仍验证自己的证据。

## 可选控制与日志

公共选项包括 `--model-config`、`--tool-metadata`、`--trace-level summary|standard|full`、`--prompt-profile`、`--l1-projection-mode`、`--audit-router-mode`、`--audit-router-threshold`、`--audit-retries 0|1`、`--no-checker`、`--no-tool-view`、`--no-delegated-tasks` 和 `--completion-prompt`。默认值见[配置](model_tool_configuration.md)。没有新增同名 NoL2 CLI 参数，完整消融可通过现有 API/Dashboard。

离线导出注册任务清单而不调用模型：

```bash
python -m experiments.run_benchmark --suites banking slack \
  --write-task-manifest artifacts/20261027_example/full_tasks.json
```

目标文件必须不存在。partial 使用同名选项导出其范围。

## 指标与证据

TSR 是有效 utility 布尔标签中的成功比例，ASR 是有效原生安全布尔标签中的攻击成功比例。clean ASR 不适用；错误、未知和不支持单列，不能作为成功防御。框架完成不等于原生业务成功，有界停止也可能保留已发生的 utility/security 成功。

`authorization_intents/authorization_tools/intent_progress`、generation、audit 的实际 usage 均计成本。区分 GOAL 与计分、当前调用与缓存/全运行、实际成本与潜在节省；缺失 usage 不补零。查看 `summary.md`、完整 `failure_cases.jsonl`、原生任务及响应附件，见[结果文件](result_files.md)。

<a id="默认-v35-意图流程"></a>
<a id="默认-v34-策略与复测"></a>
<a id="默认-v33-策略与复测"></a>
<a id="默认-v32-策略与复测"></a>

旧版本章节入口已收敛到[当前框架](framework.md)与[迁移边界](migration.md)；历史记录按原身份保留，不能把旧章节名称当作当前策略说明。
