# 小批量测试：run_partial_benchmark

2026-10-26：默认legacy接入[v352 §4.7事件路由](../workshop/completed/intent_tool_events_20261026.md)。L2第二次请求以宿主固定step-ID键对象增加进度工具关联，不新增调用或权限；授权协议 `intent-global-tools-v4-keyed-event-links`，进度协议 `dscg.intent-progress.host-events.v3`。准备读取可由宿主记录；复杂目标仍需语义判断。`progress_source=host`没有新的response_id，不能沿用上一条模型原文。严格单次直接邀请完成模式不覆盖网站查邮箱／多人／条件／附加交付。新运行名和新配置绑定必需；Dashboard重启后随共享factory采用，无新增控件。


## 默认 DSCG_v3.5

新执行任务的 `.json` 主要保留原生交互和评分，防御记录移至同名 `.dscg.jsonl`；其中保存L3／进度模型的完整返回文本及校验结果，L2只保存解析后的授权。GOAL预检也采用该结构，不增加参数／模型调用，缓存命中和旧文件不改写。`--trace-level`只控制独立诊断详细度；参见[文件说明](./result_files.md#精简任务轨迹与独立诊断)。

full、partial、cohort 共用默认 `legacy / DSCG_v3.5` 意图流程：L2先生成intent及goal_kind，再选全局工具白名单。进度模型只返回satisfaction/evidence_ids，宿主根据真实执行、最终回答与冻结目标类型控制状态及顺序推进；不猜测依赖跳步。L3围绕当前intent和完整原请求约束审计。明确任务不应因未知可查询参数要求用户补充，真实歧义仍须语义判断；每个意图提前结束最多一次继续反馈，不替模型补执行。详见[宿主FSM报告](../workshop/completed/intent_host_fsm_20261025.md)。

已注册、L2允许且参数有效的 public/internal 读取固定免审，包括来自工具结果的博客网址；personal/secret 读取、写入与外发仍审计。免审按工具标签判断，不检查URL或对象隐私；private频道若仍标为internal也免审。混合批次保留次序，分别处理免审读取与待审计动作。`off/shadow/selective` 均不重新审计固定免审读取。

```bash
python -m experiments.run_partial_benchmark \
  --model-config config/models.local.toml --progress --name DSCG_v35_partial_01

# 显式 v3.4 对照，使用独立名称
python -m experiments.run_partial_benchmark \
  --model-config config/models.local.toml --prompt-profile legacy-v34 \
  --progress --name DSCG_v34_control_partial_01
```

命令会调用真实模型。两阶段授权与`intent_progress`独立计入主模型成本，本次没有减少触发频率，不承诺耗时或Token减少。API／超时／内部异常是运行错误；已收到的非法决策、引用及有界无进展仍按原生终止计分，保留已经发生的效果和原生成功。新进度协议必须新name，旧v3.5／v3.4缓存不能跨策略reuse；冻结cohort仍按轻量规则读取，不需重筛。历史`intent-evidence-v35`候选保持旧含义，不是当前默认。[完整机制与边界](./benchmark.md#默认-v35-意图流程)。

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

DSCG CLI默认router shadow，baseline/NoChecker默认off，Python factory/API仍默认off。v3.5的public/internal固定读取免审在这些模式下均生效；其他动作继续L3审计。阈值仅保留作诊断并绑定配置，旧artifact非空仍拒绝；NoChecker才关闭语义审计，但保留意图进度。新策略须用新运行名。

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
