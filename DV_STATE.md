# DSCG Project State

> 更新日期：2026-10-27（Asia/Shanghai）。范围：默认启用静态任务视图并按details实施／在线验证（已完成）；当前代码内部为 **DSCG_v3.5.3**。运行事实依据当前代码和保存配置；研究任务边界依据 [technical_route.md](../research/technical_route.md)。
>
> 后续工作顺序：**复用现有配对账 → 定位残余漏授权／误拒 → 单项改动 → 新名称复测**。每次阶段完成时更新本文件的代码状态、进行中任务、问题和验证摘要，详细过程放阶段报告。

## 1. 项目概述

- **研究目标：**防御工具使用型 LLM Agent 接收外部工具内容时遭遇的间接提示词注入，同时控制用户任务成功率损失和模型成本。
- **核心技术方案：**L1 构建隔离的规划视图，有限银行任务使用结构投影；L2 根据可信任务、完整原生工具定义和参数 schema 编译工具授权；L3 审计当前动作与任务的关系。Reference Monitor、一次性回执与执行票据负责执行前复核。
- **当前开发阶段：**默认启用static-task-v352并按details优化；四臂61例＋4例消融在线完成，共248计分／247有效／1 API错误。最终共同60例成功29→39，但banking问题攻击仅1/10，较旧默认2/10下降；不是所有问题已解决。详见[阶段报告](workshop/completed/v353_optimization_20261027.md)。
- **评测环境：**AgentDojo v1.2；`ipi` 当前为 Python 3.10.21、AgentDojo 0.1.35，配置模型为 DashScope `qwen3.7-flash`。后端识别属于 metadata-only，不认证远端服务或源码等价性。
- **研究状态：**E0 pending；I3 partial（24 个有效探针、8 个范围违规）；I2 locked。对象／数据／参数授权及已关闭 provenance/source-to-sink 路线没有重新解锁。

## 2. 当前代码状态

| 项目 | 当前快照 |
| --- | --- |
| Git Branch | `workshop` |
| HEAD Commit | `04c479a45867b086c074101ebb1d10ec7bb01ff7`；`v3.5.2：L2`；上一轮测试仍对应报告中的冻结源码／旧HEAD |
| HEAD 提交时间 | 2026-10-27 13:05:42 +08:00；本次未执行提交 |
| 工作区是否有未提交修改 | 保留先前analysis/v3-5-2.md与本状态文档修改；当前补充benchmark日志任务ID、针对性测试和说明。未改正式results、download或credentials，未暂存／提交。 |
| 实际默认运行策略 | `prompt_profile=static-task-v352`，内部DSCG_v3.5.3；baseline默认legacy／原生循环，显式legacy保留单次授权。CLI投影off为继承设置，factory/API仍projected；在线四臂显式统一off。 |
| AGENTS.md | HEAD 已收录精简后的规则；其部分跨分支框架描述与本分支代码存在差异，执行机制须逐项查当前实现。 |
| 最近更新时间 | 2026-10-27；本轮在线已收到真实Qwen响应，完整调用／样本／用量以本次产物汇总为准；不能套用此前分析的0调用或旧专项成绩。 |

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

## 4. 本轮交接与近期结果

