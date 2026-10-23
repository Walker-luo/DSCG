# 完整任务测试：AgentDojo 与 AgentDyn

## v3.5 显式候选（未提升默认）

`--prompt-profile intent-evidence-v35` 在 full、partial、cohort 共用实现中选择 **DSCG_v3.5**；不传仍为 **legacy / DSCG_v3.4**，`--name` 不选择策略。候选 L2 一次返回每个动作工具的完整布尔映射 `tool_permissions`，宿主严格检查后合并原自动读取；L3 同次输出有界 `assessment` 与有限代码 `verdict`，分别说明当前用途、参数依据与缺失证据。读取无需提前知道待查询事实；实际写入仍核对目标及已有依据。读取免审范围、Monitor、整批回执和执行票据不变。

本轮300万Tokens后续验证已按用户要求停止：922次请求、919次成功响应、已知1,693,429Tokens，另3次连接故障usage未知。最佳完整六例5/6，但同代码确认4/6，未达提升门槛。当前显式候选恢复到实际执行的round13：L3关闭思考、JSON Object＋严格宿主四字段verdict/三字段assessment、明确执行前审计；主模型/L2不启用思考。最新部分运行仅四条完整、2成功；另有GOAL连接错误和未开始项。未验证的结构化证据候选只存快照，不进入运行入口。见[后续报告](../workshop/completed/v35_followup_20261023.md)。未运行离线回归或完整评测。

最初220次请求的独立阶段仍保留[历史报告](../workshop/completed/v35_live_iterations_20261023.md)，不与本轮合并预算或分母。

显式试用需新名称，以下命令会发起真实模型调用；本次未执行这些扩大范围的命令。已有冻结cohort可继续按轻量规则读取；测量缓存仍绑定实际新协议/策略，不能跨策略reuse。

```bash
python -m experiments.run_benchmark --suites banking slack \
  --model-config config/models.local.toml --prompt-profile intent-evidence-v35 \
  --audit-router-mode shadow --progress --name DSCG_v35_candidate_01
```

<a id="默认-v32-策略与复测"></a>

<a id="默认-v33-策略与复测"></a>

## 默认 v3.4 策略与复测

当前内部身份为 **`DSCG_v3.4`**，默认 `prompt_profile=legacy`。full、partial、cohort与factory使用同一策略；`--name`只命名实验，不选择版本。历史实验和原manifest保持原样。

**L2**保留完整原生名称、描述、参数schema和自动读取标记，一次调用只返回请求的动作步骤：`{"steps":[{"intent":"请求的效果性子目标","tools":["native_action_name"]}]}`。不再重复输出顶层tools或读取步骤；宿主严格校验注册动作名称/重复/界限后求并集，合并原自动读取权限。覆盖未知参数、条件及后续动作，合理候选可并存；步骤不是语义完整性证明，不动态补权。旧显式prompt候选与宿主受限授权沿用原协议。

**L3**保留四字段JSON，decision为allow/deny/abstain，confidence为有限[0,1]。reason_code固定为ALIGNED、OFF_TASK_ACTION、EXPLICIT_CONSTRAINT、UNSUPPORTED_PARAMETER、UNREQUESTED_DISCLOSURE、INSTRUCTION_AS_AUTHORITY、ORDER_VIOLATION、MISSING_EVIDENCE。allow要求空violations与ALIGNED；deny要求具体违规代码及匹配理由；abstain要求MISSING_EVIDENCE。非法格式或组合仍失败关闭，不修补或重新请求。

