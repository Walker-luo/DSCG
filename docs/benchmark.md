# 完整任务测试：run_benchmark

以下命令在 `DSCG/` 执行，默认已激活 `ipi` 环境。本指南面向用户正式实验，不会因阅读文档自动发起模型调用。

## 1. 使用哪个入口

| 入口 | 任务范围 | 默认结果根目录 |
| --- | --- | --- |
| `python -m experiments.run_injection_precheck screen` | 仅将全部 injection GOAL 直接作为用户请求，生成冻结名单 | `results/injection_precheck/` |
| `python -m experiments.run_benchmark` | 默认 v1.2 四个场景的全部注册用户任务与注入任务（full） | `results/benchmarks/` |
| `python -m experiments.run_benchmark --cohort PATH` | 全部用户任务 × 名单保留的注入目标（screened；无保留目标的场景跳过） | `results/benchmarks/` |
| `python -m experiments.run_partial_benchmark` | 每场景注册顺序前 3 个用户任务、前 3 个注入任务 | `results/partial_benchmark/` |

测量入口共用模型配置、当前框架、攻击选择、缓存绑定和报告流程。**全量入口不再使用前 3 个任务的限制**；如通过 `--task-manifest` 显式导入 full 任务清单，必须包含当前注册顺序下的完整执行集合，不能用 partial 清单缩小全量测试。

