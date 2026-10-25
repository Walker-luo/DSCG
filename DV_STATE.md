# DSCG Project State

> 更新日期：2026-10-25（Asia/Shanghai）。范围：当前 workshop 分支的 **DSCG_v3.4**、对应 baseline、配套筛选与诊断。运行事实依据当前代码和保存配置；研究任务边界依据 [technical_route.md](../research/technical_route.md)。
>
> 后续工作顺序：**查询现有 v3.4 结果 → 配对分析失败原因 → 选择有证据支持的优化 → 新名称复测**。每次阶段完成时更新本文件的代码状态、进行中任务、问题和验证摘要，详细过程放阶段报告。

## 1. 项目概述

- **研究目标：**防御工具使用型 LLM Agent 接收外部工具内容时遭遇的间接提示词注入，同时控制用户任务成功率损失和模型成本。
- **核心技术方案：**L1 构建隔离的规划视图，有限银行任务使用结构投影；L2 根据可信任务、完整原生工具定义和参数 schema 编译工具授权；L3 审计当前动作与任务的关系。Reference Monitor、一次性回执与执行票据负责执行前复核。
- **当前开发阶段：**v3.4 工程实现及筛选／诊断迁移已完成，进入现有结果的查询与失效归因阶段。效用损失仍明显，尚不能据低原生 ASR 宣称一般安全或优化验收通过。
- **评测环境：**AgentDojo v1.2；`ipi` 当前为 Python 3.10.21、AgentDojo 0.1.35，配置模型为 DashScope `qwen3.7-flash`。后端识别属于 metadata-only，不认证远端服务或源码等价性。
- **研究状态：**E0 pending；I3 partial（24 个有效探针、8 个范围违规）；I2 locked。对象／数据／参数授权及已关闭 provenance/source-to-sink 路线没有重新解锁。

## 2. 当前代码状态

| 项目 | 当前快照 |
| --- | --- |
| Git Branch | `workshop` |
| HEAD Commit | `9f9b64b6056648adde2fe53555b3b5bea459d5c5`；`fix:修改agents.md逻辑` |
| HEAD 提交时间 | 2026-10-25 18:31:18 +08:00 |
| 工作区是否有未提交修改 | 有。筛选、诊断、读取器、Dashboard、测试、文档和附件迁移均在工作树；未暂存、未提交。完整快照见 [git_status_before.txt](workshop/artifacts/20261025_dv_state/git_status_before.txt)。 |
| 实际默认运行策略 | `prompt_profile=legacy`，内部 `FRAMEWORK_VERSION=DSCG_v3.4`，见 [input_isolation.py](dscg/input_isolation.py) 和 [defended.py](dscg/pipelines/defended.py)。 |
| AGENTS.md | 已按用户要求核对为 `769e11d` 的原文，原文件即一致。其跨分支框架描述与本分支代码存在差异，执行机制须逐项查当前实现。 |
| 最近更新时间 | 2026-10-25；本次整理为文档与已有数据读取，没有新增模型调用或运行行为修改。 |

运行名不选择策略；目录名称、保存的 pipeline 名、配置身份和实际代码需分别核对。历史结果不因本次迁移改写或重新标记。

## 3. 已完成的工作

- [x] L1 来源封装与有限银行月支出投影；原始返回继续保留供审计与原生轨迹使用。
- [x] v3.4 L2 动作步骤授权：根据完整原生定义输出有界步骤，由宿主求动作工具并集并合并自动读取权限；整批权限前置检查和授权规划视图已接入。
- [x] v3.4 L3 当前动作审计：有限四字段判决、严格宿主校验和受限证据上下文；Monitor／回执／票据执行链已接入。
- [x] full、partial、cohort 和 Dashboard 使用共享工厂及评分／读取路径；原生 baseline 独立执行。
- [x] 从 `2d57bc7` 迁入单次 injection GOAL 筛选：每目标一次，成功保留，失败／错误分别处理，续跑只处理未开始目标；旧冻结名单保留原语义。
- [x] 从 `d457369` 迁入适用于当前 v3.4 的独立诊断、L3 原始回复附件、分层阻挡来源、共享读取器和续跑快照支持。
- [x] 对迁移完成 12 个真实计分案例的记录链路验证；结果、调用量和限制见 [迁移报告](workshop/completed/workshop_commit_transfer_20261025.md)。
- [x] 定位当前 v3.4 与 baseline 正式结果，读取摘要／CSV 并核对 1,167 个任务键及 cohort 摘要；尚未逐轨迹审计。

