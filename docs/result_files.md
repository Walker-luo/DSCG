# 测试结果文件与L3路由汇总

新运行以根目录作为查阅入口，不再生成场景report.txt、攻击级或根级all_report.txt、单独攻击错误TXT。旧报告保留，不自动清理。此改动只影响派生展示，不进入防御/缓存配置身份，不改变模型、路由策略、校准阈值或评分。

## 当前规则的shadow观察（DSCG_v3.3）

read-purpose-v2按普通读取规则产生候选，不用分数/阈值筛选，不输出新规则阈值扫描。报告标记rule_based_unvalidated，分开统计候选的实际审计与Monitor判断、模型协议失败和审计记录校验失败；分歧不是安全标签。shadow仍执行审计，已知候选审计Token仅是反事实可省小计，selective实际总节省未知。缺失轨迹/成本保持未知，原公开免审不计为新增收益。[规则及边界](./benchmark.md#默认-v33-策略与复测)。

## 历史shadow选阈值（2026-10-21）


`threshold-read-v1` 使用经验阈值，默认0.70，不依赖artifact。根级报告按攻击/场景/配置比较0.65/0.70/0.75以及去重后的本次阈值，记录模拟免审、审计allow/deny/abstain分布、协议失败/未知状态及已知/未知审计Token。原公开免审不重复计入新增收益，selective真实Token节省仍未知。

模拟比例只针对已记录事件；缺失轨迹或成本时保留已知小计，完整模拟Token为未知。每次事件保留四个信号、s、阈值、资格及回退原因、审计协议状态、最终Monitor决定和延迟。该统计帮助人工选择阈值，不自动调参，不把审计判断当安全标签。

新策略显示“经验阈值、未独立校准”，没有artifact不是错误；旧 `local_calibrated_algorithm` 记录仍要求原artifact语义，不因新阈值被重新解释。历史报告与结果不自动改写，下文旧校准说明仅适用于旧策略。

## 从哪里开始看

| 文件 | 用途 |
| --- | --- |
| `summary.md` | 配置/范围入口、每攻击/场景一行的TSR/ASR、分母、错误、Token；最多10个失败链接；链接到L3总报告 |
| `l3_router_summary.md` | 全运行及各攻击/场景的路由统计、实际模式、校准状态、原因与完整性 |
| `l3_router_summary.json` | 相同路由统计的结构化版本，包含完整分组配置及问题明细 |
| `failure_cases.jsonl` | 完整失败/缺失案例及有界片段；摘要截取10个入口不减少此文件案例数 |
| 场景`summary.json`、`detailed_results.csv` | 原聚合指标、配置及全部任务结果，供历史页/导出读取 |
| 原始任务JSON及可选full附件 | 原生缓存、动作/审计记录、复核证据；保持原路径和格式 |
| manifests、cohort、execution、reuse/validation快照 | 范围绑定、冻结名单、运行状态和续跑证据；不合并或移动 |

分组异常时，`execution/<invocation>/execution.json` 和 `failure_cases.jsonl` 的对应错误记录可包含 `execution_error`：执行阶段、任务 ID，以及最多 8 个模块/函数/行号。它不保存异常原文、请求、响应或局部变量。`--progress` 可标出 GOAL 预检、计分或 clean 任务；其他入口无法确定具体任务时阶段为 `group`。若模型请求失败，原始任务轨迹的 `dscg_cost.models` 可保留本任务新增的安全 `last_api_error` 诊断；先核对该诊断再判断是否为服务错误，不把分组异常计入有效评分分母。

CLI full/partial/cohort共用精简报告。Dashboard正常完成后也生成上述根级摘要、失败索引与L3报告，同时保留overall_results.json、CSV及原报告下载API；网页没有新增路由模式控件，不会因为报告功能自动开启shadow/selective。CLI中断可生成部分报告，未完成轨迹明确标记；后续续跑更新派生汇总，保留原有配置快照机制。旧TXT不会被清理，但不应当作续跑后的最新汇总。

一般新运行目录：

```text
results/benchmarks/<backend>/<model>_<name>/
  summary.md
  l3_router_summary.md
  l3_router_summary.json
  failure_cases.jsonl
  attack_manifest.json             # 以及实际需要的cohort/执行/绑定记录
  <attack>/<suite>/
    summary.json
    detailed_results.csv
    run_manifest.json
    <user>/<attack>/<injection>.json
```

clean的攻击存储组件仍为none；Dashboard的原生轨迹目录与CSV目录可能不同，汇总器按已记录pipeline名称和任务选择读取，不移动它们。保留大量原生JSON是为了续跑和取证，本轮主要减少重复报告与查阅冗余，不代表磁盘空间可大幅下降。

## 如何理解L3统计

- `coverage`区分计划、成功读取、含事件、明确无候选、路由关闭/原生baseline、缺失、损坏、身份冲突和越界路径。off只是关闭新增路由，**不等于关闭L3语义审计**。
- `candidate_batches`包含记录的全部批次。`previously_audited_batches`表示排除原公开读取免审和L2前置拒绝后、原本需审计的批次；即使selective实际免审，它仍属于此分母。
- `eligible_batches`只表示满足路由适用条件。`eligible_rate`以原本需审计的批次为分母，不平均场景比例，不是安全通过率。
- `would_bypass_batches`为事件中模拟判断，`actual_bypass_batches`为实际新增选择性免审；原公开读取免审单独列示，不能算新增算法收益。
- 缺少/无效校准文件、无认证阈值或不兼容配置时，shadow有效模拟节省显示未知，不能把would_bypass=0解释成已经证明无收益。selective实际Token节省始终未知，没有反事实轨迹就不估算。
- 缺少范围、轨迹或有效事件时，整体审计调用/有效模拟节省保持未知；`known_shadow_would_save_tokens`仅为已知部分的小计，不能替代全运行节省。
- `known_semantic_audit_tokens`只累加可用的计分轨迹事件usage；未知批次/轨迹单列。off缺少路由事件时可从原layer_routing读取已记录调用次数，但不伪造费用。不要再把这些Token加到已有运行总Token上；原总量可能已包含GOAL预检。
- Shadow模拟免审与实际审计allow/deny/abstain的交叉计数只是判断分歧，不是误放率或独立安全真值。未审计事件标记not_audited，不当作丢失的语义判断。
- 实际模式、提示候选、模型/路由配置摘要和校准artifact分组展示；不同组不合并风险分数和阈值。分位数从原事件重新计算，沿用现有floor((n-1)*q)口径，不平均组内P95。原字段缺失为unrecorded/unknown，不推造身份。

读取范围来自当前运行声明的任务列表，只读计分任务，不递归抓取所有JSON。GOAL预检、旧reuse/validation快照及其他运行不会进入统计。缺少声明范围或存在不一致会报告问题；最多展开100条问题位置，完整问题类型计数保留。Markdown列出摘要，JSON保留完整结构。

## 给旧目录补充报告

不需要API Key、模型或安装相同后端；只需能运行标准库Python：

```bash
python -m experiments.diagnostics.summarize_results \
  --run-dir results/benchmarks/agentdojo/qwen3.7-flash_DSCG
```

本轮只对这个指定目录回填。其他旧运行可手动指定路径，支持带声明元数据的CLI当前/旧路径和Dashboard整体结果。默认**仅新增两份l3_router_summary文件**，不改原summary.md、场景summary、CSV、TXT、任务JSON、cohort或manifests；不会自动扫描修改整个results/。

报告已存在时默认拒绝覆盖。确需重新读取原始记录后刷新：

```bash
python -m experiments.diagnostics.summarize_results \
  --run-dir results/benchmarks/agentdojo/qwen3.7-flash_DSCG --refresh
```

refresh只替换具有本工具schema/Markdown标记的两份报告，不覆盖同名个人文件。生成时持有目录锁、检查现有CLI运行锁、临时写入后原子替换单文件；符号链接输出拒绝。先确认运行已停止；Dashboard在另一服务进程中的活动状态不能仅凭文件锁完整识别。两份报告的时间来源相同，若进程在两次替换之间崩溃，可在运行停止后refresh重建。

所有指标只是已保存事件的统计，不验证远端模型版本，不更改研究闸门，也不证明防御有效或阈值已可部署。

## 工具参数错误记录

CLI测量的每个`<attack>/<suite>/task_errors.jsonl`只追加本次新出现的主模型工具参数JSON语法错误，每行含invocation_id、阶段/任务ID、固定错误码、解析位置、参数长度及有限堆栈；不含参数正文、异常原文或凭证。原生轨迹不补造utility/security标签。场景summary.json的task_error_diagnostics仅含本次事件；当前评分及失败索引不扫描历史错误文件来反推失败。

新错误记录还区分`empty_arguments`和`json_syntax`，保存`response_finish_reason`及`response_completion_tokens`；无法取得时为null。`length`可作为输出达到服务长度限制的线索；其他结束原因不能证明参数完整，也不能反推历史错误的原因。

计分/clean错误行的派生标签为空、sample_status=infrastructure_error，保留计划数但排除有效TSR/ASR分母。GOAL预检错误使用goal_preflight阶段与独立计数，根摘要明确显示，不进入评分分母。进度100%表示尝试已结束；有错误仍返回退出码1。API成功返回后发生格式错误，Token已计入，不把它计作HTTP失败。

显式reuse仍由原生loader决定缓存完整性，完整错误缓存不自动重试；缺失/不完整任务按原规则补测并保存旧字节快照。历史task_errors.jsonl原样保留；新尝试成功时只在历史中保留旧错误。screen/Dashboard及其他JSON异常不应用这套单任务隔离。详见[完整指南](./benchmark.md#工具参数-json-解析错误)。

## 审计与交接诊断

v3.2的审计事件保留`mediation_diagnostics`：`checker_parser_status`和受限`checker_protocol_diagnostics`记录原始模型协议观察，`audit_record_status`记录审计记录校验，`router_handoff_status`记录路由回执交接。`failure_stage`分别为`model_protocol`、`model_request`、`audit_record`或`router_handoff`，正常为空；未检查/未知状态不反推模型错误。审计摘要新增`mediation_failure_counts`，并继续保留原始解析计数。

不要仅凭`AUDIT_SCHEMA_INVALID`断定模型JSON格式失败：可能是记录或回执校验失败，即使原始解析为ok仍会拒绝执行。新增字段不保存响应正文或异常原文，不放宽Monitor；旧轨迹缺字段时保留未知，不回填历史结果。

## L2步骤记录（v3.3）

默认授权的 `dscg_authorizations` 每条记录新增 `authorization_protocol=native-steps-v1` 和 `authorization_steps`（intent/tools）。该映射只记录一次授权模型的自述，不认证步骤完整、参数正确或任务成功。`allowed_tools` 仍是工具级有效授权；显式旧候选/受限授权没有这些字段时不补造。新协议和提示身份进入现有绑定，旧策略结果请保留并使用新运行名。
