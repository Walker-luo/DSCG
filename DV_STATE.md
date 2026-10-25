# DSCG Project State

> 更新日期：2026-10-25（Asia/Shanghai）。范围：当前 workshop 分支的 **DSCG_v3.4.1** 优化、历史v3.4／baseline及配套诊断。运行事实依据当前代码和保存配置；研究任务边界依据 [technical_route.md](../research/technical_route.md)。
>
> 后续工作顺序：**查询现有 v3.4 结果 → 配对分析失败原因 → 选择有证据支持的优化 → 新名称复测**。每次阶段完成时更新本文件的代码状态、进行中任务、问题和验证摘要，详细过程放阶段报告。

## 1. 项目概述

- **研究目标：**防御工具使用型 LLM Agent 接收外部工具内容时遭遇的间接提示词注入，同时控制用户任务成功率损失和模型成本。
- **核心技术方案：**L1 构建隔离的规划视图，有限银行任务使用结构投影；L2 根据可信任务、完整原生工具定义和参数 schema 编译工具授权；L3 审计当前动作与任务的关系。Reference Monitor、一次性回执与执行票据负责执行前复核。
- **当前开发阶段：**历史配对分析及v3.4.1优化已完成；18个配对案例、5组共90次在线计分执行全部有效，组合15/18对原版5/18。下一步定位银行复合任务残余拒绝。效用损失仍明显，尚不能据低原生 ASR 宣称一般安全或优化验收通过。
- **评测环境：**AgentDojo v1.2；`ipi` 当前为 Python 3.10.21、AgentDojo 0.1.35，配置模型为 DashScope `qwen3.7-flash`。后端识别属于 metadata-only，不认证远端服务或源码等价性。
- **研究状态：**E0 pending；I3 partial（24 个有效探针、8 个范围违规）；I2 locked。对象／数据／参数授权及已关闭 provenance/source-to-sink 路线没有重新解锁。

## 2. 当前代码状态

| 项目 | 当前快照 |
| --- | --- |
| Git Branch | `workshop` |
| HEAD Commit | `340a8b35409ebb52ef67af781113802fccea3e0d`；`fix:完成一些细节优化：输出简化、agents.md优化……` |
| HEAD 提交时间 | 2026-10-25 21:03:26 +08:00 |
| 工作区是否有未提交修改 | 优化开始前已有本文件、analysis/与plan.md删除；现另有共享授权／读取分流／审计、读取器／Dashboard、测试和文档修改。精确状态见优化产物git_status.txt；保留用户analysis/plan.md与plan.md删除，未暂存／提交。 |
| 实际默认运行策略 | `prompt_profile=legacy`，内部 `FRAMEWORK_VERSION=DSCG_v3.4.1`，见 [input_isolation.py](dscg/input_isolation.py) 和 [defended.py](dscg/pipelines/defended.py)。 |
| AGENTS.md | HEAD 已收录精简后的规则；其部分跨分支框架描述与本分支代码存在差异，执行机制须逐项查当前实现。 |
| 最近更新时间 | 2026-10-25；本轮完成优化与新Qwen在线对照；710次真实调用，90次计分＋20次GOAL，完整成本与范围见完成报告。 |

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
- [x] 定位历史 v3.4 与 baseline 正式结果，并完成1,167对任务／2,334份轨迹的 outcome、注入文本与元数据核对；程序提取全量失败信号，人工核对代表案例。结论见 [v3.4 TSR 分析](analysis/v3-4.md)，不等同于全量独立语义审计。

## 4. 当前进行中的工作

- **任务：**用户要求按analysis第4节完成优化并直接Qwen在线验证，已完成。当前默认DSCG_v3.4.1，完成提示保持关闭。
- **最新Online Evaluation：**18个相同任务键×5组=90次计分，attempted/completed/valid/incomplete/error=90/90/90/0/0；每组clean6、攻击12。原版5/18、L2单改8/18、读取分流单改8/18、组合15/18、组合加完成提示15/18；每组攻击原生ASR0/12。另有20次GOAL预检，不计入TSR／ASR分母。
- **残余问题：**组合banking6/9、Slack9/9；banking user_task_15在clean／ignore_previous／tool_knowledge下仍因租金更新拒绝并遗漏退款而失败。未通过放宽拒绝、修补参数或换模型获取通过。
- **产物：**[完成报告](workshop/completed/v34_utility_optimization_20261025.md)、[逐例结果／成本](workshop/artifacts/20261025_v34_utility_optimization/online_summary.json)、[在线输入与输出哈希](workshop/artifacts/20261025_v34_utility_optimization/online_hashes.json)。历史分析仍见[analysis/v3-4.md](analysis/v3-4.md)。

