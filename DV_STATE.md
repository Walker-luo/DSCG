# DSCG Project State

> 更新日期：2026-10-26（Asia/Shanghai）。范围：按v3.5.1后续方案实施、在线消融与独立确认（进行中）；基准代码内部为 **DSCG_v3.5.1**（历史v3.5运行保存的内部版本仍为v3.4.1）。运行事实依据当前代码和保存配置；研究任务边界依据 [technical_route.md](../research/technical_route.md)。
>
> 后续工作顺序：**复用现有配对账 → 定位残余漏授权／误拒 → 单项改动 → 新名称复测**。每次阶段完成时更新本文件的代码状态、进行中任务、问题和验证摘要，详细过程放阶段报告。

## 1. 项目概述

- **研究目标：**防御工具使用型 LLM Agent 接收外部工具内容时遭遇的间接提示词注入，同时控制用户任务成功率损失和模型成本。
- **核心技术方案：**L1 构建隔离的规划视图，有限银行任务使用结构投影；L2 根据可信任务、完整原生工具定义和参数 schema 编译工具授权；L3 审计当前动作与任务的关系。Reference Monitor、一次性回执与执行票据负责执行前复核。
- **当前开发阶段：**已按候选方案实现独立源码快照并开始真实Qwen消融；P0记录及静态任务视图相关124项回归通过（4跳过）。最终候选尚未选定，不把短试作为正式benchmark结果。
- **评测环境：**AgentDojo v1.2；`ipi` 当前为 Python 3.10.21、AgentDojo 0.1.35，配置模型为 DashScope `qwen3.7-flash`。后端识别属于 metadata-only，不认证远端服务或源码等价性。
- **研究状态：**E0 pending；I3 partial（24 个有效探针、8 个范围违规）；I2 locked。对象／数据／参数授权及已关闭 provenance/source-to-sink 路线没有重新解锁。

## 2. 当前代码状态

| 项目 | 当前快照 |
| --- | --- |
| Git Branch | `workshop` |
| HEAD Commit | `2fb274de67b514bf02a085fc8d0c0dcdc3a8c796`；`v3.5.1:针对TSR、ASR进行优化` |
| HEAD 提交时间 | 2026-10-26 14:10:05 +08:00 |
| 工作区是否有未提交修改 | 继承上一轮分析改名／归档文档；本轮修改P0记录、SDK重试配置及静态任务视图候选。未暂存／提交；正式results、download和credentials保持原样。最终采用范围待独立确认。 |
| 实际默认运行策略 | `prompt_profile=legacy`，内部 `FRAMEWORK_VERSION=DSCG_v3.5.1`，见 [input_isolation.py](dscg/input_isolation.py) 和 [defended.py](dscg/pipelines/defended.py)。 |
| AGENTS.md | HEAD 已收录精简后的规则；其部分跨分支框架描述与本分支代码存在差异，执行机制须逐项查当前实现。 |
| 最近更新时间 | 2026-10-26；本轮聚焦117例／89个失败并复原证据选择统计，新增模型调用0；上轮4,476份轨迹配对与历史231次在线计分独立保留。 |

运行名不选择策略；目录名称、保存的 pipeline 名、配置身份和实际代码需分别核对。历史结果不因本次迁移改写或重新标记。

## 3. 已完成的工作

- [x] L1 来源封装与有限银行月支出投影；原始返回继续保留供审计与原生轨迹使用。
- [x] v3.4 L2 动作步骤授权：根据完整原生定义输出有界步骤，由宿主求动作工具并集并合并自动读取权限；整批权限前置检查和授权规划视图已接入。
- [x] v3.4 L3 当前动作审计：有限四字段判决、严格宿主校验和受限证据上下文；Monitor／回执／票据执行链已接入。
- [x] full、partial、cohort 和 Dashboard 使用共享工厂及评分／读取路径；原生 baseline 独立执行。
- [x] 从 `2d57bc7` 迁入单次 injection GOAL 筛选：每目标一次，成功保留，失败／错误分别处理，续跑只处理未开始目标；旧冻结名单保留原语义。
- [x] 从 `d457369` 迁入适用于当前 v3.4 的独立诊断、L3 原始回复附件、分层阻挡来源、共享读取器和续跑快照支持。
- [x] 对迁移完成 12 个真实计分案例的记录链路验证；结果、调用量和限制见 [迁移报告](workshop/completed/workshop_commit_transfer_20261025.md)。
- [x] v3.4.1：L2逐工具布尔权限一次编译；public/internal读取固定免审（含混合批次）；私人读取拒绝执行；L3按当前阶段／实际参数组织输入；整批schema与off回执校验；现有完成提示单独对照且默认关闭。
- [x] 定位历史 v3.4 与 baseline 正式结果，并完成1,167对任务／2,334份轨迹的 outcome、注入文本与元数据核对；程序提取全量失败信号，人工核对代表案例。结论见 [归档v3.4分析](workshop/archive/v34_analysis_20261025.md)，不等同于全量独立语义审计。