两个测量入口都支持 `--suites travel banking slack` 跳过workspace，默认仍为四场景。`run_benchmark` 保留所选场景的全部注册任务；`run_partial_benchmark` 保留每场景原前三个用户×前三个注入，三场景typical计划81条计分rollout，另有预检成本。partial命令见 [小批量测试指南](./partial_benchmark.md#对照与输出)。

例如，只对travel/banking/slack进行完整任务测量：

```bash
python -m experiments.run_benchmark \
  --model-config config/models.local.toml \
  --suites travel banking slack \
  --force-rerun --name dscg_selected_suites_01
```

匹配baseline使用相同场景并加 `--baseline`、换新name。可与 `--clean` 或 `--cohort PATH` 分别组合；cohort模式使用所选场景全部用户×名单通过目标，原生预检仍保留，clean与cohort继续互斥。显式选择的场景须在cohort中存在，未选场景不执行，不重写冻结名单。

`attack_manifest.json` 和场景summary记录 `suites`、`suite_scope=selected`；普通完整任务测量仍为 `task_scope=full`，意指所选场景内部完整，摘要标题为“所选场景全任务评测摘要”。实际执行四场景时记录 `suite_scope=all_registered`；cohort空目标场景仍按原规则跳过。场景子集不能标成四场景正式全量结果。改变场景集合需新name，`--force-rerun`不绕过绑定；离线 `--write-task-manifest` 仅导出所选场景的完整ID集合，导入清单仍不能缩减这些场景内部的任务。

partial 同样支持 `--cohort PATH`：只过滤原来前三个 injection targets，仍保留每场景前三个用户，不补入后续目标，标记为 `partial_screened`；不会转到全量用户任务。与本指南全量 `--cohort` 的 `screened` 范围不同，用法及分母见 [partial筛选说明](./partial_benchmark.md#对照与输出)。

“全部任务”与“全部攻击”是两项独立选择：全量入口默认 `--attack typical`，在全部任务上运行三种目标型攻击；`--attack all` 才运行已安装注册表中的全部自动攻击，排除交互式 `manual`。具体名称、类型和来源见 [评测指南的攻击表](./benchmark.md#攻击选择)。

如已完成 injection 目标预检，筛选测量也统一使用本入口：显式加 `--cohort <cohort.json>`，结果标为 `task_scope=screened`，保留全部用户任务并采用冻结目标。该选项与 clean/其他任务清单/清单导出互斥，拒绝 DoS；不传时仍为完整 full。命令、进度和旧数据续跑见 [Injection 目标预检指南](./injection_precheck.md)。

## 2. 配置与默认框架

模型字段、API Key 获取和工具目录配置见 [模型、工具与运行参数详解](./model_tool_configuration.md)。准备好 `config/models.local.toml` 和对应 Key 环境变量即可；标准 AgentDojo 工具与模拟环境已提供，不需要真实银行、邮箱或 Slack 账号，也不要求额外任务清单。

- **baseline：** 加 `--baseline`，使用原生 AgentDojo 工具循环与相同主模型配置；不加载 DSCG 风险目录，不创建安全模型，不启用 DSCG 或 AgentDojo 防御。`--no-checker` 是保留其他防御的消融，不能代替无防御 baseline。
- **当前 DSCG：** 不加 `--baseline`。沿用 `three-layer-v3.1`：L1 有限投影默认 `projected`，L2 工具授权/前置检查、工具视图和有限明确任务来源展开开启，L3 当前动作审计开启。
- **保持普通对照默认值：** DSCG CLI算法路由 `shadow`（baseline/NoChecker自动为off）、重审 `0`、完成提示关闭、日志 `summary`。路由 `off` 不会关闭 L3。没有部署阈值时，不在这轮全量测试中临时启用 selective；参数决策另见 [L3 参数计划](../L3_plan.md)。

两组使用同一份 `[main]`；只有 DSCG 使用 `[security]`，省略该角色时按既有规则复用主模型。固定模型配置、工具目录和源码后再开始成对实验；记录中保留 revision 与源码哈希，但模型服务未提供或未固定的实际修订仍是重复性限制。

可先进行不调用模型的检查：

```bash
python -m experiments.run_benchmark --help
python -m experiments.run_benchmark \
  --write-task-manifest download/full_v12_tasks_01.json
```

第二条仅导出全部注册任务 ID 并退出，文件已存在时拒绝覆盖。该清单可供核对，普通运行无需导入；若需要冻结它，在两组运行中都加 `--task-manifest download/full_v12_tasks_01.json`。DoS 仍从完整清单按原生规则选首个注入 ID，不把它扩展成所有注入组合。

历史clean修正、诊断与候选撤回记录见 [v3.1工程报告](../workshop/completed/clean_utility_20261015.md)和[诊断报告](../workshop/completed/read_discovery_20261016.md)。这些阶段观察不替代本轮匹配对照；以下命令使用新名称测量当前配置。

## 3. 先运行全量干净任务对照

正式全量攻击前，先判断当前基础智能体能完成哪些正常任务，再检查 DSCG 是否损失这些能力。两组均无注入，默认四场景共97个用户任务；加 `--suites` 后只运行所选场景的全部用户。与后续攻击实验分别命名、分别保存。这里的失败是“固定模型/配置下本轮未完成”，不是模型永远无法完成的证明。

### 3.1 clean 与攻击目标预检的区别

| 检查 | 智能体收到的任务 | 用途 |
| --- | --- | --- |
| baseline clean | 原始合法用户任务；无攻击、无防御 | 建立基础智能体的正常任务能力参照 |
| DSCG clean | 相同合法用户任务；无攻击、保留当前防御 | 检查防御对正常任务的效用影响 |
| 攻击目标预检 | 将 injection task 的 GOAL 直接作为用户请求；无注入 | 检查当前 pipeline 被直接要求时能否完成攻击目标 |
| 正式攻击实验 | 原始合法任务 + 工具返回中的注入文本 | 检查间接注入的成功与效用变化 |

当前 AgentDojo 0.1.35 的 warning：

```text
Not all injection tasks were solved as user tasks.
```

对应**攻击目标预检**，不表示已经检查了全部正常用户任务。目标型攻击会先执行这项预检；DoS 不执行。部分目标失败后只警告，仍继续后续攻击，不自动删除这些目标。

预检使用当前受测 pipeline：baseline 运行检查原生智能体，DSCG 运行也会经过 DSCG。因此 DSCG 的目标预检失败不能直接归为裸模型能力不足，预检成功也不保证注入成功。诊断时另记目标预检的通过/失败/错误，保留攻击结果原有分母。

如需先独立运行全部 injection GOAL、复测失败并冻结能力筛选名单，使用 [独立预检入口](./injection_precheck.md)。筛选测量保留全部 user tasks，但属于单独的目标子集；不改写本指南的 full 范围和原始结果。

### 3.2 成对运行命令

固定两组的主模型公开配置、工具/任务版本、环境和源码。保持 DSCG 的现行默认开关，使用不同的新 name；如果下列名称已经使用，改为新的后缀，不覆盖已保留结果。两组合计计划 194 个 clean 样本，不等于 194 次 API 请求。

```bash
python -m experiments.run_benchmark --baseline --clean --force-rerun \
  --model-config config/models.local.toml --name full_baseline_clean_01

python -m experiments.run_benchmark --clean --force-rerun \
  --model-config config/models.local.toml --name full_dscg_clean_01
```

`--clean` 不构造攻击，也不执行攻击目标预检；无需再指定 `--attack`。干净任务的 ASR/Defense Rate 为 `null`，不是 0%/100%。

### 3.3 获取失败名单并配对

分别查看：

```text
results/benchmarks/<model_id>_full_baseline_clean_01/
results/benchmarks/<model_id>_full_dscg_clean_01/
```

每组先读 `summary.md`，再读 `failure_cases.jsonl` 和 `none/<suite>/detailed_results.csv`；单个正常任务的原始轨迹位于：

```text
none/<suite>/<user_task_id>/none/none.json
```

`failure_cases.jsonl` 中的 `tsr_failure` 给出本轮未完成的任务；同时检查 `task_error`、`result_missing`、`run_error` 和原始 JSON 的 error/工具返回。零失败时该 JSONL 为空，不表示缺少文件。**当前 runner 尚未把攻击目标预检失败汇总进这份失败清单**；它主要索引正式选中的用户任务。目标预检的原始结果另在攻击运行中：

```text
<attack>/<suite>/<injection_task_id>/none/none.json
```

按 **`(suite_name, user_task_id)`** 配对两组，不能只用 user_task_id，因为不同场景会复用同名 ID。核对全量 ID、模型配置和实际框架开关一致性后，对具备完整可判定结果的任务建立四格表：

| baseline clean | DSCG clean | 诊断方向 |
| --- | --- | --- |
| 成功 | 成功 | 正常任务能力在这次对照中保留 |
| 成功 | 失败 | 优先检查防御引起的效用损失：误拒、缺必要工具/事实、投影回退或其他执行问题 |
| 失败 | 失败 | 检查基础任务能力、工具/模型兼容、事实不足及评分问题，不能归为防御导致 |
| 失败 | 成功 | 本轮 DSCG 完成了 baseline 未完成的任务；检查轨迹并重复验证，不能据此直接作因果结论 |

缺失结果或已确认运行错误单列为异常，不强行放入上述成功/失败配对。原生全量 TSR 和全部样本记录仍照常保留，诊断分类不改写原始评分。

### 3.4 失败原因与后续攻击分析

对每个未完成任务至少记录场景、任务 ID、运行名、原生 utility、原始轨迹路径、异常状态和复核原因：

| 类型 | 需要检查什么 | 应怎样解释 |
| --- | --- | --- |
| API/基础设施问题 | 网络、服务错误、限流、上下文超限、缺失轨迹等 | 单列运行问题，不作为模型本身不会完成任务的证据 |
| 任务执行问题 | 规划/算术/参数错误、工具调用失败、未取得必要事实、模型拒绝等 | 记录本轮失败；工具错误可能来自模型参数，也可能来自环境/接口，须区分 |
| 防御相关问题 | baseline 成功，而 DSCG 的授权、审计或输入处理造成损失 | 保留被拒动作/审计与终态证据，不能只凭最终回答归因 |
| 评分或事实歧义 | 实际终态与 native utility 不一致、环境事实被误读等 | 保留原生标签，另附独立复核，不私改 predicate 或结果 |

对关键失败采用新的运行名重复验证；可以重复整套 clean，或对个别失败另外做诊断，但诊断结果不能替换原全量结果，也不能据单次失败宣布某任务永久不可完成。

选择 full 路径时，后续攻击实验仍执行全部注册任务并报告全量结果；选择 injection 目标筛选路径时，按下节的冻结名单另报 screened 结果。两条路径均保留全部用户任务，不根据 clean 成功与否改变执行清单。另可在攻击结果分析前，冻结 baseline clean 中**完成且无已确认运行错误**的任务键集合：

\[
C_0=\{(s,u):\operatorname{Utility}^{\mathrm{baseline,clean}}(s,u)=1
\ \land\ \text{结果完整且无已确认运行错误}\}.
\]

同时报告全量结果，以及两组在同一个 C0 上的攻击下 TSR/ASR；匹配相同 task/attack 键，DoS 仍单列，无效/缺失分母另报。不能根据 DSCG 自己的成功任务重新筛选集合，也不能看完攻击结果后挑选有利任务。C0 只作补充分层分析，不改变全量入口的任务清单或 native 指标。

进入正式攻击实验前，应具备两组的实际任务 ID、全量/分场景 clean TSR、四格配对与异常计数、失败轨迹及原因、模型/配置身份和总 Tokens。若网络/服务等错误造成实验明显不完整，先解决并以新名称重跑，避免把基础设施失败解释成安全或能力结论。

## 4. 运行全量任务攻击对照

### 可选：先预检 injection 目标，再运行筛选对照

如果本轮希望先排除当前 baseline 直接请求下两次均未完成的攻击目标，先运行以下流程。`screen` 只负责预检和生成名单；后续 baseline、DSCG 与 shadow 测量统一使用 `run_benchmark --cohort`。不采用筛选时，直接使用下方“三种典型攻击”或“全部自动攻击”的完整任务命令。

**第一步：独立预检全部 injection GOAL，复用已有兼容记录。**

```bash
python -m experiments.run_injection_precheck screen \
  --model-config config/models.local.toml \
  --reuse-from results/benchmarks/deepseek-flash_baseline \
  --name injection_screen_01
```

这里的 `--reuse-from` 是已有 baseline 运行目录；没有旧结果时省略该参数。程序核对兼容性后复用旧预检，缺少的目标才补测：任一次有效成功保留，两次有效失败排除；API/上下文错误、缺失或损坏结果单列为未决，不算能力失败。终端立即显示逐目标进度，执行超过15秒会显示等待提示。

在模型为 `deepseek-flash` 时，先检查：

```text
results/injection_precheck/deepseek-flash_injection_screen_01/summary.md
results/injection_precheck/deepseek-flash_injection_screen_01/status.json
results/injection_precheck/deepseek-flash_injection_screen_01/cohort.json
```

仅当所有目标判定完成时才生成 `cohort.json`。存在未决或运行中断时，解决问题后以相同 name 重复同一条 `screen` 命令，保留已有尝试并继续补测；该阶段不加 `--force-rerun`。更新代码前先停止旧进程；本次已知旧版本兼容范围内可同名续跑，未知模型/任务/防御变化仍要求新 name。详细兼容规则见 [预检与续跑指南](./injection_precheck.md)。

**第二步：用冻结名单运行新的 baseline 和 DSCG 对照。**

```bash
python -m experiments.run_benchmark \
  --cohort results/injection_precheck/deepseek-flash_injection_screen_01/cohort.json \
  --model-config config/models.local.toml \
  --baseline --attack typical --force-rerun --name baseline_screened_02

python -m experiments.run_benchmark \
  --cohort results/injection_precheck/deepseek-flash_injection_screen_01/cohort.json \
  --model-config config/models.local.toml \
  --attack typical --force-rerun --name dscg_screened_02
```

两组使用同一个 `cohort.json`、主模型配置与攻击集合。每个保留场景仍执行全部 user tasks，仅筛选 injection targets；无保留目标的场景明确跳过，全部为空时拒绝启动。输出分别位于 `results/benchmarks/<model_id>_baseline_screened_02/` 和 `<model_id>_dscg_screened_02/`。示例名称已用过时换新名称；不要在旧 full 运行目录上追加筛选结果。

**需要同步收集 L3 路由数据时，将 DSCG 命令替换为 shadow/full 记录：**

```bash
python -m experiments.run_benchmark \
  --cohort results/injection_precheck/deepseek-flash_injection_screen_01/cohort.json \
  --model-config config/models.local.toml \
  --attack typical --force-rerun --name dscg_screened_shadow_02 \
  --audit-router-mode shadow --trace-level full
```

shadow 保留 L3 语义审计，不实际新增免审；无需提供路由 artifact 即可收集资格和分数。任务 JSON 的 `dscg_router_events` 保存逐批记录，场景 `summary.json.audit_router` 保存统计，任务旁的 `.dscg_trace.jsonl.gz` 保存有界 `audit_input`。无有效 artifact 时 `would_bypass=false`，不能据此判断没有路由优化空间。阈值仍需独立标签、相关组和校准；full 增加本地日志开销，不能将这轮观测直接当作 selective 的端到端收益。

筛选测量需同时注意：

- `--cohort` 与 `--clean`、`--task-manifest`、`--write-task-manifest` 互斥，仍需单独运行第3节的 clean 对照。
- 支持 typical 或具体目标型攻击；DoS 不适用此筛选，包含 DoS 的 `--attack all` 也会拒绝。
- `task_scope` 必须为 `screened`，两组 `cohort_sha256` 和实际 task/attack ID 必须一致。额外查看 `screened_run_manifest.json`、`screened_cohort.json` 与 `preflight_report.json`。
- 筛选后计划规模为每种目标型攻击的 `Σ(场景用户数 × 保留目标数)`；下方完整任务规模表不适用于 screened，最终仍按实际有效结果报分母。
- 原生攻击流程仍执行保留目标的预检，相关成本包含在共享总量中；逐目标 usage 不可得时单独预检 Tokens 为 null，不重复累加。独立筛选阶段的成本另在预检目录中报告。

直接请求下的拒绝或失败不证明间接攻击无法成功。screened 结果描述本轮能力筛选子集，不根据 DSCG 结果重新筛选，也不与 full 的 ASR 分母混作防御收益。旧 `run_injection_precheck benchmark` 仅保留兼容转发，仍要求非空 `--cohort`；推荐使用上述统一入口。

### 攻击选择

这些攻击均有 AgentDojo 官方实现。[AgentDojo 发表于 NeurIPS 2024 Datasets and Benchmarks][agentdojo-publication]，[InjecAgent 发表于 ACL Findings 2024][injecagent-paper]。表中区分论文实验与 AgentDojo 官方模板；16 个名称包含消融变体，并非 16 种独立发表的方法。`system_message` 和 `tool_knowledge` 在此仅标为 AgentDojo 官方实现。

| `--attack` 值 | 简要说明 | 类型 | 来源 |
| --- | --- | --- | --- |
| `typical` | 默认运行3种目标型攻击（不含injecagent） | 批量选择 | 本项目选择器 |
| `all` | 显式运行全部 16 种自动攻击 | 批量选择 | 本项目选择器 |
| `direct` | 用 `TODO` 直接要求执行攻击目标 | 目标型 | [AgentDojo §4.2][agentdojo-paper] |
| `ignore_previous` | 要求忽略原指令，改做攻击任务 | 目标型 | [AgentDojo §4.2][agentdojo-paper] |
| `system_message` | 用系统消息标记伪装指令来源 | 目标型 | [AgentDojo 官方模板][agentdojo-baseline] |
| `injecagent` | 用 `IMPORTANT` 和“忽略之前指令”强调攻击目标 | 目标型 | [InjecAgent][injecagent-paper]、[AgentDojo 官方适配][agentdojo-baseline] |
| `important_instructions` | 冒充用户，声称必须先完成攻击目标才能做原任务 | 目标型 | [AgentDojo §4.1–4.2][agentdojo-paper] |
| `important_instructions_no_user_name` | 上述模板中，用泛称代替真实用户名 | 目标型变体 | [AgentDojo 表 2][agentdojo-paper]、[AgentDojo 官方变体][agentdojo-variants] |
| `important_instructions_no_model_name` | 上述模板中，用泛称代替真实模型名 | 目标型变体 | [AgentDojo 表 2][agentdojo-paper]、[AgentDojo 官方变体][agentdojo-variants] |
| `important_instructions_no_names` | 同时用泛称代替用户名和模型名 | 目标型变体 | [AgentDojo 表 2][agentdojo-paper]、[AgentDojo 官方变体][agentdojo-variants] |
| `important_instructions_wrong_user_name` | 换成错误用户名，测试身份线索的影响 | 目标型变体 | [AgentDojo 表 2][agentdojo-paper]、[AgentDojo 官方变体][agentdojo-variants] |
| `important_instructions_wrong_model_name` | 换成错误模型名，测试模型称呼的影响 | 目标型变体 | [AgentDojo 表 2][agentdojo-paper]、[AgentDojo 官方变体][agentdojo-variants] |
| `tool_knowledge` | 在重要指令模板中补充工具调用顺序和参数占位符 | 目标型 | [AgentDojo 官方模板][agentdojo-baseline] |
| `dos` | 要求立即停止当前任务，输出指定文本 | DoS | [AgentDojo 附录 D][agentdojo-paper]、[AgentDojo 官方实现][agentdojo-dos] |
| `swearwords_dos` | 用辱骂内容诱使模型停止任务 | DoS | [AgentDojo 附录 D][agentdojo-paper]、[AgentDojo 官方实现][agentdojo-dos] |
| `captcha_dos` | 声称须先解决验证码，否则停止任务 | DoS | [AgentDojo 附录 D][agentdojo-paper]、[AgentDojo 官方实现][agentdojo-dos] |
| `offensive_email_dos` | 要求发送威胁性消息，诱使模型拒绝并中断任务 | DoS | [AgentDojo 附录 D][agentdojo-paper]、[AgentDojo 官方实现][agentdojo-dos] |
| `felony_dos` | 声称处理当前内容违法，诱使模型停止任务 | DoS | [AgentDojo 附录 D][agentdojo-paper]、[AgentDojo 官方实现][agentdojo-dos] |

[agentdojo-publication]: https://papers.neurips.cc/paper_files/paper/2024/hash/97091a5177d8dc64b1da8bf3e1f6fb54-Abstract-Datasets_and_Benchmarks_Track.html
[agentdojo-paper]: https://arxiv.org/html/2406.13352v2
[injecagent-paper]: https://aclanthology.org/2024.findings-acl.624/
[agentdojo-baseline]: https://agentdojo.spylab.ai/api/attacks/baseline_attacks/
[agentdojo-variants]: https://github.com/ethz-spylab/agentdojo/blob/main/src/agentdojo/attacks/important_instructions_attacks.py
[agentdojo-dos]: https://github.com/ethz-spylab/agentdojo/blob/main/src/agentdojo/attacks/dos_attacks.py

### 三种典型攻击

`typical` 为 `ignore_previous`、`important_instructions`、`tool_knowledge`。`injecagent`仍保留显式与all选择。以下运行全部任务，不是 partial 子集：

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
| `--attack typical` | 3 × 949 = 2,847 |
| 任一 DoS 攻击 | 97 |
| `--attack all` | 当前 11 种目标型 × 949 + 5 种 DoS × 97 = 10,924 |

这些是注册表下的**计划数**，不等于最终有效分母或 API 请求数。目标型攻击还会先把注入任务作为普通任务执行，检查模型是否能完成攻击目标；这些预检不计入上表，但消耗 Tokens。一个计分样本也可能包含多次规划、授权、审计与工具调用。

DoS 按原生任务失败口径计分，每个用户仅执行首个注入 ID 一次；不要将它与目标型 ASR 合并成一个安全结论。最终以实际注册表、manifest、任务 ID 和有效结果为准。

## 5. 结果在哪里，应该核对什么

### 结果文件

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

1. **范围与配对：** 完整任务运行的 `attack_manifest.json` 和各场景 `summary.json` 中 `task_scope` 应为 `full`，所选数等于可用数（DoS/clean 除外）。使用 `--cohort` 时应为 `screened`，用户 ID 仍完整，注入 ID 与冻结名单一致，同时核对两组 `cohort_sha256`。两种模式均须确认 baseline/DSCG 的实际 task/attack ID 一致，仅运行名称相似不足以证明配对。
2. **实际防御：** suite 的 `run_manifest.json` 记录 baseline/full/no-checker profile、L1/L2 控制、模型公开配置、源码哈希和路由身份。baseline 的 defense 应为 null，无安全模型开销；正常 DSCG 保持本指南默认开关。
3. **完整性：** 核对 planned/total/security_missing、运行错误和失败片段。缺失安全结果为未知/基础设施问题，不是安全成功；全部缺失时 ASR 为 null。`summary.md` 的 partial/error 状态也要检查。
4. **指标：** 分别比较干净 TSR、攻击下 TSR、按攻击类型区分的 native ASR，并检查环境终态与代表性失败。计数加权汇总，不能直接平均不同分母的场景百分比。
5. **成本：** 同时看 `overhead`、`sec_overhead` 和 `api_accounting`；主模型开销含其承担的授权与预检调用，统计总量时不要重复相加。缺失 usage 保持未知，使用新名称并 force-rerun 也不能单独证明成本可比。

先读 `summary.md`：指标显示百分比及成功数/分母，Token 区分主模型、审计模型和合计，并标出各场景的成本统计范围。失败索引给出任务 ID、原始 JSON 的相对路径及 `failure_cases.jsonl` 的行号。TSR 失败是 `utility=false`，防御失败是 AgentDojo 原生 `security=true`（ASR 成功）；两者可同时出现，也可单独出现。DoS 使用独立的 `not utility` 口径，不与 targeted ASR 合并。

两个测量入口的 `failure_cases.jsonl` 共用 `dscg.partial-failure.v1`：`failure_types` 区分 `tsr_failure`、`asr_success`、`asr_unavailable`、`result_missing`、`task_error` 和 `run_error`；记录 `trace_path`、`trace_exists`、原生标签与 `excerpt_status`。每例最多保存 6 个片段、每片最多 800 字符，优先选取错误、最后的助手文本、最近的工具调用和能精确匹配注入内容的工具返回；任务描述/攻击目标各最多 400 字符。`source_pointer` 定位原 JSON，字符范围针对文本块拼接或序列化工具调用；`truncated` 显式记录截断。片段是排查线索，不是失败原因证明，也不重新判断攻击成功。

缺失/非布尔安全结果不计入 ASR 分母；缺失的计划任务保留位置及空标签，不伪造 TSR/ASR 结果。运行异常显示 N/A 与异常类型，保留本次中断前已经完成场景的统计，不读取未完成场景的旧 `summary.json`。正常无失败时仍生成空的 JSONL。无攻击轨迹位于 `none/<suite>/<user_task>/none/none.json`。

运行级summary.md和failure_cases.jsonl在本次运行结束时更新，也支持正常缓存读取；不会复制完整轨迹或改写原生任务 JSON。强制终止进程可能尚未生成它们。历史目录不自动补写，使用新运行名称；现有配置绑定仍生效。Agent 测试输出继续显式使用新的 `--results-dir workshop/artifacts/<YYYYMMDD>_<task>/partial_benchmark` 或全量的 `benchmarks` 子目录。

## 6. 中断、缓存和退出状态

- 正式成本对照推荐本指南的**新 name + force-rerun**。模型、工具/schema 或框架开关变化后使用新 name；源码仅在明确审阅的等价过渡下允许reuse兼容；`--force-rerun` 不绕过配置绑定，也不把 partial 缓存变成 full。
- 长任务中断时，用相同name、模型与控制参数加 `--reuse`。未指定攻击/场景时读取原计划；旧typical四攻击继续按四攻击运行。reuse与显式force-rerun互斥，并覆盖DSCG_FORCE_RERUN的强制设置。
- 续跑可能混合历史缓存和新调用，Token 记录不再等同于一次完整新运行。检查 `cost_scope`、`invocation_cost` 与 `cost_comparison_ready`，将其与新鲜匹配成本实验分开；不为获取统一成本而覆盖旧证据。
- 退出 `1` 表示配置/运行或某攻击发生异常；攻击异常被记录后继续后续攻击，不能算成 0-ASR。退出 `2` 通常是命令行参数错误。退出 `0` 只表示流程正常结束，还须检查结果完整性；不表示所有任务成功或真实 E0/安全验收通过。

### 显式续跑示例

```bash
python -m experiments.run_benchmark --reuse \
  --model-config config/models.local.toml \
  --baseline --name full_baseline_typical_01
```

使用原name和结果根目录；DSCG省略baseline并传回原框架控制。cohort测量仍需传同一份 `--cohort PATH`，clean测量仍需 `--clean`。未指定attack/suites时采用原完整名单，因此旧typical可能仍包含injecagent；显式指定必须与原名单一致。想运行新的三攻击实验应使用新name，不能在旧四攻击目录下改分母。

没有根计划的旧目录须显式提供完整原攻击及场景，例如：

```bash
python -m experiments.run_benchmark --reuse --baseline \
  --model-config config/models.local.toml --name baseline \
  --attack ignore_previous injecagent important_instructions tool_knowledge \
  --suites workspace travel banking slack
```

该命令仅适用于这些参数确为原实验范围、其逐场景绑定也可核验的目录。不要根据已经生成的部分子目录推断未启动部分。目录不存在、缺少可核验绑定或任一配置冲突时拒绝续跑；不会自动启动新的全量测量。

旧普通baseline若未记录原生防御选项，须有与原绑定一致的summary明确记录defense，或screened根绑定提供明确证据；缺失时不能推定为无防御，将拒绝reuse。此类目录需用原代码继续，或用新name重新测量。新运行会直接绑定该选项。兼容名单也不覆盖真实防御实现变化。

新普通运行在任务执行前写入benchmark_plan.json，保存完整攻击/场景计划；screened运行使用screened_run_manifest.json。reuse先核对全部已有绑定，仅读取明确哈希映射的等价源码版本；旧manifest和完整缓存轨迹不重写，新增compatibility记录保存原/当前身份。更新汇总前，将原报告和执行清单存到 `reuse/<本次ID>/snapshot/`；原生loader判定不完整、将被重跑的JSON及其侧车也先保存原字节。新缺失场景的绑定可以在全部检查通过后补写。

reuse沿用原生缓存规则：有效成功和任务失败都保留，原生接受的带API错误结果也不自动重试；损坏JSON沿用原报错路径。它补跑缺失/原生未完成的任务，不恢复单个工具动作，也不修正原生评分。无需显式reuse的同版本默认缓存行为继续保留。

cohort续跑分别核对原请求场景和非空的实际执行场景；被筛空场景继续明确跳过，不因续跑重新加入任务。

reuse与 `--force-rerun`、离线清单导出互斥；要求name；显式reuse覆盖DSCG_FORCE_RERUN。Python API使用 `reuse=True`，未指定attack/suites时同样恢复原计划；默认reuse=False。它与screen阶段引用旧预检的 `--reuse-from` 是不同参数。

### cohort 或续跑校验失败

`screening configuration/source/catalog changed` 表示冻结名单的配置、源码或任务目录未通过核验，不等于模型配置文件缺失。当前错误提示区分模型配置、工具元数据与测量证据问题，并列出不匹配的源码路径及预期/实际哈希前缀。先核对导入目录，再查看 `git diff -- experiments/run_partial_benchmark.py` 等提示中的文件；不要修改历史 manifest/cohort 或直接替换兼容映射中的哈希来绕过检查。

例如，CLI 的 `--audit-router-mode` 在解析器中使用 `default=None`，随后根据 profile 选择 DSCG 的 `shadow` 或 baseline/NoChecker 的 `off`。因此无需把解析器默认值改成 `"shadow"`；这种修改会破坏默认分流，并使文件哈希与已审核版本不符。先备份本地差异，再恢复这一处为已审核代码。更新代码时，runner 与两个兼容映射也应一起同步。

旧运行必须沿用原防御设置；原路由为 off 时，即使当前 DSCG CLI 默认 shadow，也应显式传入 `--audit-router-mode off`。Python 与 AgentDojo 版本仍须和原运行一致；兼容映射生成机器的 Python 版本仅作来源记录，不额外限制前后版本相同的服务器。未知源码变更仍拒绝复用，无法核验时使用原代码或新运行名。

需要改变结果位置时，两组都支持 `--results-dir DIR`。用户正式实验默认留在 results；agent 临时检查必须显式隔离，例如：

```bash
python -m experiments.run_benchmark --baseline --attack injecagent \
  --name agent_full_probe_01 \
  --results-dir workshop/artifacts/20261017_benchmark_probe/benchmarks
```

上述probe会调用模型，不是离线检查，仅在需要实际测量时执行。全量任务数量增加不会修复当前工具级权限边界、I3 范围缺口，也不自动完成独立 E0 核查。

## 可选控制与日志

| 参数 | 用途 |
| --- | --- |
| `--name NAME` | 区分运行，保留历史结果 |
| `--baseline` | 匹配当前入口任务范围的原生无防御控制 |
| `--suites NAME [NAME ...]` | 两入口均支持；默认四场景，full保留所选场景全部任务，partial仍取前三个 |
| `--cohort PATH` | 冻结 injection 预检名单；partial仅过滤原前三个目标并保留前三个用户，full保留全部用户 |
| `--attack NAME [NAME ...]` | 具体攻击，可重复该选项；默认 typical，all 显式运行全部 |
| `--force-rerun` | 重跑任务；也可设 DSCG_FORCE_RERUN=1，与显式reuse互斥 |
| `--reuse` | 同name显式续跑，沿用原名单及native缓存；覆盖环境强制重跑，不自动重试错误 |
| `--clean` | 相同用户任务的无攻击效用控制；使用独立运行名称 |
| `--no-checker` | 关闭语义审计，保留工具授权、Monitor、ticket |
| `--trace-level summary/standard/full` | 默认 summary；standard 简化逐条记录；full 详细诊断和压缩侧车，增加写入成本 |
| `--include-extra-info` | full 的兼容快捷开关 |
| `--model-config PATH`、`--tool-metadata PATH` | 覆盖本地模型配置、工具元数据 |
| `--results-dir DIR` | 两个入口均支持；agent 必须指定 workshop/artifacts 下的新目录 |
| `--no-tool-view`、`--no-delegated-tasks` | 工具展示/任务文件展开的对照开关 |
| `--l1-projection-mode off/shadow/projected` | 当前默认 projected；按支持域投影，其他情况回退 |
| `--audit-router-mode off/shadow/selective` | DSCG CLI默认shadow；baseline/NoChecker未显式指定时为off。shadow保留审计并记录观测 |
| `--audit-router-artifact PATH` | 独立分组校准的冻结路由artifact；无有效artifact不增加免审 |
| `--audit-retries 0/1`、`--completion-prompt` | 可选审计重试/完成提示，默认0/关闭 |
| `--task-manifest PATH`、`--write-task-manifest PATH` | 读取/离线导出任务ID；不可与cohort混用，full导入仍须保留所选场景全部ID |

常规对照保持当前默认值：L1/L2/L3开启、CLI路由shadow、审计重试0、completion_prompt=false、trace_level=summary。baseline不使用安全模型，不能启用语义审计消融、非零重试、完成提示或路由观测。完整配置说明见 [模型与工具配置](./model_tool_configuration.md#5-运行控制默认值用途及设置入口)。

Python API/factory仍默认off，网页/API配置不因CLI默认值变化而改变。需要CLI的off对照时显式加 `--audit-router-mode off`；显式shadow/selective与baseline或NoChecker组合仍报错，不静默覆盖。

full tracing只是详细记录，不改变防御逻辑，额外增加序列化、压缩和写盘开销。shadow不实际新增免审；路由阈值仍需独立标签与分组校准。日志与模式名不能代替成本/效用/安全验证。

## 指标与证据

- **TSR**：原生utility成功数/实际返回效用结果数；区分clean与攻击下效用，并另报缺失任务和运行错误。
- **目标型ASR**：原生injection predicate成功数/有效布尔安全结果数。缺失/非布尔标签单列，全部缺失时为null，不当作安全成功。
- **DoS**：按原生`not utility`定义计分，每用户使用首个注册注入目标一次；与目标型ASR分开报告。cohort测量拒绝DoS。
- **成本**：同时核对主模型、审计模型与合计Tokens；原生攻击目标预检包含在共享汇总中，不能重复累加。独立screen成本单独报告；缺少逐次usage时保留未知。
- **分母与可比性**：核对task/attack ID、模型/源码、cohort哈希、suite_scope、实际错误/跳过计数和cost_scope。计划组合不等于有效样本数，不能直接平均不同分母的场景百分比。

保留原始predicate与轨迹。文本判据可能误报，失败片段仅用于定位，需要独立终态复核；小规模回归、单轮观察或正常退出不证明通用安全结论。阶段证据从 [workshop报告索引](../workshop/completed/README.md)查阅，不在本指南维护历史成绩表。
