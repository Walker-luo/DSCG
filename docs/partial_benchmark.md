# 小批量测试：run_partial_benchmark

## v3.5 显式候选（未提升默认）

`--prompt-profile intent-evidence-v35` 在 full、partial、cohort 共用实现中选择 **DSCG_v3.5**；不传仍为 **legacy / DSCG_v3.4**，`--name` 不选择策略。候选 L2 一次返回每个动作工具的完整布尔映射 `tool_permissions`，宿主严格检查后合并原自动读取；L3 同次输出有界 `assessment` 与有限代码 `verdict`，分别说明当前用途、参数依据与缺失证据。读取无需提前知道待查询事实；实际写入仍核对目标及已有依据。读取免审范围、Monitor、整批回执和执行票据不变。

本轮300万Tokens后续验证已按用户要求停止：922次请求、919次成功响应、已知1,693,429Tokens，另3次连接故障usage未知。最佳完整六例5/6，但同代码确认4/6，未达提升门槛。当前显式候选恢复到实际执行的round13：L3关闭思考、JSON Object＋严格宿主四字段verdict/三字段assessment、明确执行前审计；主模型/L2不启用思考。最新部分运行仅四条完整、2成功；另有GOAL连接错误和未开始项。未验证的结构化证据候选只存快照，不进入运行入口。见[后续报告](../workshop/completed/v35_followup_20261023.md)。未运行离线回归或完整评测。

最初220次请求的独立阶段仍保留[历史报告](../workshop/completed/v35_live_iterations_20261023.md)，不与本轮合并预算或分母。

显式试用需新名称，以下命令会发起真实模型调用；本次未执行这些扩大范围的命令。已有冻结cohort可继续按轻量规则读取；测量缓存仍绑定实际新协议/策略，不能跨策略reuse。

```bash
python -m experiments.run_partial_benchmark --suites banking slack \
  --model-config config/models.local.toml --prompt-profile intent-evidence-v35 \
  --audit-router-mode shadow --progress --name DSCG_v35_candidate_partial_01
```

