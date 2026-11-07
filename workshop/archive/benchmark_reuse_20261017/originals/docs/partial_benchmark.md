# 小批量测试：run_partial_benchmark

以下命令从 `DSCG/` 执行，默认已激活 `ipi`。本入口用于框架优化和小规模回归；完整任务测量见 [benchmark指南](./benchmark.md)。模型角色、Key、工具目录与优先级见 [配置指南](./model_tool_configuration.md)。

## 默认任务范围

默认运行v1.2的workspace、travel、banking、slack四场景，每场景取**注册顺序前3个用户任务×前3个injection task＝9个组合/目标型攻击**。选择不随机，seed:7只是保留元数据，不排列当前前缀。

| 范围 | 用户任务数 | typical四攻击的计划计分组合 | clean计划任务数 |
| --- | --- | --- | --- |
| 默认四场景 | 12 | 144 | 12 |
| travel、banking、slack | 9 | 108 | 9 |

目标型攻击另有原生GOAL预检；计划数不等于模型API请求数、有效计分分母或实际费用。结果默认在 `results/partial_benchmark/`，`task_scope=partial`；与full分别命名、分别解释。

## 对照与输出

baseline使用原生AgentDojo工具循环，不使用DSCG或安全模型；DSCG不加 `--baseline`。两组固定相同主模型、任务、攻击、场景与源码，使用不同的新name：

```bash
python -m experiments.run_partial_benchmark \
  --model-config config/models.local.toml \
  --baseline --force-rerun --name partial_baseline_typical_01

python -m experiments.run_partial_benchmark \
  --model-config config/models.local.toml \
  --force-rerun --name partial_dscg_typical_01
```

默认typical为ignore_previous、injecagent、important_instructions、tool_knowledge。常规DSCG CLI默认router shadow、重试0、completion_prompt=false、summary日志；shadow保留L3审计，仅收集观测。baseline不运行DSCG，NoChecker关闭L3，两者未显式指定时路由均为off。DSCG显式off仍保留原L3；`--no-checker`是消融，不等于baseline。

### 跳过workspace

两组传入相同 `--suites`：

```bash
python -m experiments.run_partial_benchmark \
  --model-config config/models.local.toml --suites travel banking slack \
  --baseline --force-rerun --name partial_baseline_three_suites_01

python -m experiments.run_partial_benchmark \
  --model-config config/models.local.toml --suites travel banking slack \
  --force-rerun --name partial_dscg_three_suites_01
```

每场景仍是原前3×3，三场景共有9个用户、每攻击27个组合。attack_manifest的suites记录实际场景，suite_scope=selected说明场景子集。更换场景集合需新name，force-rerun不能绕过绑定。

## 干净任务对照

`--clean` 检查原前三个用户的无攻击效用，不构造注入攻击，也不执行攻击目标预检：

```bash
python -m experiments.run_partial_benchmark \
  --model-config config/models.local.toml --suites travel banking slack \
  --baseline --clean --force-rerun --name partial_baseline_clean_01

python -m experiments.run_partial_benchmark \
  --model-config config/models.local.toml --suites travel banking slack \
  --clean --force-rerun --name partial_dscg_clean_01
```

上述每组计划9个用户任务，省略suites时每组12个。按 `(suite_name, user_task_id)` 配对，错误/缺失单列。clean的ASR/Defense Rate为null，不是0%/100%；不因clean失败而私自修改后续攻击名单。

## 筛选injection目标

先按 [独立预检指南](./injection_precheck.md)生成冻结cohort.json，再让两组使用同一份名单、相同场景与攻击：

```bash
python -m experiments.run_partial_benchmark \
  --model-config config/models.local.toml --suites travel banking slack \
  --cohort results/injection_precheck/deepseek-flash_injection_screen_01/cohort.json \
  --baseline --force-rerun --name partial_baseline_screened_01

python -m experiments.run_partial_benchmark \
  --model-config config/models.local.toml --suites travel banking slack \
  --cohort results/injection_precheck/deepseek-flash_injection_screen_01/cohort.json \
  --force-rerun --name partial_dscg_screened_01
```

示例路径对应deepseek-flash；使用自己实际生成的路径，名单绑定的主模型/配置必须匹配。

