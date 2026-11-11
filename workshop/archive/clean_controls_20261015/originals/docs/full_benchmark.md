# 全量测试：当前 DSCG 与无防御 baseline

以下命令在 `DSCG/` 执行，默认已激活 `ipi` 环境。本指南面向用户正式实验，不会因阅读文档自动发起模型调用。

## 1. 使用哪个入口

| 入口 | 默认任务范围 | 默认结果根目录 |
| --- | --- | --- |
| `python -m experiments.run_benchmark` | v1.2 四个场景的全部注册用户任务与注入任务 | `results/benchmarks/` |
| `python -m experiments.run_partial_benchmark` | 每场景注册顺序前 3 个用户任务、前 3 个注入任务 | `results/partial_benchmark/` |

两者共用模型配置、当前框架、攻击选择、缓存绑定和报告流程。**全量入口不再使用前 3 个任务的限制**；如显式导入任务清单，必须包含当前注册顺序下的完整执行集合，不能用 partial 清单缩小全量测试。

“全部任务”与“全部攻击”是两项独立选择：全量入口默认 `--attack typical`，在全部任务上运行四种目标型攻击；`--attack all` 才运行已安装注册表中的全部自动攻击，排除交互式 `manual`。具体名称、类型和来源见 [评测指南的攻击表](./evaluation.md#攻击选择)。

## 2. 配置与默认框架

模型字段、API Key 获取和工具目录配置见 [模型、工具与运行参数详解](./model_tool_configuration.md)。准备好 `config/models.local.toml` 和对应 Key 环境变量即可；标准 AgentDojo 工具与模拟环境已提供，不需要真实银行、邮箱或 Slack 账号，也不要求额外任务清单。

- **baseline：** 加 `--baseline`，使用原生 AgentDojo 工具循环与相同主模型配置；不加载 DSCG 风险目录，不创建安全模型，不启用 DSCG 或 AgentDojo 防御。`--no-checker` 是保留其他防御的消融，不能代替无防御 baseline。
- **当前 DSCG：** 不加 `--baseline`。沿用 `three-layer-l1-v3`：L1 有限投影默认 `projected`，L2 工具授权/前置检查、工具视图和有限任务文件展开开启，L3 当前动作审计开启。
- **保持普通对照默认值：** 算法路由 `off`、重审 `0`、完成提示关闭、日志 `summary`。路由 `off` 不会关闭 L3。没有部署阈值时，不在这轮全量测试中临时启用 selective；参数决策另见 [plan.md](../plan.md)。

两组使用同一份 `[main]`；只有 DSCG 使用 `[security]`，省略该角色时按既有规则复用主模型。固定模型配置、工具目录和源码后再开始成对实验；记录中保留 revision 与源码哈希，但模型服务未提供或未固定的实际修订仍是重复性限制。

可先进行不调用模型的检查：

```bash
python -m experiments.run_benchmark --help
python -m experiments.run_benchmark \
  --write-task-manifest download/full_v12_tasks_01.json
```

第二条仅导出全部注册任务 ID 并退出，文件已存在时拒绝覆盖。该清单可供核对，普通运行无需导入；若需要冻结它，在两组运行中都加 `--task-manifest download/full_v12_tasks_01.json`。DoS 仍从完整清单按原生规则选首个注入 ID，不把它扩展成所有注入组合。

## 3. 先运行全量干净任务对照

这两组不注入攻击，用于观察防御对正常任务完成率的影响。它们与后续攻击运行分别命名、分别保存。

```bash
python -m experiments.run_benchmark --baseline --clean --force-rerun \
  --model-config config/models.local.toml --name full_baseline_clean_01

python -m experiments.run_benchmark --clean --force-rerun \
  --model-config config/models.local.toml --name full_dscg_clean_01
```

`--clean` 不构造攻击，也不执行注入能力预检。干净任务的 ASR/Defense Rate 为 `null`，不是 0%/100%。

## 4. 运行全量任务攻击对照

### 四种典型攻击

`typical` 为 `ignore_previous`、`injecagent`、`important_instructions`、`tool_knowledge`。以下运行全部任务，不是 partial 子集：

```bash
python -m experiments.run_benchmark --baseline --attack typical --force-rerun \
  --model-config config/models.local.toml --name full_baseline_typical_01

python -m experiments.run_benchmark --attack typical --force-rerun \
  --model-config config/models.local.toml --name full_dscg_typical_01
```

### 全部自动攻击

若本轮还要求覆盖全部自动攻击，两组都改用 `all` 和新的名称；不需要先跑完 typical 再重复跑 all，因为 all 已包含 typical。

```bash
python -m experiments.run_benchmark --baseline --attack all --force-rerun \
  --model-config config/models.local.toml --name full_baseline_all_01

python -m experiments.run_benchmark --attack all --force-rerun \
  --model-config config/models.local.toml --name full_dscg_all_01
```

也可用 `--attack tool_knowledge injecagent` 在全部任务上运行指定攻击；`typical/all` 不能与具体攻击名称混用。选择较少攻击不会将任务缩回 partial。

### 当前任务规模

2026-10-15 在 AgentDojo 0.1.35 / v1.2 安装下只读核对：

| 场景 | 全部用户任务 | 全部注入任务 | 每种目标型攻击的计划组合 |
| --- | --- | --- | --- |
| workspace | 40 | 14 | 560 |
| travel | 20 | 7 | 140 |
| banking | 16 | 9 | 144 |
| slack | 21 | 5 | 105 |
| 合计 | 97 | 35 | 949 |

每个运行组的计划规模如下；baseline 与 DSCG 各自都要运行一组：

| 选择 | 计划计分样本 |
| --- | --- |
| `--clean` | 97 |
| 任一目标型攻击 | 949 |
| `--attack typical` | 4 × 949 = 3,796 |
| 任一 DoS 攻击 | 97 |
| `--attack all` | 当前 11 种目标型 × 949 + 5 种 DoS × 97 = 10,924 |

这些是注册表下的**计划数**，不等于最终有效分母或 API 请求数。目标型攻击还会先把注入任务作为普通任务执行，检查模型是否能完成攻击目标；这些预检不计入上表，但消耗 Tokens。一个计分样本也可能包含多次规划、授权、审计与工具调用。

DoS 按原生任务失败口径计分，每个用户仅执行首个注入 ID 一次；不要将它与目标型 ASR 合并成一个安全结论。最终以实际注册表、manifest、任务 ID 和有效结果为准。

## 5. 结果在哪里，应该核对什么

新布局为：

```text
results/benchmarks/<model_id>_<name>/
  attack_manifest.json
  summary.md
  failure_cases.jsonl
  all_report.txt
  <attack或none>/<suite>/
    run_manifest.json
    summary.json
    detailed_results.csv
    report.txt
    <user_task_id>/<attack或none>/<injection_task_id或none>.json
```

启用 `--trace-level full` 时，压缩审计侧车与对应任务 JSON 相邻。普通比较使用默认 summary；full 增加序列化和写盘成本，按需用于诊断。旧全量的平铺结果保留，不迁移或作为新布局缓存读取。

完成后按以下顺序核对：

1. **范围与配对：** `attack_manifest.json` 和各场景 `summary.json` 中的 `task_scope` 应为 `full`；`task_selection` 的 user/injection ID 在 baseline 与 DSCG 之间一致，所选数等于可用数，DoS/clean 除外。仅运行名称相似不足以证明配对。
2. **实际防御：** suite 的 `run_manifest.json` 记录 baseline/full/no-checker profile、L1/L2 控制、模型公开配置、源码哈希和路由身份。baseline 的 defense 应为 null，无安全模型开销；正常 DSCG 保持本指南默认开关。
3. **完整性：** 核对 planned/total/security_missing、运行错误和失败片段。缺失安全结果为未知/基础设施问题，不是安全成功；全部缺失时 ASR 为 null。`summary.md` 的 partial/error 状态也要检查。
4. **指标：** 分别比较干净 TSR、攻击下 TSR、按攻击类型区分的 native ASR，并检查环境终态与代表性失败。计数加权汇总，不能直接平均不同分母的场景百分比。
5. **成本：** 同时看 `overhead`、`sec_overhead` 和 `api_accounting`；主模型开销含其承担的授权与预检调用，统计总量时不要重复相加。缺失 usage 保持未知，使用新名称并 force-rerun 也不能单独证明成本可比。

`failure_cases.jsonl` 提供 TSR=false、ASR=true、指标缺失及原始文件位置/有界片段，保留原生评分，不替代独立安全 oracle。进一步口径见 [评测指南的结果文件](./evaluation.md#结果文件)。历史分析可通过 `python -m dashboard.app` 启动并选择这两个新运行组，筛选相同攻击；仍需单独核对 task ID。

## 6. 中断、缓存和退出状态

- 正式成本对照推荐本指南的**新 name + force-rerun**。源码、模型、工具/schema 或框架开关变化后使用新 name；`--force-rerun` 不绕过配置绑定，也不把 partial 缓存变成 full。
- 若长任务中断且只想继续，保持源码/配置/name 不变，去掉 `--force-rerun` 后重新执行；同时取消 `DSCG_FORCE_RERUN` 的强制设置。原生缓存复用已完成任务，不代表恢复中断中的单个动作。
- 续跑可能混合历史缓存和新调用，Token 记录不再等同于一次完整新运行。检查 `cost_scope`、`invocation_cost` 与 `cost_comparison_ready`，将其与新鲜匹配成本实验分开；不为获取统一成本而覆盖旧证据。
- 退出 `1` 表示配置/运行或某攻击发生异常；攻击异常被记录后继续后续攻击，不能算成 0-ASR。退出 `2` 通常是命令行参数错误。退出 `0` 只表示流程正常结束，还须检查结果完整性；不表示所有任务成功或真实 E0/安全验收通过。

需要改变结果位置时，两组都支持 `--results-dir DIR`。用户正式实验默认留在 results；agent 临时检查必须显式隔离，例如：

```bash
python -m experiments.run_benchmark --baseline --attack injecagent \
  --name agent_full_probe_01 \
  --results-dir workshop/artifacts/20261015_agent_full_probe/benchmarks
```

上述 probe 是会调用模型的全量命令，不是离线检查，本次工程验证没有执行它。全量任务数量增加不会修复当前工具级权限边界、I3 范围缺口，也不自动完成独立 E0 核查。