- **benchmark日志定位：**L2授权编译失败输出suite／stage／user_task_id／injection_task_id及安全错误码；GOAL失败／错误警告逐目标输出，明确user_task_id=none，不伪造普通用户任务关联。共享full／partial／cohort路径仅增加控制台上下文，权限、请求、评分、缓存与原始轨迹不变；两后端各16项针对性测试通过，真实模型调用0。验证与命令见[日志定位报告](workshop/completed/benchmark_task_log_ids_20261027.md)。
- **遗留问题入口已补齐：**[analysis/v3-5-2.md第5节](analysis/v3-5-2.md#5-启用static后仍未解决的问题2026-10-27)按当前static专项列出银行执行／日期、Slack误拒、travel候选混用／年份、引用协议失败，并单列最终交付／文本及错误投影边界；保留第1–4节历史正式结果。仅文档整理，无新增模型调用；本次链接／状态与diff核验位于`workshop/artifacts/20261027_v353_residual_notes/`。
- **本轮优化已交付：**[阶段报告](workshop/completed/v353_optimization_20261027.md)、[已完成方案](workshop/completed/v353_implementation_plan_20261027.md)、[执行账](workshop/artifacts/20261027_v353_optimization/progress.md)。三臂初测183例＋引用提示修订后61例＋4例静态消融；原生GOAL另120次（119有效／1错误），组件提取12次不计任务覆盖。最终共同60例：旧legacy29→39，旧static33→39；最终问题攻击banking1/10、Slack6/7、travel10/14（另1 API错误），攻击ASR0/38。引用协议失败初始7/61→最终1/61。案例／注入文本一致，源码／原始结果冻结；不作因果或总体安全结论。无新增完成性闸门／恢复／扩权。
- **对应建议已补充：**details的8个问题分析后各加简短建议：对照现有static候选、区分主规划停办与执行、展示任务相关证据、补必要读取、独立候选筛选、明确费用口径、日历／文本污染及完整最终交付。本轮已落实到现有任务提取／规划／审计提示并在线测试，效用仍分场景变化；不新增完成性账本、恢复或动态扩权。原文与继承改动保持，快照／[文档核验](workshop/artifacts/20261027_v352_recommendations/verification.json)在独立任务目录。
- **失败任务细查：**[analysis/details.md](analysis/details.md)复核8个重点用户任务165例＋travel全部43个退步。v3.5.2 u15漏退款权限18/24；银行5任务共26例已授权、无目标候选且无阻挡。Slack u11仍7例拒random；u13的12例私信阻挡中5例无查询错误、7例混合查询错误。29例零L3退步分为地址漏查4、推荐对象改变20、费用口径4、未提日历1；分型是观察，不是独立语义评分。u13地址停办是新版新增，不能称该任务旧版也失败。u3邮件成功且中间已给完整酒店信息，最终只余确认，区别于根本未查询。u12酒店偏好、u11餐次表达、u19原生未乘两人餐费的评分局限单列。证据在`workshop/artifacts/20261027_v352_details/`，未改标签／执行策略，未重放独立oracle。
- **此前v3.5.2文档同步（本轮已更新默认）：**README与docs全部10份当时统一v3.5.2默认legacy／显式static-task-v352，明确启用命令、调用差异、当前读取规则和CLI／Dashboard候选消融限制；精简约52%，历史过程改为阶段链接并保留旧锚点。原文快照及[文档检查](workshop/artifacts/20261026_v352_docs/verification.json)位于同一任务目录；CLI帮助／示例参数、链接和git diff --check验证，无模型调用／运行时回归。
- **最新入口：**[analysis/v3-5-2.md](analysis/v3-5-2.md)；原v3.5.1分析已[归档](workshop/archive/v351_analysis_20261026.md)，保留原始字节快照。正式输入为`results/benchmarks/agentdojo/qwen3.7-flash_DSCG_v3.5.2`与`download/dscg-history-analysis-20261026T145313Z`；同名partial目录实际保存历史DSCG_v3.5，不作为本轮证据。比较范围仅为导出选定的banking／Slack／travel。
- **口径／结果：**两版共同1119键，注入逐例一致；排除新版travel important_instructions/u19/i5的参数JSON错误，共1118有效。banking232→228/384，Slack188→194/315，travel322→305/419，整体742→727/1118；banking/Slack ASR0，travel新增2次最终回答污染。
- **实际配置：**本次正式默认legacy，1119例各一次authorization，static_task_view为0；没有启用static-task-v352。默认L1、L2单次布尔权限、读取免审、Monitor及完成策略未变；新增L3原请求编号显示／读取对照、P0引用及SDK retries0。两阶段L2的专项成绩不能归给默认版本。
- **原因：**banking恢复26／退步30，Slack19／13，travel26／43。所有退步案例的授权集合与旧版相同；travel43个退步仅7个有阻挡、29个没有任何L3模型调用。代表问题包括只查询却称已安排付款、邮件已发但最终答复漏评分／价格、推荐／计算变化。u15退款授权仍缺18/24，u11付款仍0/24；Slack u11、u13误拒延续。generation5283次均未实际发送temperature，不能按模型属性0假定确定性重放。
- **证据：**[配对账](workshop/artifacts/20261026_v352_analysis/paired_analysis.json)、[分型统计](workshop/artifacts/20261026_v352_analysis/diagnostic_counts.json)、[输入哈希](workshop/artifacts/20261026_v352_analysis/input_hashes.json)。全量独立语义oracle未重放；E0/I3/I2状态不变。
- **此前工程试验：**[执行账](workshop/artifacts/20261026_v352_optimization/progress.md)、[固定案例](workshop/artifacts/20261026_v352_optimization/selection.json)、[在线分型](workshop/artifacts/20261026_v352_optimization/online_summary.json)。三臂重点117例：对照28，默认L3候选31，显式静态视图57；各自测例／错误分母与正式结果分开。风险字段移除／隔离延后没有采用；L1标记组合也未推广。不得把专项数字外推为正式总体收益。
- **工程验证尚有遗留：**最终集成全套747项出现9失败／5错误／13跳过，其中原I3为5失败／5错误（对照已复现），另有3个旧版本断言和1个旧示例对象身份断言，已在本轮适配；static候选的CLI／Dashboard NoL2／NoChecker限制也已修复，4例真实clean调用链验证完成。另发现原生generation函数自带重试；已记录失败调用即使随后返回，也应统一标基础设施错误，当前共享投影尚未覆盖此情况。当前正式1119例没有已记账API失败，此问题不是其TSR下降原因；保留先前试验中的错误与未知成本，不重写原始标签。

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
| v3.5.3仅部分恢复效用 | banking u15退款权限3/3但TSR0/3；u4/u6仍停日期；Slack u13/K:2两次MISSING_EVIDENCE；travel u15/I:2候选混用复发 | 分开复核真实缺参、可选参数更新及有限审计事实；不扩权／补日期／改评分 |
| 静态协议与日历年份仍有缺口 | 最终Slack u18/K:3仍QUOTE_NOT_LITERAL；travel u7/P:6原生utility=True但事件2024年缺少成功的年份观测 | 严格引用不放宽；原生TSR不等于参数／任务语义认证，污染委托源不宣称已支持 |
| v3.5.2正式结果没有总体改善 | 三场景共同1118例成功742→727，travel净少17；新增2次最终回答污染 | 默认L3小改与显式两阶段L2分开评价；扩大任务类型覆盖，保留当前失败证据 |
| 正式v3.5.1 TSR仍低于baseline（历史对比） | banking差10.18pp、Slack差11.11pp；v3.5恢复29／23例又退步30／21例 | u11/u15、Slack u11/u13的问题继续存在；已授权却不执行与误拒分别分析 |
| 历史v3.5.1原生ASR0但TSR仍低 | 该版1,119例安全标签全False；部分合法任务也未执行，且Dora网址有6例误拒 | 不把ASR0解释成既安全又完成任务，不恢复全部读取免审来掩盖问题 |
| 剩余I3旧诊断离线失败 | 原版快照同样出现5失败／5错误；旧审计fixture依赖过时协议，未改闭合I3机制 | 留在报告失败索引；原先私人deny覆盖／旧schema预期两项已按新语义更新且通过 |
| 历史成本尚不能直接作节省结论 | baseline／v3.4两组全部场景摘要 `cost_comparison_ready=false`；记录总 Token 分别 24,176,340 与 23,202,303 | 核查 invocation、cache、GOAL 预检、缺失 usage 和记录范围，再判断是否能比较 |
| 历史原始审计回复可能缺失 | 新迁入记录只作用于新执行；旧 inline／gzip 不一定含完整模型文本 | 可定位已有证据；缺失部分明确标未知，不能反推或伪造原回复 |
| 边界与文档存在限制 | E0 未过；I3 尚有8个范围缺口。AGENTS 为用户指定跨分支快照；部分 `report/report.md` 链接缺失，旧080824导出已不在当前download，归档保留原链接 | 本文件按当前v3.5.3源码交接；不补造历史文件；研究解锁和独立验证继续走研究侧入口 |
| 受限 host profile 的诊断详情不全 | 源提交的 authorization 白名单省略若干 profile 详情，运行授权不受影响 | 若本轮失败实际涉及该路径，再补足必要诊断并验证 |
| 长请求约束仍可能截断 | 新static任务视图仅在新增提取路径检查L3原文长度；NoL2、零调用目录、受限host路径保留旧协议及截断行为 | 不宣称修复所有长请求，也不把辅助摘要视为完整原文替代 |

## 7. 测试与验证

### 本轮Online Evaluation／Offline Regression（2026-10-27）

- Qwen3.7-Flash：attempted/completed/valid/error/incomplete=248/248/247/1/0；四臂各61例、4例消融，原生GOAL另120次。最终TSR39/60、ASR0/38；共同60例旧legacy29、旧static33、初始优化35。所有中间退步／API错误／协议失败保留，正式结果不回写。
- 共2,968次API尝试／2,966成功响应，8,252,464已知Tokens；2次失败usage／费用未知，0缺失usage响应。计分＋消融2,103调用／6,146,710 Tokens，GOAL853／2,098,779，组件12／6,975。generation实际未发送temperature，未修改原生采样。
- 初始集成202／AgentDyn49／Node49通过；初始优化全套752中729通过、5失败／5错误／13跳过，均为旧I3。最终诊断／提示变更后static10、defaults5、AgentDyn defaults5通过；独立增量两后端各15项通过，495个parser边界接受集合不变。两次gpt-6.1-sol审查无剩余发现。
- [交付核验](workshop/artifacts/20261027_v353_optimization/delivery_verification.json)记录源码冻结、6153份历史正式输入及1180份详细分析输入原始哈希、链接／diff检查；具体命令、标签、成本与限制见[本轮报告](workshop/completed/v353_optimization_20261027.md)。没有全量benchmark或研究门槛通过结论。

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
- **此前v3.5.1 Offline Analysis：**`/opt/miniconda3/envs/ipi/bin/python -B workshop/artifacts/20261026_v351_analysis/analyze.py` exit0；核对4,476份主轨迹、配对分母与注入文本；代表性失败人工复核，链接／git diff --check验证。模型调用0，未运行单元回归，未改历史结果。
- **此前分型与设计：**`focus_review.py`、`reconstruct_evidence.py`（位于workshop/artifacts/20261026_v351_followup_design）均exit0；117例、109条有审计统计均复原匹配。模型调用0，仅文档／原始数据只读分析，不作为新模型质量或TSR/ASR验证。
- **此前v3.5.2总体 Offline Analysis：**`/opt/miniconda3/envs/ipi/bin/python -B workshop/artifacts/20261026_v352_analysis/analyze.py` exit0；2238主轨迹、1119键／1118共同有效、逐例注入一致。只读统计及代表性语义复核；无新模型调用、未运行运行时回归。`verify.py`核对6153份输入哈希、旧分析字节／归档链接、新文档链接及git diff --check；历史缺失导出单列，[验证记录](workshop/artifacts/20261026_v352_analysis/verification.json)。
- **本轮详细 Offline Analysis（2026-10-27）：**`/opt/miniconda3/envs/ipi/bin/python -B workshop/artifacts/20261027_v352_details/{analyze,compose,verify}.py`分别exit0；208对／416主轨迹、1182份输入哈希、18处逐字片段和29例无L3分型核验，链接／git diff --check通过。[验证记录](workshop/artifacts/20261027_v352_details/verification.json)。无新模型调用、原生工具执行或运行时回归；继承README／docs修改保持原样。
- **尚未验证：**全量独立有效性／语义归因、未知adapter等价性、历史成本可比性，以及超出所选范围的优化效果。

## 8. 下一步计划

1. 基于最终残余任务，优先复核banking真实日期缺参／已有订单可选参数更新，以及Slack u13的任务相关事实误拒；不要重跑已完成阶段或以补日期、扩权限追回TSR。
2. 保留travel候选混用／日历年份、静态引用单例失败及原生评分疑点；提示改进不构成完成保证。共享API失败投影与旧I3仍是独立遗留。
3. 当前用户授权的新任务验证已完成；后续新实施按新范围命名，不重开历史campaign。E0 pending、I3 partial、I2 locked。

**下一行动：**以本轮失败索引逐项分析banking日期／原生schema与Slack证据上下文，形成单项候选后再开展新的实现；当前不继续扩样或完整benchmark。