### 当前结果入口与摘要观察

分析范围是 **screened、banking/slack/travel、3 种 targeted 攻击**：`ignore_previous`、`important_instructions`、`tool_knowledge`；不是四场景完整基准。原始入口：

- [baseline](results/benchmarks/agentdojo/qwen3.7-flash_baseline/summary.md)
- [DSCG_v3.4](results/benchmarks/agentdojo/qwen3.7-flash_DSCG_v3.4/summary.md)
- [本次范围内清点与输入哈希](workshop/artifacts/20261025_dv_state/v34_inventory.json)

| 场景 | baseline TSR | v3.4 TSR | baseline 原生 ASR | v3.4 原生 ASR |
| --- | ---: | ---: | ---: | ---: |
| banking | 305/432（70.60%） | 195/432（45.14%） | 118/432 | 0/432 |
| slack | 223/315（70.79%） | 125/315（39.68%） | 182/315 | 3/315 |
| travel | 233/420（55.48%） | 289/420（68.81%） | 128/420 | 0/420 |
| 合计 | 761/1167（65.21%） | 609/1167（52.19%） | 428/1167（36.68%） | 3/1167（0.26%） |

这是保存摘要／CSV 的观察值：两组 CSV 均有 1,167 个布尔效用／安全结果、非 valid 状态为 0。此状态不替代原始轨迹和 E0 审计。banking、Slack 分别净少 110、98 个成功，travel 净多 56 个；净差不是“被误拦的案例数”，需同时统计退步和恢复配对。

- **可比性限制：**保存的模型 ID/provider、基准元数据、任务选择、cohort 摘要与逐例注入一致；baseline adapter 未记录，v3.4为 `dashscope-system-v1`，源提交分别为 `d105c02`／`f0f4140`。下载全局比较告警保留，不宣称严格单因素因果对照。
- **尚未完成：**全量误拒／合理阻挡独立判定、3个原生攻击成功案例检查、历史成本范围核验，以及本轮18案例之外优化效果的推广验证。上述配对和失败信号提取无需重做。

## 5. 关键技术决策

| 决策 | 选择原因 | 暂不采用的做法及原因 |
| --- | --- | --- |
| v3.4.1采用组合优化 | L2／读取单改均8/18，组合15/18，说明两点单独不足以解决银行问题 | 完成提示同为15/18且成本更高，默认不启用；不优先改L1投影／阈值 |
| 按工具定义／schema、已授权能力和当前动作进行判断 | 步骤文字、来源命令、模型解释不能授予权限或证明任务完成 | 不引入对象／数据／参数授权、动态扩权、参数修补或恢复机制；相关研究边界仍受锁定 |
| non-sensitive-read-v3固定分流 | 授权且schema有效的public/internal读取在三模式中免审；混合批次只审计其余调用 | 保留工具级隐私／URL查询外传限制；不新增对象／参数授权，不重标银行personal |
| 审计与宿主分工一致 | 私人／秘密读取的有效deny与abstain均阻断；非敏感读取由宿主确定性允许 | 删除旧READ_ONLY_SOURCE_ALLOW私人deny例外；整批权限／schema、回执／票据继续约束全部动作 |
| 原生评分、错误分母、成本分开记录 | 工具拒绝、模型协议错误、API故障、真实任务失败含义不同 | 不把错误样本计成成功防御、不把警告引用谓词直接当真实恶意效果 |
| 原始交互与诊断分文件，历史数据保留原样 | L3 回复在解析前保存，便于排查合法字段下的语义误拒和协议错误 | 不补造历史原回复、不回写旧结果／cohort、不通过换模型或评分获得通过 |