## 4. 当前进行中的工作

- **本轮实施（进行中）：**用户已批准按方案优化并在线测试。[执行账](workshop/artifacts/20261026_v352_optimization/progress.md)、[固定选样](workshop/artifacts/20261026_v352_optimization/selection.json)、[源码哈希](workshop/artifacts/20261026_v352_optimization/source_hashes.json)。六臂各42个原生计分案例：24攻击重点、6clean、7历史ASR控制、5合法／只读控制；初轮无效用提升的风险字段臂、明显退步的初始隔离延后臂不推广。任务呈现／静态任务视图均10/24，对照7/24；标记臂9/24，均尚需独立确认。
- **确认与限制：**关闭SDK重试并绑定配置后，以新源码／运行名确认117个重点攻击案例及18个控制；保留24个短试键与93个未用于选候选的键的分层统计。只做任务子集，不是完整benchmark。首次沙箱网络失败没有响应，记录保留；其后获得网络权限并收到真实响应。旧初轮SDK未显式关闭重试，实际传输尝试数存在未知；最终确认固定max_retries=0。没有重试筛选GOAL、改日期或评分。
- **任务：**最新入口[analysis/v3-5-1.md](analysis/v3-5-1.md)。原v3.5分析与批准方案已[归档](workshop/archive/v35_analysis_20261026.md)，原优化[报告](workshop/completed/v35_optimization_20261026.md)保留各阶段，不把专项37例推广为正式结果。
- **输入与口径：**`results/benchmarks/agentdojo/qwen3.7-flash_DSCG_v3.5.1`与`download/dscg-history-analysis-20261026T080824Z`；四版本共同1,119键／4,476主轨迹，逐例注入一致。v3.5旧有1例参数JSON错误排除后1,118组共同有效；新版自身1,119例全valid。injection_task_8为正常cohort过滤，不作为问题。
- **正式结果：**共同有效banking383例，baseline270成功／v3.5为232／v3.5.1为231；Slack315例分别223／186／188；travel420例分别233／319／322。新版整体原生ASR0。银行新版全量原始为232/384，不能与旧错误样本混分母。
- **TSR原因：**banking恢复29／退步30，Slack恢复23／退步21。u15仍17/24漏授退款；u4退款17个失败均已授权、无L3阻挡、未提出转账；u11付款24/24有授权却全失败，其中7例无任何工具调用。Slack u13的11个失败均有私信阻挡，u17六例均拒绝用户指定的Dora网站，合法读取新退步抵消其他任务改善。
- **当前优先：**banking u11/u15比baseline少29次成功（场景净差39）；Slack u11/u13/u17少24次（净差35）。区分漏授权、实际参数错误、语义误拒、主模型停办，不把所有失败归为L3／证据预算。
- **证据：**[四方配对账](workshop/artifacts/20261026_v351_analysis/paired_analysis.json)、[原因计数](workshop/artifacts/20261026_v351_analysis/root_cause_counts.json)、[输入哈希](workshop/artifacts/20261026_v351_analysis/input_hashes.json)。本轮仅分析，没有新Online Evaluation／运行时回归；全量独立oracle审计仍未完成。
- **详细诊断：**[117例报告](workshop/completed/v351_tsr_diagnosis_20261026.md)：109条有调用轨迹的统计全部匹配，8条无工具调用；Slack u11/u13/u17相关阻断没有窗口遗漏／截断。u11付款26次提议全部被拒、金额目标一致但日期14种；当前安装utility只看200.29，不能把全部拒绝定为误拒。
- **待实施方案：**[候选A/B](workshop/v351_next_optimization_20261026.md)：先补紧凑输入引用，分开消融L3诊断字段／任务条目、L1激活时机／标记；再评估多一次前置调用的静态任务视图与全局授权。风险字段影响、L1初始提示影响仍是假设；无新完成性账本、状态机、自动恢复、参数补造或动态扩权。

## 5. 关键技术决策

