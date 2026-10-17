# Injection 目标预检与筛选后测量

`experiments.run_injection_precheck screen` 将 injection task 的 GOAL 直接交给无防御 baseline，检查当前模型/配置下的目标可完成性并冻结名单。之后统一使用 `experiments.run_benchmark --cohort PATH` 进行筛选测量；不传 `--cohort` 时仍是完整注册任务。预检不向工具返回注入内容，不修改原生 predicate 或防御机制。

这是**基于直接目标预检的筛选子集**，不能标为 AgentDojo 全量结果。直接请求失败不证明间接注入无法成功：模型可能主动拒绝直接请求，也可能在执行细节或原生评分上失败。筛选后的 ASR 与未筛选的 ASR 分母不同，不能直接混作防御收益。

优化阶段也可用 `experiments.run_partial_benchmark --cohort PATH --suites travel banking slack --name <新名称>`。默认每场景3用户×3注入的前缀不变，只从原前三个注入目标中筛掉名单排除项，不补位；结果标记 `partial_screened`，默认保存到 `results/partial_benchmark/`。完整命令见 [小批量测试指南](./partial_benchmark.md#对照与输出)。本指南下方 `run_benchmark --cohort` 仍使用全部用户任务。

全量筛选也支持 `run_benchmark --cohort PATH --suites travel banking slack --name <新名称>`：只运行所选场景，保留这些场景全部用户与全部通过目标。名单必须覆盖显式选择的场景；原名单、证据和筛选结论不变。完整命令与范围标记见 [全量指南](./benchmark.md#1-使用哪个入口)。

## 1. 独立预检

以下命令在 `DSCG/`、已激活 `ipi` 环境下执行。使用新 name，不复用其他类型实验的目录：

```bash
python -m experiments.run_injection_precheck screen \
  --model-config config/models.local.toml \
  --reuse-from results/benchmarks/deepseek-flash_baseline \
  --name injection_screen_01
```

默认覆盖 v1.2 四场景全部 35 个注入目标，不受 partial 的前 3 个任务限制；正常用户任务不在本阶段运行。

启动后立即显示模型、目标数、复用来源、输出目录和首次运行/续跑状态。每个目标按 `[序号/总数] 场景/目标ID` 输出复用、恢复、新尝试或失败复测，以及结果、耗时、已知 Tokens 或“未知”。模型执行期间每 15 秒显示等待提示；每个目标结束显示累计保留/排除/未决数量。输出逐行刷新，重定向日志也可实时查看；进度提示不会额外请求模型或自动重试。

```text
[预检 0.1s] [1/35] workspace/injection_task_0 复用历史尝试=1，状态=kept。
[预检 0.2s] [4/35] workspace/injection_task_3 开始尝试 attempt_0002（失败复测）。
[预检 15.2s] [4/35] workspace/injection_task_3 等待中，已执行 15s
```

- 核对已有 baseline 记录的模型公开配置、运行源码哈希、AgentDojo/任务版本、场景/任务 ID、GOAL 与原生结果完整性。扫描各攻击目录下的预检，任一兼容成功优先；相同文件哈希不重复计数。记录原始路径、哈希及复用依据，不改写旧文件。
- 任一次有效成功即 `kept`；两次有效失败才 `excluded`。兼容旧记录计入已有尝试，不足时补测。`excluded` 只表示本轮两次未完成。
- API/上下文错误、损坏或缺失轨迹是 `error`，不计有效失败。单个目标遇到新错误后暂停该目标、继续其他目标；存在未完成判定时不生成冻结名单，退出 1。
- 历史证据缺少独立环境/任务实现哈希，现有检查不能证明过去与现在所有环境字节一致；服务模型真实修订也可能未固定。这些限制写入报告。

默认输出目录：

```text
results/injection_precheck/<model_id>_injection_screen_01/
  screen_manifest.json
  status.json
  summary.md
  compatibility/<current-binding-hash>.json  # 仅在兼容读取旧绑定时新增
  cohort.json                         # 全部目标完成判定后才生成，拒绝覆盖
  attempts/<suite>/<injection_task_id>/attempt_0001/
    attempt_manifest.json             # 新模型尝试的预先配置绑定
    attempt.json                      # 结果、原始路径/hash、成本或未知状态
    direct_goal/<suite>/<injection_task_id>/none/none.json
```

复用尝试只写引用记录，原始轨迹留在原目录。保留这些原始文件以及 manifest，后续使用冻结名单会重新核对其哈希。`status.json` 保存每个目标的全部尝试、复用拒绝记录、已知 Token 总量及成本未知尝试数；`summary.md` 给出状态表。主动拒绝、执行偏差、评分疑点须根据轨迹单独复核，不由关键词自动定性。

## 2. 中断和错误后续跑

保持源码、配置、任务版本与 name 不变，重新执行同一条 `screen` 命令即可。已完成目标不重跑；失败但不足两次有效尝试的目标补测；每次新尝试使用新目录，不覆盖错误或中断轨迹。已完成原生结果但尚未写完 wrapper 记录时，可以根据尝试绑定恢复结果，该次成本记为未知。

冻结名单已经生成时只核验并返回，不重跑或重写名单。没有 `--force-rerun` 选项；需要全新预检就使用新 name，并按需省略 `--reuse-from`。

本次进度/入口整理提供明确的旧版本兼容映射：核对已知旧脚本/runner 字节哈希、当前改动文件哈希、相同模型/任务/规则以及未变的防御运行源码后，可以继续旧预检或读取旧名单。只新增 compatibility 记录，保留旧 manifest、attempt 和 cohort 的原始字节。Git revision 变化但绑定源码完全相同也只记录出处；未知脚本、模型、任务或防御变化仍拒绝执行，须用新 name。

已经启动的进程不会自动获得新日志。更新代码后重新执行同一条预检命令；Ctrl+C 会停止等待提示，已有尝试保留用于续跑。旧版已经开始的攻击测量保留原身份，升级后使用新的测量 name。

## 3. 使用冻结名单测 baseline

```bash
python -m experiments.run_benchmark \
  --cohort results/injection_precheck/deepseek-flash_injection_screen_01/cohort.json \
  --model-config config/models.local.toml \
  --baseline --attack typical --force-rerun \
  --name baseline_screened_02
```

保留各场景全部 user tasks，仅筛选 injection tasks。默认 typical 四种目标型攻击，也支持具体名称及重复 `--attack`；DoS 或包含 DoS 的 `all` 会被拒绝。某场景没有保留目标时明确跳过；全部场景为空或名单不完整/证据变化时拒绝启动。

底层复用共享 runner，筛选结果在 run/attack manifest 和场景汇总中明确记录 `task_scope=screened` 与名单哈希，摘要标题为“筛选目标评测摘要（全部用户任务）”。以 `task_selection` 中 ID 和 `screened_cohort.json` 为准。`--cohort` 不能与 `--clean`、`--task-manifest` 或 `--write-task-manifest` 同用；不传 `--cohort` 时正式 full 任务范围保持完整。

所有模型、工具目录、防御消融、审计重审、完成提示、L1、L2 和 L3 路由/trace 控制沿用 benchmark CLI；Python API 同样支持 `run_benchmark.main(cohort_path=...)`。显式传入 `suites` 时必须包含冻结名单中的所有非空场景，否则提前拒绝，避免悄悄扩大运行范围。旧 `run_injection_precheck benchmark` 命令仍可用，会提示并转发到统一入口，仍要求非空 `--cohort`，不再单独维护测量参数。

默认输出 `results/benchmarks/<model_id>_baseline_screened_02/`，原有报告和轨迹布局保持一致，额外保存：

| 文件 | 内容 |
| --- | --- |
| `screened_run_manifest.json` | 名单身份、模型/源码、攻击与主要记录选项；同名冲突拒绝执行 |
| `screened_cohort.json` | 完整名单副本、跳过场景、原始/保留目标数、全部用户数和每种目标型攻击的计划组合数 |
| `preflight_report.json` | 本次攻击流程中的非计分目标预检通过/失败/错误/缺失状态、路径/hash与成本限制 |

原生攻击流程仍会对保留目标执行各攻击下的预检。它们消耗模型资源，但不计入攻击样本分母。共享 runner 的总成本包含这些预检；原生逐任务日志没有独立 usage，因此 `preflight_total_tokens=null`，不能把未知记成 0，也不能重复加到总成本上。独立筛选阶段的成本在筛选目录另报，复用旧尝试的 Token 成本为未知。

继续中断的攻击测量时，保持配置/name 不变，去掉 `--force-rerun` 并取消环境变量 `DSCG_FORCE_RERUN` 的强制设置；成本解释遵循共享 runner 的缓存口径。

## 4. 后续 DSCG / shadow 对照

两组必须使用**同一冻结名单**，不能根据 DSCG 的预检或攻击结果重新筛选。例如：

```bash
python -m experiments.run_benchmark \
  --cohort results/injection_precheck/deepseek-flash_injection_screen_01/cohort.json \
  --model-config config/models.local.toml \
  --attack typical --force-rerun --name dscg_screened_shadow_01 \
  --audit-router-mode shadow --trace-level full
```

shadow 保留完整 L3 审计；路由数据仍在任务 JSON 的 `dscg_router_events`、场景 `summary.json.audit_router` 和 full 压缩侧车中。独立标签/相关组/校准仍按 [L3 方案](../workshop/L3_checker_opt.md) 和 [参数计划](../L3_plan.md) 执行。筛选子集的调用数不等于独立校准组数。

两个子命令均支持 `--results-dir`。用户实验使用上述默认目录；agent 离线/临时检查必须显式使用新的 `workshop/artifacts/<YYYYMMDD>_<task>/` 下的输出根。实现和离线验证不代表新的模型实验、E0 通过或安全收益。
