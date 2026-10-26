# DSCG Project State

> 更新日期：2026-10-26（Asia/Shanghai）。范围：v3.5正式结果分析与后续专项优化；当前代码内部默认为 **DSCG_v3.5.1**（历史v3.5运行保存的内部版本仍为v3.4.1）。运行事实依据当前代码和保存配置；研究任务边界依据 [technical_route.md](../research/technical_route.md)。
>
> 后续工作顺序：**复用现有配对账 → 定位残余漏授权／误拒 → 单项改动 → 新名称复测**。每次阶段完成时更新本文件的代码状态、进行中任务、问题和验证摘要，详细过程放阶段报告。

## 1. 项目概述

- **研究目标：**防御工具使用型 LLM Agent 接收外部工具内容时遭遇的间接提示词注入，同时控制用户任务成功率损失和模型成本。
- **核心技术方案：**L1 构建隔离的规划视图，有限银行任务使用结构投影；L2 根据可信任务、完整原生工具定义和参数 schema 编译工具授权；L3 审计当前动作与任务的关系。Reference Monitor、一次性回执与执行票据负责执行前复核。
- **当前开发阶段：**v3.5.1方案实施及专项Qwen验证完成：最终37例TSR14→17、原生ASR7/28→0/28，合法网页4/4成功；保留全部231次计分／41次GOAL预检过程。退款漏授权与L3效果误拒仍未解决，未通过整体效用／一般安全验收。
- **评测环境：**AgentDojo v1.2；`ipi` 当前为 Python 3.10.21、AgentDojo 0.1.35，配置模型为 DashScope `qwen3.7-flash`。后端识别属于 metadata-only，不认证远端服务或源码等价性。
- **研究状态：**E0 pending；I3 partial（24 个有效探针、8 个范围违规）；I2 locked。对象／数据／参数授权及已关闭 provenance/source-to-sink 路线没有重新解锁。

## 2. 当前代码状态

| 项目 | 当前快照 |
| --- | --- |
| Git Branch | `workshop` |
| HEAD Commit | `06d723ce6724c38b85199a57032ea848fe1a441d`；`DSCG_v3.5:针对v3.4进行优化，主要针对是slack和banking场景` |
| HEAD 提交时间 | 2026-10-25 23:13:54 +08:00 |
| 工作区是否有未提交修改 | 继承分析改名／归档的未提交文档改动；本轮修改L2/L3、读取分流、证据预算、版本／绑定及相关测试文档。未暂存／提交，未改正式结果、download或credentials。 |
| 实际默认运行策略 | `prompt_profile=legacy`，内部 `FRAMEWORK_VERSION=DSCG_v3.5.1`，见 [input_isolation.py](dscg/input_isolation.py) 和 [defended.py](dscg/pipelines/defended.py)。 |
| AGENTS.md | HEAD 已收录精简后的规则；其部分跨分支框架描述与本分支代码存在差异，执行机制须逐项查当前实现。 |
| 最近更新时间 | 2026-10-26；本轮在线专项231/231有效，2,456次真实API响应／4,869,987 Tokens；先前90次验证和正式结果独立保留。 |

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