## 4. 当前进行中的工作

- **任务：**查询分析当前 v3.4 的正式结果，为下一轮优化选择提供依据。
- **当前进度：**结果入口、摘要和 CSV 清点完成；两组各 1,167 个 `attack + suite + user + injection` 键完全对齐，保存的 cohort 摘要一致。完整有效配置、逐案例轨迹和独立结果判定仍待核验。
- **已修改文件：**本次新增 `DV_STATE.md`。此前未提交的功能修改分布如下；精确清单以 Git 状态为准。

| 区域 | 主要文件 |
| --- | --- |
| 执行／诊断 | [defended.py](dscg/pipelines/defended.py)、[task_diagnostics.py](dscg/task_diagnostics.py)、[failure_policy.py](dscg/failure_policy.py) |
| 筛选／测量 | [run_injection_precheck.py](experiments/run_injection_precheck.py)、[injection_cohort.py](experiments/common/injection_cohort.py)、[run_partial_benchmark.py](experiments/run_partial_benchmark.py) |
| 读取／汇总／续跑 | `experiments/common/benchmark_outcomes.py`、`benchmark_reuse.py`、`partial_reporting.py`、`routing_reports.py` 及相关 diagnostics |
| 页面／测试／说明 | `dashboard/`、相关 `tests/`、README、`docs/`、workshop 索引及迁移报告；PDF 保持原字节移动 |

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

- **尚未完成：**逐键配置核验、baseline 成功／v3.4 失败及反向恢复清单、失败位置与证据审计、3 个原生攻击成功案例检查、成本范围核验、优化项选择及验证。

## 5. 关键技术决策

| 决策 | 选择原因 | 暂不采用的做法及原因 |
| --- | --- | --- |
| 当前工作限定 v3.4，先分析结果再优化 | banking／Slack 的效用损失需要由真实失败链路解释 | 不按单个案例或版本名称直接改提示／权限；尚无本轮归因结论 |
| 按工具定义／schema、已授权能力和当前动作进行判断 | 步骤文字、来源命令、模型解释不能授予权限或证明任务完成 | 不引入对象／数据／参数授权、动态扩权、参数修补或恢复机制；相关研究边界仍受锁定 |
| 保留 v3.4 实际免审与 Monitor 语义 | 原 public、低风险、无 sink 读取沿用确定性免审；新增 read-purpose-v2 在 selective 才实际免审，shadow 仍审计 | 不用阈值直接扩大免审：当前词法分数和默认 0.70 是诊断输入，不参与该规则的选择 |
| 单独审查“审计拒绝”与“最终执行” | 当前 Monitor 对已授权、有效分类、read 且 sink=none 的有效 deny 保留 READ_ONLY_SOURCE_ALLOW；abstain／无效审计仍阻断 | 不把每个 L3 deny 都计为实际阻挡，也不把该例外描述为未请求审计 |
| 原生评分、错误分母、成本分开记录 | 工具拒绝、模型协议错误、API故障、真实任务失败含义不同 | 不把错误样本计成成功防御、不把警告引用谓词直接当真实恶意效果 |
| 原始交互与诊断分文件，历史数据保留原样 | L3 回复在解析前保存，便于排查合法字段下的语义误拒和协议错误 | 不补造历史原回复、不回写旧结果／cohort、不通过换模型或评分获得通过 |

