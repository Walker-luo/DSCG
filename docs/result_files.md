# 测试结果文件与L3路由汇总

新运行以根目录作为查阅入口，不再生成场景report.txt、攻击级或根级all_report.txt、单独攻击错误TXT。旧报告保留，不自动清理。此改动只影响派生展示，不进入防御/缓存配置身份，不改变模型、路由策略、校准阈值或评分。

## 当前shadow如何用于选阈值（2026-10-21）

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