当前内部身份为 **DSCG_v3.4**（legacy）：L2保留原生定义，只返回动作授权步骤；L3采用有限短码判决、支持的DashScope/Qwen组合使用严格Schema，其他提供方保留JSON Object与严格宿主校验。读取范围、默认任务前缀、并发和缓存规则不变。两入口共用策略；新name不能复用旧防御缓存，冻结cohort无需因防御更新重筛。[规则与边界](./benchmark.md#默认-v34-策略与复测)。

```bash
python -m experiments.run_partial_benchmark --suites banking slack \
  --model-config config/models.local.toml --audit-router-mode shadow \
  --progress --name DSCG_v3.4_shadow_partial_01
```

此命令会调用真实模型。v3.4与v3.5的固定案例验证均按用户要求跳过离线回归；上方命令本次未执行。shadow继续审计，selective才应用新增免审，不能把shadow的候选统计当实际TSR提升。

DashScope/Qwen与DeepSeek的Chat请求角色由DSCG公共客户端分别适配，不修改conda包；更新后使用新运行名。AgentDyn首次请求的400/422定位、受限诊断字段和小范围复测要求见[消息角色兼容排错](./model_tool_configuration.md#消息角色兼容与请求排错)。旧测量缓存与新增请求身份不一致时拒绝复用，旧数据保留；冻结cohort只比较主模型ID/provider及环境与所选任务，详见[名单校验](./injection_precheck.md#2-中断和错误后续跑)。

在 `DSCG/`、已激活 `ipi`（AgentDojo）或 `ipi-agentdyn`（AgentDyn）环境下执行。安装与依赖自检见 [全量指南](./benchmark.md#安装与依赖自检)，模型/工具配置见 [配置指南](./model_tool_configuration.md)。

## 默认任务范围

当前基准的全部场景，每场景取**注册顺序前3个用户任务×前3个注入目标**。AgentDojo四场景typical三攻击共计划108组合、clean12任务；AgentDyn三场景typical注册计划81组合，其中`tool_knowledge × dailylife`的9组合因原生参考调用缺少`placeholder_args`而标为`unsupported`，可执行计划72组合；clean9任务。seed:7保留为元数据，不改变当前前缀顺序。计划组合不等于API调用次数或有效标签分母，攻击目标原生预检另计。跳过规则、full分母和退出状态见[完整指南](./benchmark.md#1-使用哪个入口)。

AgentDojo可用 `--suites travel banking slack` 选子集，此时clean9、typical81；AgentDyn可用 `--suites shopping github`，此时clean6、typical54。全量正式结果使用 `experiments.run_benchmark`，不是本入口。实际ID查看summary.task_selection或离线导出：

```bash
python -m experiments.run_partial_benchmark --write-task-manifest \
  workshop/artifacts/20261018_dual_local_check/partial_tasks.json
```

## 对照与输出

```bash
python -m experiments.run_partial_benchmark --baseline --force-rerun \
  --model-config config/models.local.toml --name partial_baseline_typical_01

python -m experiments.run_partial_benchmark --force-rerun \
  --model-config config/models.local.toml \
  --name partial_dscg_typical_01
```

baseline使用当前基准原生工具循环，不创建DSCG或安全模型。DSCG默认自动匹配已审查工具目录，切换环境不需要额外参数；自定义目录按配置指南覆盖。默认输出：

```text
results/partial_benchmark/<benchmark_id>/<model_id>_<name>/<attack>/<suite>/
```

分类根目录下先按agentdojo或agentdyn分层，运行目录中不再自动重复后端名；自定义results-dir同样追加该层。旧目录保留，显式reuse的新旧路径查找顺序见[完整指南](./benchmark.md#显式续跑示例)。

运行目录含攻击/执行计划、summary.md和failure_cases.jsonl；逐场景保留原生JSON、CSV及summary。错误、缺失与有效分母分别报告，不能把异常当成攻击失败或防御成功。格式、成本与续跑细节共用 [全量指南](./benchmark.md#结果文件)。

<a id="并发运行"></a>

## 按攻击并行运行

主模型和审计模型默认Qwen3.7-Flash、关闭思考。不同attack默认使用spawn独立进程并行执行，每个attack内部场景、GOAL预检及计分任务仍顺序运行；不新增参数。typical最多3个攻击同时运行，all同时运行全部选定攻击；单个attack和clean保持直接顺序运行。启动打印一次模型与范围；准备阶段静默核对绑定。默认每组打印开始/完成状态，按需加`--progress`显示每个攻击/场景组的独立进度条：

```bash
python -m experiments.run_partial_benchmark --baseline --progress --force-rerun \
  --model-config config/models.local.toml --name qwen37_baseline_01

python -m experiments.run_partial_benchmark --progress --force-rerun \
  --model-config config/models.local.toml --name qwen37_dscg_01
```

默认每场景3×3任务范围不变；兼容的目标型攻击/场景组仍有额外原生GOAL预检。不支持的组在进度条开始前标记`unsupported`，不发起模型请求。进度条将预检与计分任务分开显示；clean只有用户任务，cohort同样支持`--progress`，且不影响同名`--reuse`。进度百分比只是执行项计数，不是ASR分母或剩余时间预测。详见[并行执行与准备信息](./benchmark.md#按攻击并行与准备信息)。这是在线并行，不享受官方Batch折扣；all可能触及服务限流，不增加自动重试。实际加速仍需服务器验证。

## 干净任务对照

```bash
python -m experiments.run_partial_benchmark --baseline --clean --force-rerun \
  --model-config config/models.local.toml --name partial_baseline_clean_01

python -m experiments.run_partial_benchmark --clean --force-rerun \
  --model-config config/models.local.toml \
  --name partial_dscg_clean_01
```

AgentDojo默认每组12、AgentDyn每组9用户任务，无攻击与GOAL预检，ASR/Defense Rate为null。按相同用户任务配对得失，不能把prefix结果作为97/60个完整用户任务的正式clean结果。上述命令真实调用模型，本次接入验收未执行。

## 筛选injection目标

按 [预检指南](./injection_precheck.md)生成新的AgentDyn cohort，然后两组使用同一份文件：

```bash
python -m experiments.run_partial_benchmark --baseline --attack typical \
  --cohort results/injection_precheck/agentdyn/qwen3.7-flash_injection_screen_01/cohort.json \
  --name partial_baseline_screened_01

python -m experiments.run_partial_benchmark --attack typical \
  --cohort results/injection_precheck/agentdyn/qwen3.7-flash_injection_screen_01/cohort.json \
  --name partial_dscg_screened_01
```

示例路径为AgentDyn；AgentDojo目录标识为agentdojo。换成当前环境实际生成的模型/运行目录。用户仍是原前三个，目标为“原前三个ID ∩ cohort保留目标”，不从后续补位；全筛空场景跳过，全部为空拒绝。scope为partial_screened，不能与full screened混用分母。不能同时使用clean/task manifest，拒绝DoS/all。旧名单/缓存不迁移，两套后端之间也不可复用。冻结名单仅核对主模型ID/provider、后端版本与所选任务及文件自身摘要；不读取原预检证据，目录移动不影响读取。实际测量缓存仍按完整请求/防御配置校验。

## 攻击选择与shadow记录

默认typical为ignore_previous、important_instructions、tool_knowledge；具体攻击可重复指定，all查询当前已验证后端注册表并排除manual。injecagent仅显式/all。DoS按首个注册目标、not utility单独计分。上游部分参考调用与GOAL不一致，接入不证明攻击强度。

DSCG CLI默认router shadow，保留L3审计并记录算法观测；baseline/NoChecker默认off，Python factory/API原默认off不变。显式off不关闭L3，no-checker才关闭语义审计。重试0、completion_prompt=false、trace summary保持；selective使用read-purpose-v2的读取规则，无需artifact；--audit-router-threshold保留作诊断，不决定免审。个人/秘密和混合读写仍审计，旧artifact参数非空报迁移错误。策略/阈值仍绑定，须新run名。

AgentDojo保留现有银行L1有限profile；AgentDyn没有新增profile，完整来源封装保留。动态网页/OTP操作按副作用审计；Monitor/票据仍是工具级边界。框架参数见 [配置指南](./model_tool_configuration.md#5-运行控制默认值用途及设置入口)。

## 中断续跑

```bash
python -m experiments.run_partial_benchmark --baseline --reuse \
  --model-config config/models.local.toml --name partial_baseline_typical_01

python -m experiments.run_partial_benchmark --reuse \
  --model-config config/models.local.toml \
  --name partial_dscg_typical_01
```

保持原name、根目录、攻击/场景、模型和有效防御设置；旧运行配置一致也可续跑。未指定attack/suites恢复原计划；clean仍需clean，cohort仍需同一文件。源码哈希、Git commit、Python补丁版本不作为兼容门槛；旧绑定保留，规则变化另存记录。reuse与force-rerun互斥，不自动重试原生接受的错误缓存。配置冲突拒绝且不覆盖历史报告；缓存成本不能当作完整新鲜测量。见[显式续跑](./benchmark.md#显式续跑示例)。

Agent临时测试必须用 `--results-dir workshop/artifacts/<YYYYMMDD>_<task>/partial_benchmark`。用户正式默认仍为results，不迁移旧数据。离线回归与原生模拟不能代替真实E0、重复模型对照或防御收益验证。

## AgentDyn 低 TSR/ASR 只读诊断

对已完成的 AgentDyn 攻击目录，可在 `ipi-agentdyn` 环境运行：

```bash
python -m experiments.diagnostics.agentdyn_zero_rates \
  --run-dir results/partial_benchmark/agentdyn/<model>_<name> \
  --output-dir workshop/artifacts/<YYYYMMDD>_<task>/diagnosis
```

输出目录必须是新目录。脚本只读取原始轨迹与原生标签，报告参考完成路径所用工具与 L2 授权的差集、审计阻断、工具错误、GOAL 预检及注入文本在工具返回中的精确重合。参考路径不是唯一完成路径，文本重合也不等于模型实际遵循注入；缺失、损坏、错误和未执行分组不记为 ASR=0。正式效用与攻击效果仍需同任务、同配置的 baseline/DSCG 对照。

## 工具参数 JSON 错误

单条主模型工具参数发生原生JSON语法错误时，只结束当前任务，记为基础设施错误并继续其他任务；不修补参数、不自动重试，原分母和任务范围不改变。TSR/ASR有效分母排除错误任务，GOAL预检错误另列；progress开关和attack并行采用同一策略，存在错误仍退出1。诊断在每场景`task_errors.jsonl`及本次summary/失败索引中；旧错误不污染新的成功结果。其他JSON异常仍报告原错误。详见[错误处理与续跑](./benchmark.md#工具参数-json-解析错误)。