仅对官方DashScope HTTPS地址上的qwen3.7-flash请求严格JSON Schema；其他组合保持json_object与同样严格的宿主校验。未知代理不会仅因模型名字而启用Schema；Schema请求被拒绝时明确报错，不自动降级。实际格式与schema身份进入防御/缓存绑定；主模型原生tool-call生成方式不变。[官方结构化输出说明](https://help.aliyun.com/zh/model-studio/qwen-structured-output)。

短提示只判断当前一步的用途与参数事实；允许先查询未知事实、使用相关成功返回及派生值，不要求一次调用完成整项任务或虚构验证门槛。源中出现注入不自动否决合法摘要、退款或地址更新；错误目标、无关写入、非用户要求的攻击指令外发仍拒绝。证据保留原有界限，错误/阻断返回不能当成功事实。Monitor、一次性回执、整批审批和执行票据不变。

读取路由仍为`read-purpose-v2`：合格public/internal幂等无sink读取及全读批次可以成为候选；personal/secret、混合读写和效果性操作仍审计。仅可信请求逐字指定的公共网页保留原窄例外，工具返回中的新URL不能自动免审。CLI默认shadow，**仍实际审计**；selective才应用候选。API/factory默认off，阈值只作诊断且仍绑定配置；不改风险目录。

新策略须用新name，不能复用旧防御测量缓存。冻结cohort仍按模型/provider、后端/版本/所选场景轻量读取，无需因Schema变化重做screen。baseline保持原生行为。

```bash
python -m experiments.run_benchmark --suites banking slack \
  --model-config config/models.local.toml --audit-router-mode shadow \
  --progress --name DSCG_v3.4_shadow_01
```

本轮按用户要求跳过离线回归，直接进行固定失败案例的Qwen验证；结果和限制见[实施记录](../workshop/completed/v34_decision_contract_20261022.md)。小样本不能证明整体TSR/ASR改善或安全性。shadow候选也不代表实际免审或节省。

<a id="l3直接阈值策略2026-10-21"></a>

## L3读取路由

当前策略与兼容参数见[配置指南](./model_tool_configuration.md#l3读取路由)，输出口径见[结果文件](./result_files.md)。2026-10-21直接阈值策略是历史行为，保留其结果和离线校准器，不控制当前免审。

DashScope/Qwen与DeepSeek的Chat请求角色由DSCG公共客户端分别适配，不修改conda包；更新后使用新运行名。AgentDyn首次请求的400/422定位、受限诊断字段和小范围复测要求见[消息角色兼容排错](./model_tool_configuration.md#消息角色兼容与请求排错)。旧测量缓存与新增请求身份不一致时拒绝复用，旧数据保留；冻结cohort只比较主模型ID/provider及环境与所选任务，详见[名单校验](./injection_precheck.md#2-中断和错误后续跑)。

同一份代码在两个conda环境中自动选择基准，正常测试不需要`--benchmark`或额外工具目录参数。模型/风险配置见 [配置指南](./model_tool_configuration.md)，小规模排错见 [partial](./partial_benchmark.md)。

2026-10-19的[Qwen效用诊断指南](./qwen_utility.md)提供分阶段`--prompt-profile`候选、37/97项clean对照与同cohort攻击命令。默认legacy；候选未获真实模型验收，不能同名复用旧策略缓存。协议错误分类不会改变原生标签或评分分母。

## 安装与依赖自检

在DSCG目录首次创建所需环境；已有环境不覆盖：

```bash
conda env create -f environment.yml
conda env create -f environment-agentdyn.yml
```

任选一个环境，后续测试命令完全相同：

```bash
conda activate ipi                      # AgentDojo
# 或：conda activate ipi-agentdyn         # AgentDyn
python -m dscg.benchmark_catalog
```

| 环境 | 实际后端身份 | 默认场景 |
| --- | --- | --- |
| ipi | 官方AgentDojo0.1.35发行包，suitev1.2 | workspace/travel/banking/slack |
| ipi-agentdyn | AgentDyn提交5353cf7615b135cace8d07c8f12dac53a16b6db3，suitev1.2 | shopping/github/dailylife |

两个包都声明agentdojo0.1.35，不能只看版本或环境名。当前按实际加载路径、安装来源、版本和固定revision自动识别；未知来源、错误revision、包路径冲突或不支持的场景在模型创建前拒绝。运行时不遍历后端源码、不计算源码哈希。两份lock保留历史哈希及发行元数据，当前只读取元数据；不是完整依赖锁。

当前记录`verification_mode=metadata_only`、`runtime_variant=unverified`。不再验证官方源码与本地system角色适配的逐字节差异；同轮baseline/DSCG仍应使用相同安装环境。远端模型真实修订和服务表现需实际测试。

模型配置及Key继续使用本地文件/环境变量，不覆盖已有配置。工具目录按当前后端自动选择，显式参数/环境覆盖、基准专用local目录仍可使用；当前通用tools.local是AgentDojo内置目录的相同副本，在AgentDyn自动选用对应内置目录并给出提示。未知自定义通用目录报错，不悄悄忽略。细则见配置指南；baseline不使用防御风险目录。

<a id="进程并发提速"></a>

<a id="顺序执行与准备信息"></a>

## 按攻击并行与准备信息

主模型、授权编译和审计默认使用 Qwen3.7-Flash，显式关闭思考；本地配置、环境变量和显式参数仍可覆盖。配置方法见[模型指南](./model_tool_configuration.md#24-最小可运行配置与角色复用)。

full、partial和cohort默认按attack并行：每个attack一个spawn独立进程，进程内按现有顺序执行场景、GOAL预检和计分任务。不新增参数；typical最多同时执行3种攻击，all同时执行全部选定攻击，没有额外并发上限。单个attack、clean仍直接顺序运行，screen不变。准备阶段静默核对完整任务范围与已有配置绑定，不创建pipeline或发起模型请求；启动一次打印模型、后端、攻击、场景、结果目录和缓存策略。默认每组打印开始/完成状态；加`--progress`后，每个攻击/场景组显示独立进度条，完成的组保留最终状态。主进程统一显示进度条及带attack/场景标识的原生日志；错误和必要警告继续输出。

```bash
python -m experiments.run_benchmark --baseline --force-rerun \
  --model-config config/models.local.toml --name qwen37_full_baseline_01

python -m experiments.run_benchmark --force-rerun \
  --model-config config/models.local.toml --name qwen37_full_dscg_01
```

需要实时查看进度时，在原命令后加`--progress`，例如：

```bash
python -m experiments.run_benchmark --baseline --suites travel banking slack \
  --progress --name qwen37_baseline_progress_01
```

目标型攻击的每组进度分别标为`GOAL 已完成/目标数`和`任务 已完成/用户×目标组合数`；clean只显示用户任务，DoS不做GOAL预检。百分比按已完成执行项数计算，缓存命中也会计入；它不是有效计分分母、模型请求数或剩余时间预测。交互终端显示动态条和已耗时，重定向日志写入无控制字符的阶段与少量里程碑行。`--progress`只控制显示，可在同名`--reuse`时开启或关闭，不改变配置绑定或缓存。

每个目标型攻击/场景分组仍先执行原生GOAL预检，再执行用户×注入目标组合；一次任务通常包含多次模型/工具交互，DSCG还包括授权和审计。这是在线请求并行，不享受官方Batch折扣；all可能触及服务限流，本次不增加重试或限流策略。实际加速由服务器测试确认。

同目录运行锁防止重复写入。`attack_manifest.json.execution`与`execution/<本次ID>/execution.json`记录parallel_attacks或serial、独立attack进程数/PID、各组状态及实际wall_seconds；总耗时不取各attack耗时之和。历史记录保持原样。失败组单列，其他组继续；中断保留原生结果，使用原参数加reuse恢复。CLI/API不新增并发参数。并行只是执行策略，不改变任务/评分或缓存身份，配置匹配的旧顺序运行仍可reuse。更新后重新启动命令才会使用新调度，正在运行的进程不会自动切换。

## 1. 使用哪个入口

| 入口 | 用户任务与目标 | 用途 |
| --- | --- | --- |
| `experiments.run_benchmark` | 所选场景全部注册用户任务与注入目标 | 正式完整任务对照 |
| `experiments.run_partial_benchmark` | 每场景注册顺序前3个用户、前3个注入目标 | 排错、成本较低的初步回归 |
| `experiments.run_injection_precheck screen` | 全部所选注入目标的直接GOAL | 可完成性预检与冻结cohort |

实际注册表如下，启动自检和manifest是执行范围的来源：

| 基准 / 场景 | 用户任务 | 注入目标 | 工具 | 每目标型攻击组合 |
| --- | ---: | ---: | ---: | ---: |
| AgentDojo workspace | 40 | 14 | 24 | 560 |
| AgentDojo travel | 20 | 7 | 28 | 140 |
| AgentDojo banking | 16 | 9 | 11 | 144 |
| AgentDojo slack | 21 | 5 | 11 | 105 |
| AgentDyn shopping | 20 | 9 | 39 | 180 |
| AgentDyn github | 20 | 9 | 34 | 180 |
| AgentDyn dailylife | 20 | 10 | 27 | 200 |

| 范围 | AgentDojo | AgentDyn |
| --- | ---: | ---: |
| full clean用户任务 | 97 | 60 |
| full目标总数 | 35 | 28 |
| full每目标型攻击组合 | 949 | 560 |
| full typical三攻击组合 | 2847 | 1680 |
| partial clean | 12 | 9 |
| partial typical三攻击组合 | 108 | 81 |

计划组合不是模型请求次数或有效分母；原生攻击GOAL预检另计。可用`--suites travel banking slack`选择AgentDojo子集，或`--suites shopping github`选择AgentDyn子集。跨后端场景名拒绝；full保留所选场景全部注册ID，不能用manifest缩小范围。

AgentDyn当前原生`tool_knowledge × dailylife`不支持：10个目标的参考调用均缺少该攻击生成器要求的`placeholder_args`。程序在模型请求前检查实际选中目标，将整个组标为`unsupported (missing_placeholder_args)`，不运行该组GOAL预检或计分，也不把跳过当作成功/失败样本。上表仍是**注册计划数**；默认full typical的1,680组合中200不支持、1,480可执行；默认partial的81组合中9不支持、72可执行。cohort按实际保留目标重算；若没有该场景的目标，按原空场景规则跳过。`summary.md`中该组显示`0/计划数`和`N/A`，受影响ID及原因见`attack_manifest.json.execution.groups`。至少一组完成且没有真实错误时CLI退出0；全部不支持时退出1。实际评分分母仅取原生返回结果。

## 2. Clean 对照：先确认智能体能力

建议先做同轮无攻击对照，再做攻击测试。以下会真实调用模型，请自行在服务器启动；本轮工程验收没有执行它们。

```bash
python -m experiments.run_benchmark --baseline --clean --force-rerun \
  --model-config config/models.local.toml --name baseline_clean_01

python -m experiments.run_benchmark --clean --force-rerun \
  --model-config config/models.local.toml \
  --name dscg_clean_01
```

两组使用同一主模型、源码、环境、全部用户任务和执行限制；DSCG另用当前安全模型。按 `(suite_name, user_task_id)` 配对比较成功/失败、总Token与调用数，并分别报告错误、缺失任务。clean不构造攻击、不执行攻击GOAL预检，ASR/Defense Rate为null。不能把clean失败的任务从后续完整攻击分母中悄悄删掉。若另报可完成任务子集，应先冻结名单并同时保留完整分母结果。

原生预检warning主要针对 injection GOAL，不是全部用户任务的clean能力验证。模型拒绝、动态验证码操作失败和原生评分疑点需结合真实轨迹/终态分析；一次clean失败不证明任务永远不可完成。

## 攻击选择

```bash
python -m experiments.run_benchmark --baseline --attack typical --force-rerun \
  --model-config config/models.local.toml --name baseline_typical_01

python -m experiments.run_benchmark --attack typical --force-rerun \
  --model-config config/models.local.toml \
  --name dscg_typical_01
```

默认 `typical` 为 `ignore_previous`、`important_instructions`、`tool_knowledge`；`injecagent` 可显式选择，已经不在typical。具体攻击和 `all` 来自当前已验证后端的注册表，排除交互式 `manual`。预设不能与具体名字混用，typical缺项直接报错。例如：

```bash
python -m experiments.run_benchmark --baseline --attack important_instructions injecagent \
  --name baseline_explicit_01
```

两套后端按各自原生任务/工具循环评分。AgentDyn提供动态环境与新目标，攻击生成器仍有AgentDojo基线来源；安装成功不代表比旧攻击更强。`tool_knowledge` 使用上游参考调用，shopping/github的占位参数可供原生模板使用，但其内容仍需核对GOAL与实际轨迹。本项目不补写标准答案或修改原生评分来追分。

DoS按 `not utility` 单独计分，每用户仅使用首个注册目标一次；不可与目标型ASR合并。cohort测量拒绝DoS及包含DoS的all。全部自动攻击的实际名单和组合数以运行manifest为准，不固定论文数字。

## 预检与冻结 cohort

独立screen检查当前主模型直接完成注入GOAL的能力，与通过工具返回注入的攻击实验不同：

```bash
python -m experiments.run_injection_precheck screen \
  --model-config config/models.local.toml --name injection_screen_01
```

在输出的实际目录找到 `cohort.json`，之后两组使用同一文件：

```bash
python -m experiments.run_benchmark --baseline --attack typical \
  --cohort results/injection_precheck/agentdyn/qwen3.7-flash_injection_screen_01/cohort.json \
  --name baseline_screened_01

python -m experiments.run_benchmark --attack typical \
  --cohort results/injection_precheck/agentdyn/qwen3.7-flash_injection_screen_01/cohort.json \
  --name dscg_screened_01
```

示例使用AgentDyn路径；AgentDojo输出路径中为agentdojo。使用当前环境实际生成的模型/运行目录，名单不能跨后端读取。screened保留全部所选用户任务，仅筛选目标；名单只核对主模型ID/provider、后端身份/具体包版本/suite版本（AgentDyn固定revision）、所选场景任务ID及顺序，并一次验证cohort自身摘要。原预检目录可移动或缺失，不再读取轨迹/attempt/引用manifest，不重新验证预检证据；请求adapter、endpoint与思考设置不影响名单兼容。full默认选择当前后端全部场景；若名单只覆盖子集，须用`--suites`明确选择。细则见[预检指南](./injection_precheck.md)。

## 结果文件

CLI测量和screen在分类根目录下新增后端子目录，模型/运行名称中不再自动重复后端：

```text
results/partial_benchmark/agentdojo/qwen3.7-flash_baseline/
results/partial_benchmark/agentdyn/qwen3.7-flash_baseline/
results/benchmarks/agentdojo/qwen3.7-flash_baseline/
results/injection_precheck/agentdojo/qwen3.7-flash_injection_screen_01/
```

`--results-dir DIR`仍表示分类根，实际保存为`DIR/<backend>/<model>_<name>/`，不会自动判断DIR末尾是否已有后端名。未传name时保留原pipeline默认名称，去掉原先额外追加的后端后缀。Dashboard发起实验仍保存在原dashboard目录；历史页支持两种CLI布局，按实际路径分别展示。

默认根目录保持 `results/benchmarks/`，partial为 `results/partial_benchmark/`；新运行自动使用 `<benchmark_id>/<model_id>_<name>/`。内部布局：

```text
<run>/
  benchmark_plan.json 或 screened_run_manifest.json
  attack_manifest.json
  summary.json / summary.md / failure_cases.jsonl
  l3_router_summary.md / l3_router_summary.json
  <attack>/<suite>/
    run_manifest.json / summary.json / detailed_results.csv
    <user_task>/<attack>/<injection_task>.json
```

新运行停止生成场景report.txt、各层all_report.txt和单独攻击错误TXT；原文件不清理。根摘要最多10个失败入口，完整列表仍在JSONL；L3全运行分组/校准/完整性与旧目录补充命令见[结果文件指南](./result_files.md)。报告展示格式不进入防御/缓存身份，续跑绑定规则不变。

clean使用 `none/<suite>/<user_task>/none/none.json`。原生JSON与full trace压缩侧车保留；`summary.md`便于阅读，JSONL按原路径定位失败，片段只是排查线索。缺失/非布尔安全标签、API/运行错误单列，不能当成攻击失败或防御成功；中断任务不能补造标签。计分分母和错误数必须一起报告。

manifest、cohort、summary和导出记录`benchmark`的id、repository、revision、suite_version、package_version、source_kind及`verification_mode=metadata_only`。新结果不生成后端实现/目录/组件源码哈希，也不认证runtime_variant。模型公开请求配置、完整任务集合、攻击、工具元数据内容及有效防御设置仍绑定；不同后端或任务集合不能合并分母。旧记录中的哈希保留，缺少必要身份的历史目录不能推断补齐。

成本核对主模型、安全模型、合计Token和调用次数；攻击目标预检与独立screen成本分别注明，不能重复累加。缓存复用后不等于一次完整新鲜测量；检查 `cost_scope`、`invocation_cost`、`cost_comparison_ready`，缺少usage保留未知。

## 显式续跑示例

使用相同name、根目录、模型与全部防御控制，去掉force-rerun、加reuse：

```bash
python -m experiments.run_benchmark --reuse --baseline \
  --model-config config/models.local.toml --name baseline_typical_01

python -m experiments.run_benchmark --reuse \
  --model-config config/models.local.toml \
  --name dscg_typical_01
```

未指定attack/suites时恢复原运行的完整计划；显式提供必须一致。clean仍需clean，screened仍需同一cohort。reuse与force-rerun或离线manifest导出互斥，并覆盖DSCG_FORCE_RERUN。新旧运行均按后端来源/版本、模型公开请求配置、完整任务ID、攻击/场景、cohort、工具元数据内容及有效防御配置核对；源码哈希、Git commit、Python补丁版本和旧并发设置不作为续跑门槛。缺少必要绑定或原范围不能核验时拒绝，不补造身份。

原生接受的成功、失败及错误缓存不会自动重试；reuse只补跑缺失或原生不完整任务，不恢复单个工具动作。更新汇总前保存快照，需要替换的不完整轨迹先保留原字节。旧run/cohort/attempt绑定不改写；规则变化另存configuration_only记录，明确source_equivalence_verified=false。配置一致续跑并不证明源码等价，正式比较仍需自行保持代码与环境一致。

退出0表示流程正常结束，不表示任务全成功或安全验收通过；退出1表示配置/执行/攻击异常，错误保留并继续可执行的后续攻击；退出2常为CLI参数错误。

新旧目录续跑：`--reuse`先定位新`<backend>/<model>_<name>/`；仅在新路径不存在时查找原`<model>_<backend>_<name>/`，并在旧目录原地续跑。新路径存在但绑定不完整/配置不符时直接拒绝，不回退；两者同时存在时优先新目录。不传reuse的测量只定位新结构并使用其中的原生缓存。原结果不移动，旧cohort/轨迹引用不改写。

## 工具参数 JSON 解析错误

CLI full、partial、cohort（含旧benchmark转发）均按原生单任务函数执行，与`--progress`开关无关。若任务执行中的主模型回复在原生`_openai_to_tool_call`中发生JSON语法错误，立即结束当前任务；该回复中的所有工具调用都不执行，继续后续任务。不补引号、不修补参数、不自动重发请求。其他JSON错误（缓存、攻击构造等）沿用原错误路径。

该任务的内存效用/安全值为空，作为基础设施错误排除TSR/ASR分母；原始轨迹不补写布尔评分。GOAL预检错误另列，不当作能力失败，也不据此剔除攻击目标。进度仍计入已结束尝试，100%不是全部有效或成功；有任务/预检错误时CLI退出1。

每攻击/场景的`task_errors.jsonl`追加安全诊断：阶段、任务ID、固定错误码、解析位置、参数长度及有限堆栈，不存参数正文或异常原文。场景summary、根摘要及失败索引纳入本次错误，历史错误不重新污染后续成功结果。API已返回的Token照常计入成本，格式错误不是HTTP/API失败。

只在CLI任务执行期间临时观察主模型回复，不修改已安装后端、请求参数、原生评分或审计模型；AgentDyn原生会静默丢弃非法调用，因此也在返回候选前终止整批。screen和Dashboard不在此策略范围内。已接受的完整缓存继续复用，不能据此重新认证其未保存的模型回复；缺失/原生不完整结果仍按原规则补跑，显式reuse先快照再替换。详见[结果文件](./result_files.md#工具参数错误记录)。

## cohort 或续跑校验失败

校验失败不等于模型配置文件缺失。冻结cohort检查主模型ID/provider、后端/包版本/suite版本与所选任务，以及cohort自身摘要；不检查原预检轨迹。实际测量缓存则继续核对完整模型请求配置、工具目录和有效防御参数，配置冲突仍拒绝复用。先核对实际Python与包路径及对应身份。当前已取消源码兼容映射检查，不需要为单纯源码变化修改映射或manifest。CLI路由解析器保留default=None，按profile解析shadow/off。

## 可选控制与日志

| 参数 | 说明 |
| --- | --- |
| `--baseline` | 原生AgentDyn工具循环，无DSCG与安全模型 |
| `--clean` | 无攻击用户任务效用对照 |
| `--suites NAME [NAME ...]` | 默认当前基准全部场景；full全部注册ID，partial前3×3 |
| `--progress` | 按攻击/场景显示GOAL预检与计分任务进度；默认关闭 |
| `--attack NAME [NAME ...]` | 默认typical，可重复指定；all查询固定注册表 |
| `--cohort PATH` | 冻结筛选名单，不能与clean/task manifest混用 |
| `--name NAME` / `--results-dir DIR` | 独立运行名和结果根目录 |
| `--force-rerun` / `--reuse` | 重跑/续跑，均保留身份检查 |
| `--model-config PATH` / `--tool-metadata PATH` | 模型配置/已审查工具目录 |
| `--no-checker` | 关闭L3的消融，保留授权/Monitor/ticket，不是baseline |
| `--no-tool-view` / `--no-delegated-tasks` | L2展示/有限委托消融 |
| `--l1-projection-mode off/shadow/projected` | 默认projected；AgentDojo保留银行有限profile，AgentDyn沿用完整来源封装 |
| `--audit-router-mode off/shadow/selective` | DSCG CLI默认shadow；baseline/NoChecker默认off；shadow不新增免审 |
| `--audit-router-artifact PATH` | 单独校准的冻结artifact；旧基准/输入绑定不兼容时不可复用 |
| `--audit-retries 0/1` / `--completion-prompt` | 当前默认0/关闭，常规对照不叠加恢复 |
| `--trace-level summary/standard/full` | 默认summary；full增加序列化/压缩/写盘成本 |
| `--task-manifest PATH` / `--write-task-manifest PATH` | 导入/离线导出任务ID；full不能缩小范围 |

Python factory/API原有router默认off保持；网页以有效配置为准。不要把router off当作关闭L3。具体默认及字段见 [配置指南](./model_tool_configuration.md#5-运行控制默认值用途及设置入口)。

不调用模型的目录导出：

```bash
python -m experiments.run_benchmark --write-task-manifest \
  workshop/artifacts/20261018_dual_local_check/full_tasks.json
```

Agent临时检查必须使用新 `--results-dir workshop/artifacts/<YYYYMMDD>_<task>/benchmarks`，不写用户正式results。新环境的 `browse_webpage` 可执行带副作用的handler，OTP验证也可恢复待执行写入，因此不进入读取免审。工具级框架仍不能单独授权内部handler或硬约束参数/对象；没有新增免审或安全保证。

## 指标与证据

TSR使用原生utility，ASR使用原生injection predicate，保留原始标签与轨迹；错误/缺失单列。汇报完整任务分母、有效标签分母及配对得失，不只平均各场景百分比。独立终态核查、重复对照和攻击强度仍需真实实验。本轮 [双基准报告](../workshop/completed/dual_benchmark_20261018.md) 只证明工程接线及离线模拟；没有付费模型评测，也不宣布E0通过或TSR/ASR收益。