当前 L3 使用的 evidence 是有限上下文，不是参数来源或对象隐私的认证。read-purpose-v2 还要求读取幂等、参数有效、当前输入完整，通常 sink=none；外部网页只有可信请求逐字给出公共 URL 的窄例外，详见 [README 当前流程](README.md#当前框架与工作流程)。

## 6. 已知问题

| 问题描述 | 影响范围／已尝试方法 | 后续处理建议 |
| --- | --- | --- |
| banking／Slack TSR 低于匹配键 baseline | 本次摘要清点确认损失；既往已有步骤授权、短审计提示和严格判决契约，仍不能从格式合规推断语义正确 | 优先对退步配对做逐轨迹分类，核对必要读取、授权缺口、写入审计、主模型停办及工具错误 |
| 审计结论与实际阻挡可能不同 | 只读 deny 例外、整批前置拒绝及票据复核共同影响执行；近期诊断已增加模块来源 | 使用最终 ledger／Monitor 决策及成功工具返回核对，模型解释仅作线索 |
| 两项既有离线失败 | `test_sensitive_read_deny_does_not_block_source_read`；`test_structured_audit_uses_normalized_json_input_and_redacted_metadata`。迁移前 HEAD 快照复现相同失败；后者仍期待 v3 输入，当前为 v4 | 保留失败账，不放宽防御使测试通过；后续依据本版实际语义决定测试／实现处理 |
| 成本尚不能直接作节省结论 | 两组全部场景摘要 `cost_comparison_ready=false`；记录总 Token 分别 24,176,340 与 23,202,303 | 核查 invocation、cache、GOAL 预检、缺失 usage 和记录范围，再判断是否能比较 |
| 历史原始审计回复可能缺失 | 新迁入记录只作用于新执行；旧 inline／gzip 不一定含完整模型文本 | 可定位已有证据；缺失部分明确标未知，不能反推或伪造原回复 |
| 边界与文档存在限制 | E0 未过；I3 尚有8个范围缺口。AGENTS 为用户指定跨分支快照；部分 `report/report.md` 链接缺失 | 本文件按当前 v3.4 源码交接；研究解锁和独立验证继续走研究侧入口 |
| 受限 host profile 的诊断详情不全 | 源提交的 authorization 白名单省略若干 profile 详情，运行授权不受影响 | 若本轮失败实际涉及该路径，再补足必要诊断并验证 |

## 7. 测试与验证

### 最近执行的 Online Evaluation（2026-10-25，迁移验证）

- **范围：**9 个 tool_knowledge 计分案例（workspace／banking／Slack 各3）＋3 个 banking clean 控制，另有3个原生 GOAL 预检；不是正式结果集的重新执行。
- **实际结果：**attempted/completed/valid/incomplete/error = **12/12/12/0/0**；80 次真实 API 调用／80 响应，129,017 已知 Tokens，无 API 错误、无缺失 usage。攻击 TSR 5/9、原生 ASR 0/9；clean TSR 1/3、ASR不适用。
- **记录验收：**12 个主 JSON 仅保存 `dscg_diagnostics` 防御引用，12 份诊断 complete，计分轨迹保存20份 L3 原始回复。
- **解释范围：**证明本次记录／读取链路可运行，未证明效用改善或一般安全。本次批准范围已经完成。

### 最近执行的 Offline Regression

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

- **本次文档工作：**仅读取 Git、源码、摘要和 CSV，做文档链接／状态一致性与 `git diff --check`；新增模型调用0，不重跑运行时测试。
- **尚未验证：**正式结果每条轨迹的有效性、完整配置可比性、误拒／合理阻断区分、3个攻击成功的真实效果、成本可比性，以及任何新的优化。

## 8. 下一步计划

1. **固定分析输入。**以本文件列出的 baseline 与 v3.4 为范围，逐组核对实际模型／provider／adapter、后端、任务和注入ID、cohort、router模式、源策略及成本范围。保留本次文件哈希；不重筛目标或改历史评分。
2. **生成完整配对账。**按 attack＋suite＋user＋injection＋模型身份匹配；分别输出 baseline成功／v3.4失败、反向恢复、共同失败和共同成功，优先 banking、Slack，保留 travel 的改善与新增失败作对照。
3. **逐例定位失败。**分别核对 L1 可见事实、L2 授权／schema、L3 请求与协议／语义判决、Monitor最终结果、原生工具错误及主模型遗漏／停办。允许多标签，事件数与案例数分开；缺证据保持未知，不把参考轨迹当唯一解。
4. **审计安全和成本。**单独核查3个原生 ASR成功案例与输出文本谓词；区分实际恶意效果和警告引用。同时核对 GOAL、缓存、invocation 与任务成本，不凭低 ASR 或总 Token 数宣称改进。
5. **依据证据选择优化。**分析结论形成后，优先选择跨案例、职责明确的最小共享改动；在 `workshop/` 建立相应工程任务。优化理由须对应已观察问题和负例，继续遵守研究锁定边界。
6. **在新任务中验证优化。**先做适用的离线回归，再用现有 Qwen 和共享原生评分进行新名称在线对照；至少9个不同计分案例，按影响范围补充 clean／attack 和场景覆盖。完整 benchmark 仍需明确请求；旧活动预算不续用。

**待确认事项通过分析解决：**哪些下降属于误拒、哪些是合理阻断后的任务遗漏、哪些由 L2／主模型／工具错误造成；原生 ASR 判定是否对应真实效果；当前保存成本是否具备可比口径。当前没有预选某个机制为已获验证的优化方向。