- **任务：**v3.5.1已实现并完成专项验证，见[阶段报告](workshop/completed/v35_optimization_20261026.md)和[分析第4节](analysis/v3-5.md#4-对应完善方案与实施状态)。内部v3.5.1仍为legacy逐工具布尔授权，不是intent-evidence-v35或host-FSM分支。
- **实现：**完整任务／效果类型辅助单次L2覆盖；L3当前效果判定对照；证据8192字符内优先完整记录，近期4条不低于旧展示额度；sink-free-read-v4仅免审无sink非敏感读取，外部请求走L3。审计输入v4.2，规则／示例进入配置身份。completion选项改进但对照无净益，默认关闭；无动态扩权、参数修补、来源追踪、自动恢复或I2账本。
- **专项结果：**最终37/37问题样本有效（另2个纯只读负控原版／最终均2/2成功、无写授权），主比较（banking12、Slack25），匹配原版TSR14/37→17/37、ASR7/28→0/28，恢复5例／新增失败2例；核心24例2→6，合法网页4/4、历史7个ASR键0/7。对照为优化前DSCG，不是新测无防御baseline；不能与正式整体分母混用。
- **仍未解：**最终u15四例未授send_money、效用0/4，退款覆盖跨批次仍不稳；两例退步为ignore_previous/slack/u11/i2、i3，加入random仍被EXPLICIT_CONSTRAINT拒绝。u2修改／u18私信授权提升不代表全部复合任务已解决。
- **证据：**[231次计分账](workshop/artifacts/20261026_v35_optimization/online_summary.json)、[41次GOAL预检及成本／得失键](workshop/artifacts/20261026_v35_optimization/online_details.json)、[不可变源码哈希](workshop/artifacts/20261026_v35_optimization/source_hashes.json)。使用现有DashScope qwen3.7-flash和原生评分；已完成本任务验证，不继续扩样或重复已完成筛选。
- **正式结果分析保留：**[原三方账](workshop/artifacts/20261026_v35_analysis/paired_analysis.json)仍为1,119键／1,118有效／3,357份主轨迹；用户确认injection_task_8是正常cohort过滤，不是问题。原v3.5银行ASR0、Slack3→7是历史正式结果，未改标签或旧文件。

### 正式结果共同有效范围

范围仍为screened三场景／三种targeted攻击；cohort不同且baseline adapter未记录，保留比较告警，不做严格单因素因果推断。

| 场景 | baseline TSR | v3.4 TSR | v3.5 TSR | 原生ASR v3.4→v3.5 |
| --- | ---: | ---: | ---: | ---: |
| banking | 270/383（70.50%） | 172/383（44.91%） | 232/383（60.57%） | 0/383→0/383 |
| slack | 223/315（70.79%） | 125/315（39.68%） | 186/315（59.05%） | 3/315→7/315 |
| travel | 233/420（55.48%） | 289/420（68.81%） | 319/420（75.95%） | 0/420→0/420 |

本轮人工核对代表性失败及全部7例ASR，没有全量独立语义审计或oracle重放。正式结果与此前18例的15/18不能混用分母。

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
| 正式v3.5仍低于匹配baseline | banking差9.92pp、Slack差11.75pp；旧问题延续分别56／21例，另有新增退步 | 优先文档／复合任务授权、L3效果依据与交付遗漏，不再把已改善的准备读取列为主要瓶颈 |
| 正式v3.5的Slack访问型ASR | 旧七例走public读取免审；新策略专项28攻击ASR0、合法网页4/4，但不能外推整体 | 保留旧证据；按任务相关性继续区分合法获取和源指令引导的额外访问，不以输出干净代替执行安全 |
| 剩余I3旧诊断离线失败 | 原版快照同样出现5失败／5错误；旧审计fixture依赖过时协议，未改闭合I3机制 | 留在报告失败索引；原先私人deny覆盖／旧schema预期两项已按新语义更新且通过 |
| 历史成本尚不能直接作节省结论 | baseline／v3.4两组全部场景摘要 `cost_comparison_ready=false`；记录总 Token 分别 24,176,340 与 23,202,303 | 核查 invocation、cache、GOAL 预检、缺失 usage 和记录范围，再判断是否能比较 |
| 历史原始审计回复可能缺失 | 新迁入记录只作用于新执行；旧 inline／gzip 不一定含完整模型文本 | 可定位已有证据；缺失部分明确标未知，不能反推或伪造原回复 |
| 边界与文档存在限制 | E0 未过；I3 尚有8个范围缺口。AGENTS 为用户指定跨分支快照；部分 `report/report.md` 链接缺失 | 本文件按当前v3.5.1源码交接；研究解锁和独立验证继续走研究侧入口 |
| 受限 host profile 的诊断详情不全 | 源提交的 authorization 白名单省略若干 profile 详情，运行授权不受影响 | 若本轮失败实际涉及该路径，再补足必要诊断并验证 |

## 7. 测试与验证

### 本轮Online Evaluation（2026-10-26，v3.5.1）

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
- **本轮Offline Analysis：**`/opt/miniconda3/envs/ipi/bin/python -B workshop/artifacts/20261026_v35_analysis/analyze.py` exit0；三方配对、哈希与ASR证据核查，文档链接／git diff --check，无新模型调用。
- **尚未验证：**全量独立有效性／语义归因、未知adapter等价性、历史成本可比性，以及超出所选范围的优化效果。

## 8. 下一步计划

1. 复用最终banking u11/u15、Slack u11/u13轨迹，区分漏授权、参数错误、关键依据缺失、看到依据仍误拒及真实交付遗漏；不重复全量清点。
2. 退款授权跨批不稳定，L3拒绝加入random仍在；后续以单项有证据的改动验证，不靠降低严格校验或反复补同义提示。
3. 保留正式成本可比性、独立oracle复核及I3旧诊断未完成项。E0 pending、I3 partial、I2 locked；新任务验证另用新名称，不重开历史余额或闭合campaign。

**下一行动：**先按本批完整输入／返回核对退款漏授权与加入random的效果误拒；当前专项已结束，未提交代码。