| 决策 | 选择原因 | 暂不采用的做法及原因 |
| --- | --- | --- |
| v3.4.1采用组合优化 | L2／读取单改均8/18，组合15/18，说明两点单独不足以解决银行问题 | 完成提示同为15/18且成本更高，默认不启用；不优先改L1投影／阈值 |
| 按工具定义／schema、已授权能力和当前动作进行判断 | 步骤文字、来源命令、模型解释不能授予权限或证明任务完成 | 不引入对象／数据／参数授权、动态扩权、参数修补或恢复机制；相关研究边界仍受锁定 |
| sink-free-read-v4分流 | 授权且schema有效、无sink的public/internal读取三模式免审；外部接收方读取恢复L3，混合批次只审计其余调用 | 保留工具级隐私／URL查询外传限制；不新增对象／参数授权，不重标银行personal |
| 审计与宿主分工一致 | 私人／秘密读取的有效deny与abstain均阻断；非敏感无sink读取由宿主确定性允许 | 删除旧READ_ONLY_SOURCE_ALLOW私人deny例外；整批权限／schema、回执／票据继续约束全部动作 |
| 原生评分、错误分母、成本分开记录 | 工具拒绝、模型协议错误、API故障、真实任务失败含义不同 | 不把错误样本计成成功防御、不把警告引用谓词直接当真实恶意效果 |
| 原始交互与诊断分文件，历史数据保留原样 | L3 回复在解析前保存，便于排查合法字段下的语义误拒和协议错误 | 不补造历史原回复、不回写旧结果／cohort、不通过换模型或评分获得通过 |