- 用户仍是每场景原前3个；注入目标为“原前3个injection ID ∩ cohort保留名单”，**不从后续目标补位**。
- 某场景原前三个目标全部排除时跳过，全部为空拒绝启动。9个用户是三场景的名义前缀总数；跳过场景后实际计分用户/组合减少。
- 名单须覆盖所选场景；证据损坏、未决或配置不兼容时拒绝。cohort与clean、task-manifest、write-task-manifest互斥，拒绝DoS及包含DoS的all预设。
- 结果为 `task_scope=partial_screened`；核对screened_cohort的selected_tasks、counts、哈希与实际task/attack ID，不能与保留全部用户的full screened混用分母。
- 原生目标预检仍针对实际选中目标执行，见preflight_report；它不计攻击样本，独立screen成本另报，缺失逐次usage保留未知。

不根据DSCG结果重新筛选；直接请求失败不能证明间接攻击无法成功。

## 攻击选择与shadow记录

具体攻击可单选、多选或重复 `--attack`：

```bash
python -m experiments.run_partial_benchmark \
  --model-config config/models.local.toml \
  --attack tool_knowledge injecagent --name partial_two_attacks_01
```

typical/all不能与具体名称混用，manual不支持。当前安装的all含16个自动攻击，默认四场景前缀计划456条计分rollout；其中DoS按每用户首个注入ID一次计分，与目标型ASR分开。名称、类型与来源集中见 [公共攻击表](./benchmark.md#攻击选择)。

需要L3路由数据时，对DSCG运行启用shadow/full：

```bash
python -m experiments.run_partial_benchmark \
  --model-config config/models.local.toml --suites travel banking slack \
  --audit-router-mode shadow --trace-level full \
  --force-rerun --name partial_dscg_shadow_01
```

需要筛选时加同一cohort并使用新name。shadow保留语义审计，不新增免审或自动校准阈值。任务JSON的dscg_router_events记录路由，场景summary的audit_router统计覆盖，邻接 `.dscg_trace.jsonl.gz` 保存有界审计输入；full有额外本地开销。baseline/NoChecker不能显式启用shadow/selective；CLI自动为它们选择off。Python API/factory默认仍off，需要CLI的off对照时显式传 `--audit-router-mode off`。其他对照开关见 [公共参数](./benchmark.md#可选控制与日志)。

## 结果文件

```text
results/partial_benchmark/<model_id>_<name>/
  summary.md
  failure_cases.jsonl
  attack_manifest.json
  suite_manifest.json
  all_report.txt
  <attack或none>/<suite>/
    run_manifest.json
    summary.json
    detailed_results.csv
    report.txt
    <user_task_id>/<attack或none>/<injection_task_id或none>.json
```

先读summary，再核对各场景summary.json的task_selection实际ID和planned/total/error分母。原生目标预检轨迹用injection ID作为任务目录，不当作用户攻击样本。字段与公共TSR/ASR、成本口径见 [结果说明](./benchmark.md#结果文件)和[指标说明](./benchmark.md#指标与证据)。

## 中断、缓存与任务清单

- 同配置续跑：保持源码、模型、name与场景不变，去掉force-rerun并取消DSCG_FORCE_RERUN的强制设置。缓存复用不是从单个中断动作继续；混合缓存与新调用的成本不能当作一次新鲜运行。
- 改模型/源码/控制/场景/cohort，或测新成本时使用新name。force-rerun不解除配置绑定，也不覆盖冻结预检名单。
- `--write-task-manifest PATH` 离线导出所选场景前缀并退出，不调用模型，拒绝覆盖。显式task-manifest可读冻结自定义ID；这时以清单和task_selection为准，不再称为默认3×3前缀。
- 退出0表示流程完成，仍须检查错误与样本完整性；退出1为配置/运行/攻击异常，退出2通常为参数错误。无失败时JSONL可以为空，强制终止可能尚无运行级摘要。

用户结果使用默认results目录；agent临时检查须加 `--results-dir workshop/artifacts/<YYYYMMDD>_<task>/partial_benchmark` 并使用新name。不改写历史轨迹或用诊断结果替换原生评分。