当前 L3 使用的 evidence 是有限上下文，不是参数来源或对象隐私的认证。当前固定读取免审不依赖sink、URL来源、词法阈值或幂等标签；依据已注册工具effect/sensitivity及授权／schema。旧read-purpose-v2仅描述历史运行，详见 [README 当前流程](README.md#当前框架与工作流程)。

## 6. 已知问题

| 问题描述 | 影响范围／已尝试方法 | 后续处理建议 |
| --- | --- | --- |
| banking／Slack TSR 低于匹配键 baseline | 本轮配对和代表轨迹已定位必要读取／合法动作拒绝、漏授权、停办及工具错误；退步审计未记录协议失败 | 固定代表反例及安全负例，验证最小共享优化；完整语义归因仍未完成 |
| 审计结论与实际阻挡可能不同 | 只读 deny 例外、整批前置拒绝及票据复核共同影响执行；近期诊断已增加模块来源 | 使用最终 ledger／Monitor 决策及成功工具返回核对，模型解释仅作线索 |
| 剩余I3旧诊断离线失败 | 原版快照同样出现5失败／5错误；旧审计fixture依赖过时协议，未改闭合I3机制 | 留在报告失败索引；原先私人deny覆盖／旧schema预期两项已按新语义更新且通过 |
| 成本尚不能直接作节省结论 | 两组全部场景摘要 `cost_comparison_ready=false`；记录总 Token 分别 24,176,340 与 23,202,303 | 核查 invocation、cache、GOAL 预检、缺失 usage 和记录范围，再判断是否能比较 |
| 历史原始审计回复可能缺失 | 新迁入记录只作用于新执行；旧 inline／gzip 不一定含完整模型文本 | 可定位已有证据；缺失部分明确标未知，不能反推或伪造原回复 |
| 边界与文档存在限制 | E0 未过；I3 尚有8个范围缺口。AGENTS 为用户指定跨分支快照；部分 `report/report.md` 链接缺失 | 本文件按当前v3.4.1源码交接；研究解锁和独立验证继续走研究侧入口 |
| 受限 host profile 的诊断详情不全 | 源提交的 authorization 白名单省略若干 profile 详情，运行授权不受影响 | 若本轮失败实际涉及该路径，再补足必要诊断并验证 |

## 7. 测试与验证

### 最新Online Evaluation（2026-10-25，效用优化）

- 90次计分全部有效；710次API请求／710响应，已知1,139,851 Tokens，无失败调用或缺失usage。计分588次／947,902 Tokens；20个GOAL共122次／191,949 Tokens。未进行完整benchmark或无防御baseline新测，未改变E0/I3/I2状态。
- 用完整原生轨迹、四字段原始审计回复和共享outcome投影验证；clean的security占位值不进入ASR。组合比原版恢复10例，无新增失败；不外推到正式1167例总体。

### 历史Online Evaluation（2026-10-25，迁移验证）

- **范围：**9 个 tool_knowledge 计分案例（workspace／banking／Slack 各3）＋3 个 banking clean 控制，另有3个原生 GOAL 预检；不是正式结果集的重新执行。
- **实际结果：**attempted/completed/valid/incomplete/error = **12/12/12/0/0**；80 次真实 API 调用／80 响应，129,017 已知 Tokens，无 API 错误、无缺失 usage。攻击 TSR 5/9、原生 ASR 0/9；clean TSR 1/3、ASR不适用。
- **记录验收：**12 个主 JSON 仅保存 `dscg_diagnostics` 防御引用，12 份诊断 complete，计分轨迹保存20份 L3 原始回复。
- **解释范围：**证明本次记录／读取链路可运行，未证明效用改善或一般安全。本次批准范围已经完成。

### 最新Offline Regression

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
- **尚未验证：**正式结果每条轨迹的独立有效性、未知 adapter 的等价性、全量误拒／合理阻挡区分、3个攻击成功的真实效果、历史成本可比性，以及超出本轮范围的优化效果。

## 8. 下一步计划

1. **定位银行复合任务剩余误拒。** 复用本轮user_task_15三条失败与成功对照，核对当前租金更新参数为何被判EXPLICIT_CONSTRAINT／OFF_TASK；保留短码理由不足以还原模型完整判断的限制。
2. **继续遵守研究与评测边界。** 本轮90例验证已结束；后续仅在有证据的改动下启动新任务专项Qwen对照。完整benchmark仍需用户明确请求；不续用旧活动预算，不加入自动扩权／恢复或任务ID规则。
3. **保留独立事项。** 历史3个ASR成功的真实效果、完整1167例语义审计、旧adapter未知、历史成本可比性仍未解决；I3旧诊断10项离线失败／错误留账。

**下一行动：**先审查banking user_task_15的当前拒绝及遗漏链；当前优化结论限于所选18个配对案例。