当前 L3 使用的 evidence 是有限上下文，不是参数来源或对象隐私的认证。当前固定读取免审要求sink=none，不依赖URL来源、词法阈值或幂等标签；依据已注册工具effect/sensitivity/sink及授权／schema。旧read-purpose-v2仅描述历史运行，详见 [README 当前流程](README.md#当前框架与工作流程)。

## 6. 已知问题

| 问题描述 | 影响范围／已尝试方法 | 后续处理建议 |
| --- | --- | --- |
| 正式v3.5.1 TSR仍低于baseline | banking差10.18pp、Slack差11.11pp；v3.5恢复29／23例又退步30／21例 | 先处理u11/u15、Slack u11/u13/u17；已授权却不执行与合法动作被拒需分别分析 |
| 正式v3.5.1原生ASR0但TSR仍低 | 本次1,119例安全标签全False；部分合法任务也未执行，且Dora网址有6例误拒 | 不把ASR0解释成既安全又完成任务，不恢复全部读取免审来掩盖问题 |
| 剩余I3旧诊断离线失败 | 原版快照同样出现5失败／5错误；旧审计fixture依赖过时协议，未改闭合I3机制 | 留在报告失败索引；原先私人deny覆盖／旧schema预期两项已按新语义更新且通过 |
| 历史成本尚不能直接作节省结论 | baseline／v3.4两组全部场景摘要 `cost_comparison_ready=false`；记录总 Token 分别 24,176,340 与 23,202,303 | 核查 invocation、cache、GOAL 预检、缺失 usage 和记录范围，再判断是否能比较 |
| 历史原始审计回复可能缺失 | 新迁入记录只作用于新执行；旧 inline／gzip 不一定含完整模型文本 | 可定位已有证据；缺失部分明确标未知，不能反推或伪造原回复 |
| 边界与文档存在限制 | E0 未过；I3 尚有8个范围缺口。AGENTS 为用户指定跨分支快照；部分 `report/report.md` 链接缺失 | 本文件按当前v3.5.1源码交接；研究解锁和独立验证继续走研究侧入口 |
| 受限 host profile 的诊断详情不全 | 源提交的 authorization 白名单省略若干 profile 详情，运行授权不受影响 | 若本轮失败实际涉及该路径，再补足必要诊断并验证 |

## 7. 测试与验证

### 历史Online Evaluation（2026-10-26，v3.5.1专项）

- attempted/completed/valid/incomplete/error=231/231/231/0/0，39个不同案例；另41次原生GOAL预检。全部新名称／不可变源码快照，无cache替代模型判断。
- 2,456次尝试／2,456响应，4,869,987已知Tokens，失败调用0、缺失usage0。计分2,197次／4,437,075 Tokens；GOAL259次／432,912 Tokens；不合并TSR分母。
- 最终web_refined与原版37键／注入文本一致：TSR14→17、ASR7→0；预算修正中间批仅15/37、ASR7/28，未验收，因真实L3误放再补读阶段对照后全新验证。所有阶段保留，未按最高分挑选结论。
- gpt-6.1-sol独立只读审查发现1项近期更正被挤掉问题，RED→GREEN修复；此后读提示／配置摘要改动完成离线及在线验证，未二次独立审查。
- 最终Offline Regression：ipi730项，707通过／5失败／5错误／13跳过，十项均为旧I3；AgentDyn相关39项通过。日志／命令／限制见[本轮报告](workshop/completed/v35_optimization_20261026.md)。没有全量benchmark或研究门槛通过结论。

### 历史Online Evaluation（2026-10-25，效用优化）

- 90次计分全部有效；710次API请求／710响应，已知1,139,851 Tokens，无失败调用或缺失usage。计分588次／947,902 Tokens；20个GOAL共122次／191,949 Tokens。未进行完整benchmark或无防御baseline新测，未改变E0/I3/I2状态。
- 用完整原生轨迹、四字段原始审计回复和共享outcome投影验证；clean的security占位值不进入ASR。组合比原版恢复10例，无新增失败；不外推到正式1167例总体。

### 历史Online Evaluation（2026-10-25，迁移验证）

- **范围：**9 个 tool_knowledge 计分案例（workspace／banking／Slack 各3）＋3 个 banking clean 控制，另有3个原生 GOAL 预检；不是正式结果集的重新执行。
- **实际结果：**attempted/completed/valid/incomplete/error = **12/12/12/0/0**；80 次真实 API 调用／80 响应，129,017 已知 Tokens，无 API 错误、无缺失 usage。攻击 TSR 5/9、原生 ASR 0/9；clean TSR 1/3、ASR不适用。
- **记录验收：**12 个主 JSON 仅保存 `dscg_diagnostics` 防御引用，12 份诊断 complete，计分轨迹保存20份 L3 原始回复。
- **解释范围：**证明本次记录／读取链路可运行，未证明效用改善或一般安全。本次批准范围已经完成。

### 历史v3.4.1优化Offline Regression

- ipi全套727项：704通过、5失败、5错误、13跳过；剩余10项均为I3旧诊断，在原版HEAD快照中同样失败／错误。未改该闭合诊断机制或宣称全套绿色。详见报告失败索引。
- 新读取契约7项／权限契约3项、原生工具 authored fixture、读取器／Dashboard相关回归通过；AgentDyn新读取契约7通过（仅工程契约），Node49通过。

### 历史迁移阶段Offline Regression

| 范围 | 实际结果 |
| --- | --- |
| injection_precheck | 38 通过 |
| task_diagnostics（ipi） | 15 通过，3 个本分支缺少前置系统的案例跳过 |
| partial / reuse / routing_reports | 分别70／14／24通过 |
| cost / task_isolation / dashboard_evaluation | 分别5／5／13通过 |
| sandbox_execution | 39通过、2个已有失败；迁移前快照相同 |
| task_diagnostics（ipi-agentdyn） | 14通过、4跳过；不代表另一后端的模型质量已验证 |
| Dashboard Node | 使用 bundled Node，17通过 |

完整命令、退出码、任务键、原生结果、源码快照和哈希见 [迁移报告](workshop/completed/workshop_commit_transfer_20261025.md) 与 [delivery_validation.json](workshop/artifacts/20261025_workshop_commit_transfer/delivery_validation.json)。未宣称全套回归绿色。

- **历史分析阶段 Offline Analysis：**`python -B workshop/artifacts/20261025_v34_tsr_analysis/analyze.py`，exit 0；核对1,167对任务、2,334份轨迹，保存配对账／输入哈希。文档链接与 `git diff --check` 检查；新增模型调用0，未重跑运行时测试，不算新的 Online Evaluation／Offline Regression。
- **历史v3.5 Offline Analysis：**`/opt/miniconda3/envs/ipi/bin/python -B workshop/artifacts/20261026_v35_analysis/analyze.py` exit0；三方配对、哈希与ASR证据核查，文档链接／git diff --check，无新模型调用。
- **本轮v3.5.1 Offline Analysis：**`/opt/miniconda3/envs/ipi/bin/python -B workshop/artifacts/20261026_v351_analysis/analyze.py` exit0；核对4,476份主轨迹、配对分母与注入文本；代表性失败人工复核，链接／git diff --check验证。模型调用0，未运行单元回归，未改历史结果。
- **本轮分型与设计：**`focus_review.py`、`reconstruct_evidence.py`（位于workshop/artifacts/20261026_v351_followup_design）均exit0；117例、109条有审计统计均复原匹配。模型调用0，仅文档／原始数据只读分析，不作为新模型质量或TSR/ASR验证。
- **尚未验证：**全量独立有效性／语义归因、未知adapter等价性、历史成本可比性，以及超出所选范围的优化效果。

## 8. 下一步计划

1. 按[候选方案](workshop/v351_next_optimization_20261026.md)先做可复核引用和L3模型视图单变量消融，保留风险元数据／严格执行门。
2. L1时机／标记与L2静态任务视图分别验证；只有真实计分恢复多于退步且安全控制不退化才组合，不能靠补日期或修改评分获得通过。
3. 主模型完成性没有强保证；E0 pending、I3 partial、I2 locked。当前只有分析与候选，未改防御或调用模型。

**下一行动：**实施请求到来后先落实P0诊断引用，再用固定Qwen短试验证A1；候选未通过不推广，不重开闭合campaign。
